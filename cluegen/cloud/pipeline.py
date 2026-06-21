# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Batch clue-generation pipeline: words.in -> accepted.jsonl.

Each batch makes two fresh-context `claude -p` calls — GENERATE, then
VERIFY — with pure-code mechanical checks between them. All state lives
in append-only JSONL files under out/, so an interrupted run (rate
limit, crash) resumes cleanly: completed words are skipped, interrupted
verifications are re-run verify-only, and words with retryable failures
get exactly one regeneration attempt in a later batch.

Subcommands: `run` processes batches; `stats` reports bank totals.
"""

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from cluegen.cloud.bank_state import (
  VERDICT_ACCEPT,
  VERDICT_REJECT,
  VERDICT_REVISE,
  BankState,
)
from cluegen.cloud.claude_cli import (
  CallUsage,
  ClaudeCli,
  RateLimited,
  TransportFailure,
  describe_usage,
)
from cluegen.cloud.mechanical_checks import (
  check_word_output,
  clue_style_of,
  clue_text_of,
  expected_enumeration,
  letters_only,
  normalize_clue_text,
  stem_soft_flags,
)
from cluegen.cloud.prompt_rendering import (
  PromptTemplates,
  WordEntry,
  build_generation_prompt,
  build_verification_prompt,
  load_templates,
)

PROJECT_ROOT = Path(__file__).parent

VALID_VERDICTS = {VERDICT_ACCEPT, VERDICT_REVISE, VERDICT_REJECT}

# One clue queued for the VERIFY call:
# (word, attempt, batch, batch_size, clue, soft_flags).
VerifyItem = tuple[str, int, int, int, Mapping[str, object], Sequence[str]]

RUN_PRESETS = """\
presets:
  overnight   no --limit, no --pace: run until words.in is exhausted or
              the plan rate limit stops it; re-run next session to
              resume where it left off.
  background  --pace 15 (or --limit 60): leaves plan headroom for
              interactive use in the same 5-hour session window.

words.in is pre-sorted by expected value, so capped runs automatically
consume the highest-value words first.
"""


@dataclass(frozen=True)
class RunSettings:
  """Knobs for one `run` invocation."""

  batch_size: int
  limit: int | None
  american_per_word: int
  cryptic_per_word: int
  category_note: str
  pace_minutes: float
  call_timeout_seconds: float
  model: str
  dry_run: bool


@dataclass(frozen=True)
class BatchEntry:
  """One word slated for the current batch."""

  word: str
  attempt: int
  retry_reasons: tuple[str, ...] = ()


def parse_json_lines(
  output: str,
) -> tuple[list[dict[str, object]], list[str]]:
  """Split LLM output into JSON objects and unparseable leftovers.

  Tolerates stray markdown fences and a whole-output JSON array, since
  models occasionally ignore the no-fences instruction.
  """
  objects: list[dict[str, object]] = []
  unparsed: list[str] = []
  for line in output.splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith('```'):
      continue
    try:
      value = json.loads(stripped)
    except json.JSONDecodeError:
      unparsed.append(line)
      continue
    if isinstance(value, dict):
      objects.append(value)
    elif isinstance(value, list):
      objects.extend(v for v in value if isinstance(v, dict))
    else:
      unparsed.append(line)
  return objects, unparsed


def is_generation_output(output: str) -> bool:
  """Transport-level validity: at least one per-word JSON object."""
  objects, _ = parse_json_lines(output)
  return any('word' in o for o in objects)


def is_verification_output(output: str) -> bool:
  """Transport-level validity: at least one verdict JSON object."""
  objects, _ = parse_json_lines(output)
  return any('verdict' in o for o in objects)


def render_verification_line(
  word: str, clue: Mapping[str, object], soft_flags: Sequence[str]
) -> str:
  """One clue's JSON line for the judge, annotated with soft flags."""
  payload = dict(clue)
  payload['word'] = word
  payload['enumeration'] = expected_enumeration(word)
  if soft_flags:
    payload['leak_annotation'] = '; '.join(soft_flags)
  return json.dumps(payload)


