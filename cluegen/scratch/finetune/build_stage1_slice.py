# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Build the stage-1 fine-tuning slice from the Kaggle NYT clue set.

Implements the settled recipe (finetune.md, "Curation recipe"): normalized dedup
keeping the most recent copy; every sampling choice weighted by weekday weight x
linear recency weight; <= 4 clues per answer drawn by that combined weight
without replacement; weekday-derived difficulty token in the training prompt;
answer-level split with the panel + held-out answers excluded and a fixed block
of validation answers. Ends with hard assertions and a funnel report (rows
surviving each filter, weekday/bucket mix, contrast-pair count) as the durable
record of what the slice contained.

Usage: python build_stage1_slice.py [--size N] [--seed N]
"""

import argparse
import collections
import csv
import datetime
import json
import random
import re
from pathlib import Path

from prompts import PROMPT_TEMPLATE

CSV_PATH = Path('/Users/Shared/data/kaggle-nyt/nytcrosswords.csv')
OUTPUT_DIR = Path(__file__).parent / 'data' / 'data_stage1'

# Weekday sampling weights, Monday..Sunday (user-set, spec "Sampling weights"):
# Thursday is the top target difficulty, Sunday sits with it.
WEEKDAY_WEIGHTS = (1.0, 1.5, 2.0, 4.0, 3.0, 2.0, 4.0)

# Weekday -> difficulty bucket for the conditioning token (spec "Difficulty
# conditioning"): Mon-Tue easy, Wed-Thu medium, Fri-Sat hard, Sun medium.
WEEKDAY_BUCKETS = ('easy', 'easy', 'medium', 'medium', 'hard', 'hard',
                   'medium')

# Answers the eval harness reserves: the 12-word iteration panel and the 8
# held-out words. Training must never see them.
EXCLUDED_ANSWERS = {
    'SCORE', 'DAISY', 'GRANT', 'CHECK', 'GASP', 'AMBER',
    'TWENTY', 'GROSS', 'PAIR', 'VIOLET', 'ROBIN', 'STOCK',
    'COURT', 'SUE', 'HAZEL', 'SECOND', 'ZED', 'FORTY', 'DOZEN', 'NINETEEN',
}

CLUES_PER_ANSWER_CAP = 4
VALID_ANSWER_COUNT = 500

# Grid cross-references ("17-Across", "See 42-Down") are meaningless outside a
# puzzle and must never be imitated.
CROSS_REFERENCE_PATTERN = re.compile(r'\d+-(Across|Down)', re.IGNORECASE)

# Latin-1 mojibake markers: UTF-8 bytes mistakenly present in the latin-1 file
# decode to these sequences.
MOJIBAKE_MARKERS = ('â€', 'Â', '�')


def recency_weight(year: int) -> float:
  """Linear 1.0 (1993) -> 2.0 (2021), per the spec's mild recency bias."""
  return 1.0 + (year - 1993) / 28


def normalized_clue(clue: str) -> str:
  """Dedup key: case-, punctuation-, and whitespace-insensitive."""
  return re.sub(r'[^a-z0-9]+', '', clue.lower())


def weighted_picks(candidates: list[dict], count: int,
                   rng: random.Random) -> list[dict]:
  """Draw up to `count` candidates by weight, without replacement."""
  pool = list(candidates)
  picks = []
  while pool and len(picks) < count:
    total = sum(c['weight'] for c in pool)
    mark = rng.random() * total
    for index, candidate in enumerate(pool):
      mark -= candidate['weight']
      if mark <= 0:
        picks.append(pool.pop(index))
        break
  return picks


