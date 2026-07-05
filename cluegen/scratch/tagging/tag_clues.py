# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Headless rubric tagging of bank clues via the Claude Code subscription.

Runs `claude -p` with the rubric as the ENTIRE system prompt
(`--system-prompt-file` replaces the default; `--tools ""` and `--bare` strip
tool schemas, hooks, skills, MCP servers, and CLAUDE.md), so each call's prefix
is just rubric + scoring instructions. The prefix bytes are identical across
calls — assembled once per run — so back-to-back chunks hit the 5-minute prompt
cache.

Input: jsonl with {"answer": ..., "clue": ...} per line. Output: jsonl with the
same keys plus the 27 rubric scales and "rationale"; already-tagged (answer,
clue) pairs are skipped on rerun, so the run is resumable. Per-call token usage
is appended to a usage log to ground cost estimates.

Usage: python tag_clues.py --clues FILE [--model haiku] [--chunk-size 10]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

RUBRIC_DEFAULT = (Path(__file__).parent.parent.parent / 'local'
                  / 'quality_rubric.md')

HOLISTIC_SCALES = ('satisfaction', 'difficulty', 'craft', 'liveliness')
BREAKDOWN_SCALES = ('economy', 'surface', 'fairness', 'anchor',
                    'cross_check', 'obscurity', 'misdirection', 'currency')
BASIS_SCALES = ('basis_aha', 'basis_elegance', 'basis_resistance',
                'basis_prize_fact', 'basis_fun')
MECHANISM_SCALES = (
    'mechanism_sense_pivot', 'mechanism_frame_anchor',
    'mechanism_count_metonymy', 'mechanism_definition_by_example',
    'mechanism_double_definition', 'mechanism_conceptual_reframe',
    'mechanism_metaphor', 'mechanism_vignette',
    'mechanism_relational_pivot', 'mechanism_prize_fact')
ALL_SCALES = (HOLISTIC_SCALES + BREAKDOWN_SCALES + BASIS_SCALES
              + MECHANISM_SCALES)

INSTRUCTIONS = f"""

---

# Tagging task

You are tagging New York Times crossword clues against the rubric above.
For EACH clue in the input, emit exactly one JSON object on its own line
(JSONL, in input order, no prose or fences around them) with these keys:

- "answer" and "clue": echoed verbatim from the input.
- Each of these scale keys, with a number from 1.0 to 5.0 (any value —
  3.7 is as legal as 4.0; never round to fit a bucket):
  {', '.join(ALL_SCALES)}
- "rationale": one or two sentences justifying the scores — the audit
  trail. Mention any bank oddity (era-drifted convention) here.

Scale key mapping: the "basis_" keys are the rubric's five basis scales;
the "mechanism_" keys are its ten mechanism scales (mechanism_prize_fact
is the mechanism, basis_prize_fact the felt basis). All other keys match
the rubric's scale names directly.
"""

MISSING_KEYS_LOG = 'tag_failures.jsonl'


def load_done(output_path: Path) -> set[tuple[str, str]]:
  """(answer, clue) pairs already tagged, for resumable reruns."""
  done = set()
  if output_path.exists():
    for line in output_path.open():
      record = json.loads(line)
      done.add((record['answer'], record['clue']))
  return done


TAGGING_BEGIN = '<!-- tagging-scales-begin'
TAGGING_END = '<!-- tagging-scales-end -->'

PROMPT_HEADER = """\
# Clue quality rubric — scale definitions

You grade New York Times crossword clues on continuous 1.0-5.0 scales.
"""


def extract_scales(rubric_text: str) -> str:
  """The scale definitions between the rubric's tagging markers; the
  meta-sections (ratification pointer, addenda, accounting) stay out of the
  prompt.
  """
  if TAGGING_BEGIN not in rubric_text or TAGGING_END not in rubric_text:
    sys.exit('rubric is missing the tagging-scales-begin/-end markers the '
             'prompt extraction relies on')
  after_begin = rubric_text.split(TAGGING_BEGIN, 1)[1]
  # The begin marker is a multi-line comment; drop through its close.
  after_begin = after_begin.split('-->', 1)[1]
  return after_begin.split(TAGGING_END, 1)[0].strip()


def assemble_system_prompt(rubric_path: Path, run_dir: Path) -> Path:
  """Scales + instructions written once per run; identical bytes across calls
  keep the prompt cache warm.
  """
  prompt_path = run_dir / 'system_prompt.md'
  scales = extract_scales(rubric_path.read_text())
  prompt_path.write_text(PROMPT_HEADER + '\n' + scales + INSTRUCTIONS)
  return prompt_path