def match_verdicts(
  surviving_clues: Sequence[Mapping[str, object]],
  judge_records: Sequence[dict[str, object]],
) -> list[dict[str, object] | None]:
  """Pair each surviving clue with the judge record reviewing it.

  Matches by normalized clue text first; leftovers pair up by style in
  order, tolerating judges that echo clue text imperfectly. Unmatched
  clues get None (the caller fabricates a synthetic "revise").
  """
  by_text: dict[str, list[dict[str, object]]] = defaultdict(list)
  for record in judge_records:
    echoed_text = record.get('clue')
    if isinstance(echoed_text, str):
      by_text[normalize_clue_text(echoed_text)].append(record)

  matches: list[dict[str, object] | None] = [None] * len(surviving_clues)
  unmatched_indexes = []
  for index, clue in enumerate(surviving_clues):
    bucket = by_text.get(normalize_clue_text(clue_text_of(clue)))
    if bucket:
      matches[index] = bucket.pop(0)
    else:
      unmatched_indexes.append(index)

  leftovers = [r for bucket in by_text.values() for r in bucket]
  for index in unmatched_indexes:
    style = surviving_clues[index].get('style')
    for record in leftovers:
      if record.get('style') == style:
        matches[index] = record
        leftovers.remove(record)
        break
  return matches


