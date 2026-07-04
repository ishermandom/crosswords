# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Generate the expanded eval set: ~90 Fable-labeled graded examples.

User priority (2026-07-04, `#eval-expansion` in tasks.md): the window's judge
tuning steers by ~15 contested real rows; a ~100-example set should surface
lower-hanging fruit. This script asks Fable for invented, labeled clue examples
in funcal's pair structure — for each answer word, an accept plus a near-miss
revise/reject that isolates ONE dimension — organized into buckets drawn from
the window's discovered failure taxonomy.

Contamination guard: the prompt embeds an exclusion list built from words.in,
every eval set, the clue bank, the reject bank, and every answer word used as a
calibration example inside the judge prompts (a generated row on a
prompt-example word would test memorization, not judgment).

Two call groups keep each request small enough to finish reliably (a single big
Fable call timed out once this window):

- group 1: precision checks (vignette, question_mark, count_metonymy,
  sense_ownership, padding)
- group 2: taste gradient + truth (flat_vs_prize, fun_gradient, elegance,
  non_pinning, truth)

Usage: python expansion_gen.py --group 1 [--dry-run]

Rows land in `expansion_raw.jsonl` (append; `bucket` field kept for analysis).
Partitioning into tune/holdout battery sets happens separately once both groups
are in.
"""

import argparse
import datetime
import json
import pathlib
import re
import subprocess
import tempfile

_HERE = pathlib.Path(__file__).parent
_CLOUD = _HERE.parent / 'cloud'
_RAW_PATH = _HERE / 'expansion_raw.jsonl'

_EVAL_FILES = [
  _HERE / 'satisfaction_reference_verdicts.jsonl',
  _HERE / 'satisfaction_holdout_clues.jsonl',
  _HERE / 'fresh_validation_verdicts.jsonl',
  _HERE / 'recall_loss_verdicts.jsonl',
  _HERE / 'fun_calibration_verdicts.jsonl',
  _HERE / 'fresh_label_input.jsonl',
  _HERE / 'checkpoint_clues.jsonl',
  _HERE.parent / 'local' / 'reject_bank.jsonl',
  _HERE.parent / 'local' / 'clue_bank.jsonl',
]
_PROMPT_FILES = [_HERE / 'pipeline_local.py', *sorted((_HERE / 'variants').glob('*.py'))]
_EXAMPLE_WORD_PATTERN = re.compile(r'-> ([A-Z]+)')

# Each bucket: (name, pair count, instruction). Pair = accept + near-miss.
_GROUPS = {
  1: [
    (
      'vignette',
      7,
      'Definite-description or vignette clues: a long, specific surface — a '
      'lived moment, a scene, a definite description — that genuinely '
      'defines the answer (accept, basis fun or elegance), paired with a '
      'same-style near-miss whose description actually fits something '
      'adjacent to the answer rather than the answer itself (revise). The '
      'accepts must substitute fairly despite their length.'
    ),
    (
      'question_mark',
      5,
      "Question-mark license: an earned '?' — a stretched, figurative, or "
      'metonymic definition the ? marks, and the figurative reading is true '
      '(accept), paired with either a straight fact wearing an apologetic ? '
      "(revise) or a ?-marked near-miss equivalence where the stretch does "
      'not read true, e.g. an event equated with its score (revise).'
    ),
    (
      'count_metonymy',
      4,
      'Count metonymy: the answer is a number defined by what it counts, and '
      'the clue names the counted thing exactly (accept), paired with an '
      'unfair version where the clue names an event or object merely '
      'associated with the number rather than the thing counted (revise). '
      'Number words are allowed here when not on the exclusion list.'
    ),
    (
      'sense_ownership',
      4,
      'Sense ownership: a legitimate secondary, archaic, or famous-bearer '
      'sense (accept), paired with a sense English does not own — a '
      'homograph in another language, or a sense that exists only inside a '
      'longer idiom (reject).'
    ),
    (
      'padding',
      4,
      'Economy: a clue whose modifier earns its place — precision, image, or '
      'misdirection the definition needs (accept), paired with a version '
      'carrying genuine padding: a word or phrase whose deletion leaves the '
      'definition just as complete, precise, and vivid (revise, and the '
      'reason must quote the padding).'
    ),
  ],
  2: [
    (
      'flat_vs_prize',
      5,
      'Prize-fact gradient: a straight clue carried by a remark-worthy, '
      'checkable, specific fact (accept, basis prize-fact), paired with the '
      'same mechanism at its flat end — an accurate fact everyone already '
      'knows, plainly stated (revise).'
    ),
    (
      'fun_gradient',
      4,
      'Fun gradient: a surface with its own wit — a joke, image, or turn of '
      'phrase enjoyable before solving (accept, basis fun), paired with '
      'recognition dressed as fun: stock associations of the answer fused '
      'into a breezy surface (revise).'
    ),
    (
      'elegance',
      4,
      'Elegance: a vivid straight definition — a precise sensory scene or '
      'evocative picture of the answer\'s ordinary sense (accept, basis '
      'elegance), paired with a plain dictionary gloss of the same answer '
      '(revise).'
    ),
    (
      'non_pinning',
      4,
      'Under-determination is a virtue: a TRUE clue that also fits other '
      'answers — the solver disambiguates from crossings (accept; pick any '
      'earned basis), paired with a clue that fails not by fitting several '
      'answers but by being actually false or overclaiming for this answer '
      '(revise). The accept\'s reason must note that fitting several answers '
      'is fine.'
    ),
    (
      'truth',
      5,
      'Literal truth and referent: a clue whose qualifiers all pin and hold '
      '(accept), paired with either a modifier that overclaims or falsely '
      'implies (revise), or a clue that defines a person or thing merely '
      'associated with the answer — the referent shifts (reject).'
    ),
  ],
}

_OUTPUT_RULES = """
Output rules (strict — machine-parsed):
- One JSON object per line (JSONL), no prose, no markdown fences.
- Keys: "bucket", "word", "clue", "verdict", "basis", "reason".
- "verdict": "accept" | "revise" | "reject". "basis": for accepts, one of
  "aha" | "elegance" | "resistance" | "prize-fact" | "fun"; null otherwise.