def call_claude(prompt_path: Path, chunk: list[dict], model: str) -> dict:
  """One headless call scoring `chunk`; returns the parsed json envelope."""
  clue_lines = '\n'.join(
      json.dumps({'answer': item['answer'], 'clue': item['clue']},
                 ensure_ascii=False)
      for item in chunk)
  command = [
      'claude', '-p', f'Tag these clues:\n{clue_lines}',
      '--model', model,
      '--system-prompt-file', str(prompt_path),
      # Not --bare: it also skips credential loading, which silently breaks
      # subscription auth in headless runs (observed 2026-07-05).
      '--tools', '',
      '--setting-sources', '',
      '--no-session-persistence',
      '--max-turns', '1',
      '--output-format', 'json',
  ]
  completed = subprocess.run(command, capture_output=True, text=True,
                             timeout=600, check=True)
  return json.loads(completed.stdout)


def parse_records(result_text: str, chunk: list[dict]) -> list[dict]:
  """Valid scale records extracted from the model's JSONL reply."""
  records = []
  for line in result_text.splitlines():
    line = line.strip().strip('`')
    if not line.startswith('{'):
      continue
    try:
      record = json.loads(line)
    except json.JSONDecodeError:
      continue
    missing = [key for key in ALL_SCALES + ('answer', 'clue', 'rationale')
               if key not in record]
    if missing:
      continue
    records.append(record)
  expected = {(item['answer'], item['clue']) for item in chunk}
  return [r for r in records if (r['answer'], r['clue']) in expected]


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--clues', type=Path, required=True,
                      help='jsonl of {"answer", "clue"} to tag')
  parser.add_argument('--rubric', type=Path, default=RUBRIC_DEFAULT)
  parser.add_argument('--output', type=Path, default=Path('tags.jsonl'))
  parser.add_argument('--model', default='haiku')
  parser.add_argument('--chunk-size', type=int, default=10)
  parser.add_argument('--limit', type=int, default=None,
                      help='tag at most this many clues this run')
  parser.add_argument('--dry-run', action='store_true',
                      help='print the command and first user message; no '
                           'calls')
  args = parser.parse_args()

  # A stray API key would silently route billing to the Console instead of the
  # subscription — the one thing this script must never do.
  if os.environ.get('ANTHROPIC_API_KEY'):
    sys.exit('ANTHROPIC_API_KEY is set; unset it so calls bill the '
             'subscription, not the API.')

  run_dir = args.output.parent
  run_dir.mkdir(parents=True, exist_ok=True)
  prompt_path = assemble_system_prompt(args.rubric, run_dir)

  done = load_done(args.output)
  todo = []
  for line in args.clues.open():
    item = json.loads(line)
    if (item['answer'], item['clue']) not in done:
      todo.append(item)
  if args.limit is not None:
    todo = todo[:args.limit]
  print(f'{len(todo)} clues to tag ({len(done)} already done)')

  chunks = [todo[i:i + args.chunk_size]
            for i in range(0, len(todo), args.chunk_size)]
  if args.dry_run and chunks:
    print(f'system prompt: {prompt_path} '
          f'({len(prompt_path.read_text())} chars)')
    print('first user message:')
    print('\n'.join(json.dumps(item, ensure_ascii=False)
                    for item in chunks[0]))
    return

  usage_log = run_dir / 'tag_usage.jsonl'
  for index, chunk in enumerate(chunks):
    envelope = call_claude(prompt_path, chunk, args.model)
    records = parse_records(envelope.get('result', ''), chunk)
    with args.output.open('a') as file:
      for record in records:
        file.write(json.dumps(record, ensure_ascii=False) + '\n')
    with usage_log.open('a') as file:
      file.write(json.dumps({'chunk': index, 'clues': len(chunk),
                             'tagged': len(records),
                             'usage': envelope.get('usage'),
                             'cost': envelope.get('total_cost_usd')}) + '\n')
    if len(records) < len(chunk):
      tagged = {(r['answer'], r['clue']) for r in records}
      with (run_dir / MISSING_KEYS_LOG).open('a') as file:
        for item in chunk:
          if (item['answer'], item['clue']) not in tagged:
            file.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f'chunk {index + 1}/{len(chunks)}: {len(records)}/{len(chunk)} '
          'tagged')


if __name__ == '__main__':
  main()