class Pipeline:
  """Drives batches of generate -> mechanical checks -> verify."""

  def __init__(
    self,
    words: Sequence[str],
    templates: PromptTemplates,
    state: BankState,
    cli: ClaudeCli,
    settings: RunSettings,
  ) -> None:
    """Wire the pipeline's dependencies together."""
    self.words = words
    self.templates = templates
    self.state = state
    self.cli = cli
    self.settings = settings
    self._last_batch_start: float | None = None
    self._usage_records: list[CallUsage] = []
    self._cost_records: list[float] = []
    self._calls_missing_usage = 0

  def log(self, message: str) -> None:
    """Print a progress line and append it to out/run.log."""
    print(message, flush=True)
    with (self.state.out_dir / 'run.log').open('a') as handle:
      handle.write(f'{time.strftime("%F %T")} {message}\n')

  def _complete_logged(
    self,
    label: str,
    prompt: str,
    is_valid: Callable[[str], bool],
  ) -> str:
    """Run one CLI call, log its token usage, and return the text."""
    response = self.cli.complete(prompt, is_valid=is_valid)
    self.log(describe_usage(label, response))
    if response.usage is None:
      self._calls_missing_usage += 1
    else:
      self._usage_records.append(response.usage)
    if response.cost_usd is not None:
      self._cost_records.append(response.cost_usd)
    return response.text

  def _log_usage_summary(self) -> None:
    """Log run-total token usage across all CLI calls, if any."""
    call_count = len(self._usage_records) + self._calls_missing_usage
    if call_count == 0:
      return
    missing = (
      f' ({self._calls_missing_usage} call(s) missing usage)'
      if self._calls_missing_usage
      else ''
    )
    cost = f' cost=${sum(self._cost_records):.4f}' if self._cost_records else ''
    self.log(
      f'[usage] run total over {call_count} call(s):'
      f' input={sum(u.input_tokens for u in self._usage_records)}'
      f' output={sum(u.output_tokens for u in self._usage_records)}'
      f' cache_read='
      f'{sum(u.cache_read_input_tokens for u in self._usage_records)}'
      f' cache_write='
      f'{sum(u.cache_creation_input_tokens for u in self._usage_records)}'
      f'{cost}{missing}'
    )

  # --- Batch composition ---

  def compose_batch(self, max_words: int | None) -> list[BatchEntry]:
    """Pick the next batch: queued retries first, then fresh words."""
    size = self.settings.batch_size
    if max_words is not None:
      size = min(size, max_words)
    if size <= 0:
      return []

    entries = [
      BatchEntry(entry.word, attempt=2, retry_reasons=entry.reasons)
      for entry in self.state.retry_entries()[:size]
    ]
    touched = self.state.touched_words()
    for word in self.words:
      if len(entries) >= size:
        break
      if word not in touched:
        entries.append(BatchEntry(word, attempt=1))
    return entries

  def wait_for_pace(self) -> None:
    """Honor --pace: a minimum interval between batch starts."""
    if self._last_batch_start is not None:
      interval = self.settings.pace_minutes * 60
      remaining = interval - (time.monotonic() - self._last_batch_start)
      if remaining > 0:
        self.log(f'Pacing: waiting {remaining:.0f}s before the next batch')
        time.sleep(remaining)
    self._last_batch_start = time.monotonic()

  # --- The two LLM calls ---

  def run_batch(self, batch_id: int, entries: list[BatchEntry]) -> None:
    """Process one batch end to end and log its summary line."""
    prompt = build_generation_prompt(
      self.templates,
      [WordEntry(e.word, e.retry_reasons) for e in entries],
      american_per_word=self.settings.american_per_word,
      cryptic_per_word=self.settings.cryptic_per_word,
      category_note=self.settings.category_note,
    )
    output = self._complete_logged('generate', prompt, is_generation_output)
    objects, unparsed = parse_json_lines(output)
    if unparsed:
      self.state.record_unparsed_output(batch=batch_id, lines=unparsed)

    objects_by_word: dict[str, dict[str, object]] = {}
    for parsed_object in objects:
      word_value = parsed_object.get('word')
      if isinstance(word_value, str):
        objects_by_word.setdefault(letters_only(word_value), parsed_object)

    verify_items: list[tuple[BatchEntry, Mapping[str, object], list[str]]] = []
    clue_count = 0
    for entry in entries:
      word_object = objects_by_word.get(letters_only(entry.word))
      self.state.record_generation(
        batch=batch_id,
        batch_size=len(entries),
        attempt=entry.attempt,
        word=entry.word,
        word_object=word_object,
      )
      if word_object is None:
        self.state.record_mechanical_failure(
          batch=batch_id,
          batch_size=len(entries),
          attempt=entry.attempt,
          word=entry.word,
          clue=None,
          reasons=['generator produced no output for this word'],
        )
        continue
      result = check_word_output(
        entry.word, word_object, self.state.accepted_texts
      )
      clue_count += len(result.checked_clues)
      if result.word_failures:
        self.state.record_mechanical_failure(
          batch=batch_id,
          batch_size=len(entries),
          attempt=entry.attempt,
          word=entry.word,
          clue=None,
          reasons=result.word_failures,
        )
      for checked in result.checked_clues:
        if checked.failures:
          self.state.record_mechanical_failure(
            batch=batch_id,
            batch_size=len(entries),
            attempt=entry.attempt,
            word=entry.word,
            clue=dict(checked.clue),
            reasons=checked.failures,
          )
        else:
          verify_items.append((entry, checked.clue, checked.soft_flags))

    verdict_counts = self.verify_and_record(
      [
        (e.word, e.attempt, batch_id, len(entries), clue, flags)
        for e, clue, flags in verify_items
      ]
    )

    for entry in entries:
      self.state.settle_word_attempt(entry.word, entry.attempt)

    retry_count = sum(1 for e in entries if e.attempt == 2)
    completed = len(self.state.completed_words())
    self.log(
      f'[batch {batch_id}] words={len(entries)}'
      f' (retries={retry_count}) clues={clue_count}'
      f' mech_pass={len(verify_items)}/{clue_count}'
      f' verdicts: accept={verdict_counts[VERDICT_ACCEPT]}'
      f' revise={verdict_counts[VERDICT_REVISE]}'
      f' reject={verdict_counts[VERDICT_REJECT]}'
      f' | cumulative: accepted={len(self.state.accepted_records)}'
      f' rejected={len(self.state.rejected_records)}'
      f' completed_words={completed}/{len(self.words)}'
    )

  def verify_and_record(self, items: Sequence[VerifyItem]) -> Counter[str]:
    """Run the VERIFY call for surviving clues and record verdicts.

    Clues the judge fails to address get a synthetic "revise" so the
    word's state is always fully verdicted after this step.
    """
    counts: Counter[str] = Counter()
    if not items:
      return counts

    lines = [
      render_verification_line(word, clue, flags)
      for word, _, _, _, clue, flags in items
    ]
    prompt = build_verification_prompt(self.templates, lines)
    output = self._complete_logged('verify', prompt, is_verification_output)
    judge_objects, _ = parse_json_lines(output)

    judges_by_word: defaultdict[str, list[dict[str, object]]] = defaultdict(
      list
    )
    for record in judge_objects:
      if 'verdict' in record:
        judges_by_word[letters_only(str(record.get('word') or ''))].append(
          record
        )

    items_by_word_attempt: defaultdict[tuple[str, int], list[VerifyItem]] = (
      defaultdict(list)
    )
    for item in items:
      items_by_word_attempt[(item[0], item[1])].append(item)

    for (word, attempt), word_items in items_by_word_attempt.items():
      clues = [item[4] for item in word_items]
      matches = match_verdicts(
        clues, judges_by_word.get(letters_only(word), [])
      )
      for item, judge in zip(word_items, matches, strict=True):
        _, _, batch, batch_size, clue, _ = item
        verdict = judge.get('verdict') if judge is not None else None
        reason = judge.get('reason') if judge is not None else None
        if not isinstance(verdict, str) or verdict not in VALID_VERDICTS:
          self.state.record_verdict(
            batch=batch,
            batch_size=batch_size,
            attempt=attempt,
            word=word,
            clue_text=clue_text_of(clue),
            style=clue_style_of(clue),
            verdict=VERDICT_REVISE,
            reason='judge returned no usable verdict for this clue',
            synthetic=True,
          )
          counts[VERDICT_REVISE] += 1
        else:
          self.state.record_verdict(
            batch=batch,
            batch_size=batch_size,
            attempt=attempt,
            word=word,
            clue_text=clue_text_of(clue),
            style=clue_style_of(clue),
            verdict=verdict,
            reason=reason if isinstance(reason, str) else None,
          )
          counts[verdict] += 1
    return counts

  def recover_pending_verifications(self) -> None:
    """Finish verify steps a previous run was interrupted before."""
    pending = self.state.pending_verifications()
    if not pending:
      return
    self.log(
      f'Recovering {len(pending)} interrupted'
      f' verification(s) from a previous run'
    )
    items: list[VerifyItem] = [
      (
        p.word,
        p.attempt,
        p.batch,
        p.batch_size,
        clue,
        stem_soft_flags(p.word, clue_text_of(clue)),
      )
      for p in pending
      for clue in p.surviving_clues
    ]
    self.verify_and_record(items)
    for p in pending:
      self.state.settle_word_attempt(p.word, p.attempt)

  # --- Top level ---

  def print_dry_run(self) -> None:
    """Print the first batch's assembled prompts without any calls."""
    entries = self.compose_batch(self.settings.limit)
    prompt = build_generation_prompt(
      self.templates,
      [WordEntry(e.word, e.retry_reasons) for e in entries],
      american_per_word=self.settings.american_per_word,
      cryptic_per_word=self.settings.cryptic_per_word,
      category_note=self.settings.category_note,
    )
    print('=' * 72)
    print('SYSTEM PROMPT (both calls, via --system-prompt-file)')
    print('=' * 72)
    print(self.templates.specification)
    print()
    print('=' * 72)
    print('GENERATION PROMPT (batch 1)')
    print('=' * 72)
    print(prompt)
    print()
    print('=' * 72)
    print(
      'VERIFICATION PROMPT (batch 1; clue lines depend on the'
      ' generation output)'
    )
    print('=' * 72)
    print(
      build_verification_prompt(
        self.templates, ['<JSONL of clues that survive mechanical checks>']
      )
    )

  def run(self) -> int:
    """The full run loop; returns a process exit code."""
    if self.settings.dry_run:
      self.print_dry_run()
      return 0

    words_processed = 0
    try:
      self.recover_pending_verifications()
      while True:
        remaining = None
        if self.settings.limit is not None:
          remaining = self.settings.limit - words_processed
          if remaining <= 0:
            self.log(f'--limit {self.settings.limit} reached; stopping.')
            break
        entries = self.compose_batch(remaining)
        if not entries:
          self.log('No words left to process; bank is complete for words.in.')
          break
        self.wait_for_pace()
        self.run_batch(self.state.next_batch_id(), entries)
        words_processed += len(entries)
    except RateLimited as error:
      self.log(
        f'Plan rate limit hit — stopping gracefully; re-run'
        f' to resume. Details: {error}'
      )
      return 0
    except TransportFailure as error:
      self.log(
        f'CLI call failed twice — stopping; re-run to resume. Details: {error}'
      )
      return 1
    finally:
      self._log_usage_summary()
    return 0


