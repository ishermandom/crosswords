# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Inventory of setter drafts from the July-1 pipeline logs (bank provenance).

Each pipeline word block runs the setter funnel: angle brainstorm, 4-5 drafted
clues, a self-editor pass with KEEP/CUT verdicts, a JSON pick, then the judge.
This parses every block into (word, drafts, editor verdicts, pick, judge) rows —
the raw material for the setter-output distribution question: does the setter
draft lively options that the editor pick or judging then loses?
"""

import json
import pathlib
import re
import sys

_LOG_DIR = pathlib.Path(__file__).parent / 'logs'
_WORD_HEADER = re.compile(r'^===== (?P<word>[A-Z]+) =====$')
_STAGE_HEADER = re.compile(r'^--- (?P<stage>.+?)\.{0,3}$')
_EDITOR_VERDICT = re.compile(r'^Verdict: (?P<verdict>KEEP|CUT)')


def _blocks(text):
  """Yields (word, block_lines) per ===== WORD ===== section."""
  word, lines = None, []
  for line in text.splitlines():
    match = _WORD_HEADER.match(line)
    if match:
      if word:
        yield word, lines
      word, lines = match.group('word'), []
    elif word:
      lines.append(line)
  if word:
    yield word, lines


def _stages(lines):
  """Yields (stage_label, body_lines) per --- stage section of a block."""
  label, body = None, []
  for line in lines:
    match = _STAGE_HEADER.match(line)
    if match:
      if label:
        yield label, body
      label, body = match.group('stage'), []
    elif label is not None:
      body.append(line)
  if label:
    yield label, body


def _parse_drafts(body):
  """Clue texts from the drafts stage: first line of each blank-run group."""
  drafts = []
  group = []
  for line in [*body, '']:
    if line.strip():
      group.append(line.strip())
    else:
      if group:
        drafts.append(group[0])
      group = []
  return drafts


def _parse_editor(body):
  """(clue, verdict) pairs from the self-editor stage."""
  verdicts = []
  clue = None
  for line in body:
    line = line.strip()
    match = _EDITOR_VERDICT.match(line)
    if match and clue:
      verdicts.append((clue, match.group('verdict')))
    elif line and not line.startswith(
      ('Sentence:', 'Substitution:', 'Verdict:')
    ):
      clue = line
  return verdicts


def main() -> None:
  """Parse every pipeline log and write the draft inventory."""
  rows = []
  for path in sorted(_LOG_DIR.glob('pipeline_*.log')):
    for word, lines in _blocks(path.read_text()):
      row = {
        'word': word,
        'log': path.name,
        'drafts': [],
        'editor': [],
        'pick': None,
        'harvest': [],
        'judge': [],
      }
      for label, body in _stages(lines):
        if label.startswith('setter Pick the'):
          row['drafts'] = _parse_drafts(body)
        elif label.startswith('setter Now act as your own'):
          row['editor'] = _parse_editor(body)
        elif label.startswith('setter Select the single best'):
          try:
            row['pick'] = json.loads('\n'.join(body))
          except json.JSONDecodeError:
            print(f'unparseable pick: {path.name} {word}', file=sys.stderr)
        elif label.startswith('setter Return EVERY'):
          try:
            row['harvest'] = json.loads('\n'.join(body))['clues']
          except (json.JSONDecodeError, KeyError):
            print(f'unparseable harvest: {path.name} {word}', file=sys.stderr)
        elif label.startswith('judge['):
          row['judge'].append(label)
      rows.append(row)

  words = {r['word'] for r in rows}
  draft_count = sum(len(r['drafts']) for r in rows)
  keeps = sum(v == 'KEEP' for r in rows for _, v in r['editor'])
  cuts = sum(v == 'CUT' for r in rows for _, v in r['editor'])
  picks = sum(bool(r['pick']) for r in rows)
  harvested = sum(len(r['harvest']) for r in rows)
  print(
    f'{len(rows)} word runs over {len(words)} words: {draft_count} drafts, '
    f'{keeps} KEEP / {cuts} CUT, {picks} picks, {harvested} harvested'
  )
  no_drafts = [r['word'] for r in rows if not r['drafts']]
  if no_drafts:
    print(f'runs with no drafts parsed: {no_drafts}')
  out_path = _LOG_DIR / 'setter_draft_inventory.jsonl'
  out_path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
  print(f'wrote {out_path}')


if __name__ == '__main__':
  main()