def load_pool(funnel: collections.Counter) -> dict[str, list[dict]]:
  """Parse, filter, and dedup the CSV into per-answer candidate lists."""
  latest: dict[tuple[str, str], dict] = {}
  with CSV_PATH.open(encoding='latin-1', newline='') as file:
    for row in csv.DictReader(file):
      funnel['rows'] += 1
      try:
        date = datetime.datetime.strptime(row['Date'], '%m/%d/%Y').date()
      except (ValueError, KeyError):
        funnel['bad date'] += 1
        continue
      answer = (row['Word'] or '').strip().upper()
      clue = (row['Clue'] or '').strip()
      if not (answer.isalpha() and answer.isascii()
              and 3 <= len(answer) <= 15):
        funnel['answer shape'] += 1
        continue
      if answer in EXCLUDED_ANSWERS:
        funnel['reserved answer'] += 1
        continue
      if not clue:
        funnel['empty clue'] += 1
        continue
      if CROSS_REFERENCE_PATTERN.search(clue):
        funnel['cross-reference'] += 1
        continue
      if answer.lower() in clue.lower():
        funnel['answer in clue'] += 1
        continue
      if any(marker in clue for marker in MOJIBAKE_MARKERS):
        funnel['mojibake'] += 1
        continue

      # Normalized dedup, keeping the most recent copy.
      key = (answer, normalized_clue(clue))
      kept = latest.get(key)
      if kept is None or date > kept['date']:
        latest[key] = {
            'answer': answer,
            'clue': clue,
            'date': date,
            'bucket': WEEKDAY_BUCKETS[date.weekday()],
            'weight': (WEEKDAY_WEIGHTS[date.weekday()]
                       * recency_weight(date.year)),
        }
  funnel['after dedup'] = len(latest)

  pool: dict[str, list[dict]] = collections.defaultdict(list)
  for candidate in latest.values():
    pool[candidate['answer']].append(candidate)
  funnel['distinct answers'] = len(pool)
  return pool


def write_split(path: Path, records: list[dict]) -> None:
  """Write one JSONL split in mlx-lm chat format."""
  with path.open('w', encoding='utf-8') as file:
    for record in records:
      message_pair = {'messages': [
          {'role': 'user',
           'content': PROMPT_TEMPLATE.format(difficulty=record['bucket'],
                                             answer=record['answer'])},
          {'role': 'assistant', 'content': record['clue']},
      ]}
      file.write(json.dumps(message_pair, ensure_ascii=False) + '\n')


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--size', type=int, default=10_000,
                      help='target train-pair count (final value comes from '
                           'the 12B timing run)')
  parser.add_argument('--seed', type=int, default=20260702)
  parser.add_argument('--output-dir', type=Path, default=OUTPUT_DIR,
                      help='destination for train/valid jsonl; larger rungs '
                           'get their own directory so the 5k slice stays '
                           'intact for comparisons')
  args = parser.parse_args()

  funnel: collections.Counter = collections.Counter()
  pool = load_pool(funnel)
  rng = random.Random(args.seed)

  # Per-answer cap picks, then answer-level split: the first block of shuffled
  # answers becomes validation, the rest fill train to --size.
  answers = sorted(pool)
  rng.shuffle(answers)
  valid_answers = set(answers[:VALID_ANSWER_COUNT])

  train: list[dict] = []
  valid: list[dict] = []
  for answer in answers:
    picks = weighted_picks(pool[answer], CLUES_PER_ANSWER_CAP, rng)
    if answer in valid_answers:
      valid.extend(picks)
    elif len(train) < args.size:
      train.extend(picks)
  train = train[:args.size]

  # Hard guarantees the training run relies on.
  train_answers = {r['answer'] for r in train}
  assert not train_answers & {r['answer'] for r in valid}
  assert not (train_answers | {r['answer'] for r in valid}) \
      & EXCLUDED_ANSWERS
  assert all(r['bucket'] in ('easy', 'medium', 'hard')
             for r in train + valid)

  args.output_dir.mkdir(exist_ok=True)
  write_split(args.output_dir / 'train.jsonl', train)
  write_split(args.output_dir / 'valid.jsonl', valid)

  # Funnel report — the durable record of what the slice contained.
  print('--- funnel ---')
  for stage, count in funnel.items():
    print(f'{stage:>18}: {count}')
  print('--- train slice ---')
  print(f'{"pairs":>18}: {len(train)}')
  print(f'{"answers":>18}: {len(train_answers)}')
  bucket_counts = collections.Counter(r['bucket'] for r in train)
  for bucket in ('easy', 'medium', 'hard'):
    print(f'{bucket:>18}: {bucket_counts[bucket]}')
  buckets_by_answer = collections.defaultdict(set)
  for record in train:
    buckets_by_answer[record['answer']].add(record['bucket'])
  contrast_answers = sum(
      1 for buckets in buckets_by_answer.values() if len(buckets) > 1)
  print(f'{"contrast answers":>18}: {contrast_answers}')
  years = sorted(r['date'].year for r in train)
  print(f'{"median year":>18}: {years[len(years) // 2]}')
  print(f'{"valid pairs":>18}: {len(valid)} '
        f'({len({r["answer"] for r in valid})} answers)')


if __name__ == '__main__':
  main()