# --- stats subcommand ---


def categorize_mechanical_reason(reason: str) -> str:
  """Coarse category for a mechanical-failure reason string."""
  categories = (
    ('enumeration', 'enumeration mismatch'),
    ('fodder', 'anagram fodder'),
    ('hidden', 'hidden string'),
    ('answer', 'answer leakage'),
    ('duplicate', 'duplicate clue text'),
    ('trap', 'missing trap'),
    ('no output', 'generator produced no output'),
  )
  for needle, category in categories:
    if needle in reason:
      return category
  return 'schema/other'


def print_stats(state: BankState, words: Sequence[str]) -> None:
  """Report bank totals by style, difficulty, and failure category."""
  completed = state.completed_words()
  print(
    f'Words: {len(words)} total | {len(completed)} completed |'
    f' {len(state.retry_entries())} awaiting retry |'
    f' {len(state.pending_verifications())} pending verification |'
    f' {len(words) - len(state.touched_words())} untouched'
  )

  print(f'\nAccepted clues: {len(state.accepted_records)}')
  for label in ('style', 'difficulty', 'confidence'):
    counts = Counter(r['clue'].get(label) for r in state.accepted_records)
    if counts:
      breakdown = ', '.join(
        f'{value}={count}' for value, count in counts.most_common()
      )
      print(f'  by {label}: {breakdown}')

  print(f'\nRejected/final: {len(state.rejected_records)}')
  kind_counts = Counter(r['kind'] for r in state.rejected_records)
  for kind, count in kind_counts.most_common():
    print(f'  {kind}: {count}')

  verdict_counts = Counter(r['verdict'] for r in state.verdict_records)
  if verdict_counts:
    breakdown = ', '.join(
      f'{verdict}={count}' for verdict, count in verdict_counts.most_common()
    )
    print(f'\nJudge verdicts (all attempts): {breakdown}')

  reason_counts: Counter[str] = Counter()
  for record in state.mechanical_failure_records:
    for reason in record['reasons']:
      reason_counts[categorize_mechanical_reason(reason)] += 1
  if reason_counts:
    print('\nMechanical failures by category:')
    for category, count in reason_counts.most_common():
      print(f'  {category}: {count}')

  print_batch_size_comparison(state)


