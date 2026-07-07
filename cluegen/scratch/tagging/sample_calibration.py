# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Stratified calibration sample from the NYT bank for rubric tagging.

Draws N clues per cell of a 3x3 grid — era tercile x weekday difficulty bucket —
so the hand-label slice and the judge bake-off cover the bank's spread rather
than its bulk. Hygiene filters only (ASCII, no grid cross-references, alphabetic
answers); no answer exclusions, since tagging contaminates no model eval.

Usage: python sample_calibration.py [--per-cell 14] [--seed N]
"""

import argparse
import csv
import datetime
import json
import random
import re
from pathlib import Path

CSV_PATH = Path('/Users/Shared/data/kaggle-nyt/nytcrosswords.csv')

CROSS_REFERENCE = re.compile(r'\d+-(Across|Down)|\bSee \d+\b', re.IGNORECASE)

ERA_BOUNDARIES = (2004, 2014)
WEEKDAY_BUCKETS = {
  0: 'easy',
  1: 'easy',
  2: 'medium',
  3: 'medium',
  4: 'hard',
  5: 'hard',
  6: 'medium',
}


def era_of(year: int) -> str:
  """Era tercile label for a puzzle year."""
  if year < ERA_BOUNDARIES[0]:
    return '1993-2003'
  if year < ERA_BOUNDARIES[1]:
    return '2004-2013'
  return '2014-2024'


def bank_cells() -> dict[tuple[str, str], list[dict]]:
  """Clean clue records grouped by (era, weekday bucket)."""
  cells: dict[tuple[str, str], list[dict]] = {}
  seen: set[tuple[str, str]] = set()
  with CSV_PATH.open(encoding='latin-1') as file:
    for row in csv.DictReader(file):
      answer, clue = row['Word'].strip(), row['Clue'].strip()
      if not answer or not clue or not answer.isalpha():
        continue
      if not clue.isascii() or CROSS_REFERENCE.search(clue):
        continue
      if (answer, clue) in seen:
        continue
      seen.add((answer, clue))
      date = datetime.datetime.strptime(row['Date'], '%m/%d/%Y').date()
      cell = (era_of(date.year), WEEKDAY_BUCKETS[date.weekday()])
      cells.setdefault(cell, []).append(
        {'answer': answer, 'clue': clue, 'date': row['Date']}
      )
  return cells


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--per-cell', type=int, default=14)
  parser.add_argument('--seed', type=int, default=20260705)
  parser.add_argument(
    '--output', type=Path, default=Path('calibration_clues.jsonl')
  )
  args = parser.parse_args()

  rng = random.Random(args.seed)
  records = []
  for cell, items in sorted(bank_cells().items()):
    picks = rng.sample(items, min(args.per_cell, len(items)))
    print(
      f'{cell[0]} / {cell[1]}: {len(items)} candidates, {len(picks)} sampled'
    )
    records.extend(picks)

  with args.output.open('w') as file:
    for record in records:
      file.write(json.dumps(record, ensure_ascii=False) + '\n')
  print(f'{len(records)} clues -> {args.output}')


if __name__ == '__main__':
  main()