- "reason": one line naming the decisive dimension — instructive, the way an
  editor would explain the call to another editor.
- Each pair uses the SAME answer word for both rows, so the contrast
  isolates the dimension.
- Answer words: common English words, UPPERCASE, and NONE may appear on the
  exclusion list below. Prefer everyday, checkable subject matter.
- These are invented calibration examples for tuning a judge — make each
  one unambiguous for its bucket, not a borderline case.
"""


def _excluded_words() -> set[str]:
  """Every answer word a generated example must avoid."""
  words: set[str] = set()
  words_in = _CLOUD / 'words.in'
  words.update(
    line.strip().upper()
    for line in words_in.read_text().splitlines()
    if line.strip()
  )
  for path in _EVAL_FILES:
    if not path.exists():
      continue
    for line in path.read_text().splitlines():
      if line:
        words.add(json.loads(line)['word'].upper())
  for path in _PROMPT_FILES:
    words.update(_EXAMPLE_WORD_PATTERN.findall(path.read_text()))
  return words


def _render_prompt(group: int) -> str:
  buckets = _GROUPS[group]
  pair_total = sum(count for _, count, _ in buckets)
  bucket_text = '\n\n'.join(
    f'Bucket "{name}" — {count} pairs:\n{instruction}'
    for name, count, instruction in buckets
  )
  exclusion = ', '.join(sorted(_excluded_words()))
  return (
    'You are generating calibration examples for the clue-judging '
    'specification in your system prompt. Invent graded example pairs — '
    f'{pair_total} pairs ({pair_total * 2} rows) across the buckets below — '
    'that teach a judge exactly where each boundary sits.\n\n'
    f'{bucket_text}\n'
    f'{_OUTPUT_RULES}\n'
    f'EXCLUSION LIST (never use these as answer words): {exclusion}\n'
  )


def _generate(prompt: str) -> dict:
  command = [
    'claude',
    '-p',
    '--output-format',
    'json',
    '--disable-slash-commands',
    '--disallowedTools',
    '*',
    '--model',
    'claude-fable-5',
    '--system-prompt-file',
    str(_CLOUD / 'CLUE_SPEC.md'),
  ]
  completed = subprocess.run(
    command,
    input=prompt,
    capture_output=True,
    text=True,
    timeout=1500,
    cwd=tempfile.mkdtemp(prefix='expansion-gen-'),
    check=True,
  )
  return json.loads(completed.stdout)


def _parse_rows(result_text: str, group: int, excluded: set[str]) -> list[dict]:
  """Validated rows from the reply; complaints printed, bad rows dropped."""
  bucket_names = {name for name, _, _ in _GROUPS[group]}
  rows = []
  for line in result_text.splitlines():
    line = line.strip().strip('`')
    if not line.startswith('{'):
      continue
    row = json.loads(line)
    problems = []
    if row.get('bucket') not in bucket_names:
      problems.append(f'bucket {row.get("bucket")!r}')
    if row.get('verdict') not in ('accept', 'revise', 'reject'):
      problems.append(f'verdict {row.get("verdict")!r}')
    word = str(row.get('word', '')).upper()
    if not word or word in excluded:
      problems.append(f'word {word!r} excluded or empty')
    if not row.get('clue') or not row.get('reason'):
      problems.append('missing clue or reason')
    if problems:
      print(f'DROPPED ({"; ".join(problems)}): {json.dumps(row)}')
      continue
    row['word'] = word
    rows.append(row)
  return rows


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--group', type=int, required=True, choices=(1, 2))
  parser.add_argument('--dry-run', action='store_true')
  cli = parser.parse_args()

  prompt = _render_prompt(cli.group)
  if cli.dry_run:
    print(prompt)
    raise SystemExit(0)

  excluded = _excluded_words()
  envelope = _generate(prompt)
  rows = _parse_rows(envelope.get('result', ''), cli.group, excluded)
  stamp = datetime.datetime.now(datetime.UTC).isoformat(timespec='seconds')
  with _RAW_PATH.open('a') as raw:
    for row in rows:
      raw.write(json.dumps({**row, 'group': cli.group, 'ts': stamp}) + '\n')
  cost = envelope.get('total_cost_usd', 0.0)
  counts: dict[str, int] = {}
  for row in rows:
    counts[row['bucket']] = counts.get(row['bucket'], 0) + 1
  print(f'group {cli.group}: {len(rows)} rows kept, ${cost:.2f}')
  for bucket, count in sorted(counts.items()):
    print(f'  {bucket}: {count}')