def print_batch_size_comparison(state: BankState) -> None:
  """Accept and mech-pass rates per batch size, for calibration runs."""
  generated: Counter[int] = Counter()
  for generation in state.generation_records:
    word_object = generation['object']
    if word_object is not None:
      clues = word_object.get('clues')
      if isinstance(clues, list):
        generated[generation['batch_size']] += len(clues)
  if len(generated) < 2:
    return

  mechanical_failures: Counter[int] = Counter()
  for failure in state.mechanical_failure_records:
    mechanical_failures[failure['batch_size']] += 1
  verdicts_by_size: dict[int, Counter[str]] = defaultdict(Counter)
  for verdict in state.verdict_records:
    verdicts_by_size[verdict['batch_size']][verdict['verdict']] += 1

  print('\nBy batch size (for calibration):')
  for size in sorted(generated):
    clue_count = generated[size]
    passed = clue_count - mechanical_failures[size]
    verdicts = verdicts_by_size[size]
    total_verdicts = sum(verdicts.values())
    accept_rate = (
      verdicts[VERDICT_ACCEPT] / total_verdicts if total_verdicts else 0.0
    )
    print(
      f'  batch_size={size}: clues={clue_count}'
      f' mech_pass={passed}/{clue_count}'
      f' accept_rate={accept_rate:.0%}'
      f' (of {total_verdicts} verdicts)'
    )


# --- CLI ---


def load_words(path: Path) -> list[str]:
  """Read the answer word list, one word per line."""
  return [
    line.strip() for line in path.read_text().splitlines() if line.strip()
  ]


def build_argument_parser() -> argparse.ArgumentParser:
  """The pipeline's command-line interface."""
  parser = argparse.ArgumentParser(
    description='Batch clue-generation pipeline over words.in.'
  )
  subcommands = parser.add_subparsers(dest='command', required=True)

  run_parser = subcommands.add_parser(
    'run',
    help='process batches of words through generate/verify',
    epilog=RUN_PRESETS,
    formatter_class=argparse.RawDescriptionHelpFormatter,
  )
  run_parser.add_argument(
    '--batch-size',
    type=int,
    default=12,
    help='words per batch — per-call load, the quality knob'
    ' (default: %(default)s)',
  )
  run_parser.add_argument(
    '--limit',
    type=int,
    default=None,
    help='max words to process this run — per-run budget, the cost'
    ' knob (default: no limit)',
  )
  run_parser.add_argument(
    '--american-per-word',
    type=int,
    default=2,
    help='American-style clues requested per word (default: %(default)s)',
  )
  run_parser.add_argument(
    '--cryptic-per-word',
    type=int,
    default=2,
    help='cryptic-style clues requested per word (default: %(default)s)',
  )
  run_parser.add_argument(
    '--category-note-file',
    type=Path,
    default=None,
    help='file whose text fills {{CATEGORY_NOTE}} in the generation prompt',
  )
  run_parser.add_argument(
    '--pace',
    type=float,
    default=0,
    metavar='MINUTES',
    help='minimum wall-clock interval between batch starts;'
    ' 0 = unthrottled (default: %(default)s)',
  )
  run_parser.add_argument(
    '--call-timeout',
    type=float,
    default=900,
    metavar='SECONDS',
    help='timeout per claude CLI call (default: %(default)s)',
  )
  run_parser.add_argument(
    '--model',
    default='claude-fable-5',
    help='Claude model for both LLM calls, passed through to'
    ' `claude --model` (default: %(default)s)',
  )
  run_parser.add_argument(
    '--dry-run',
    action='store_true',
    help="assemble and print the first batch's prompts without calling the CLI",
  )

  subcommands.add_parser(
    'stats',
    help='report bank totals by style, difficulty, and failure category',
  )
  return parser


def main(argv: Sequence[str] | None = None) -> int:
  """Entry point; returns a process exit code."""
  args = build_argument_parser().parse_args(argv)
  words = load_words(PROJECT_ROOT / 'words.in')
  state = BankState(PROJECT_ROOT / 'out')

  if args.command == 'stats':
    print_stats(state, words)
    return 0

  if args.american_per_word + args.cryptic_per_word < 1:
    print('error: at least one clue per word is required', file=sys.stderr)
    return 2
  category_note = ''
  if args.category_note_file is not None:
    category_note = args.category_note_file.read_text().strip()

  settings = RunSettings(
    batch_size=args.batch_size,
    limit=args.limit,
    american_per_word=args.american_per_word,
    cryptic_per_word=args.cryptic_per_word,
    category_note=category_note,
    pace_minutes=args.pace,
    call_timeout_seconds=args.call_timeout,
    model=args.model,
    dry_run=args.dry_run,
  )
  pipeline = Pipeline(
    words=words,
    templates=load_templates(PROJECT_ROOT),
    state=state,
    cli=ClaudeCli(
      timeout_seconds=settings.call_timeout_seconds,
      model=settings.model,
      system_prompt_file=PROJECT_ROOT / 'CLUE_SPEC.md',
    ),
    settings=settings,
  )
  return pipeline.run()


if __name__ == '__main__':
  sys.exit(main())
