# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Build the stage-0 fine-tuning slice from the xd clue corpus.

Stage-0 plumbing only: any clean ~500-pair slice suffices — real curation
(source choice, quality filters, difficulty conditioning) is the data design
round's scope. One clue per answer so the answer-level train/valid split is
trivial and no answer leaks across the split. Panel and held-out answers
(reserved by the eval harness) are excluded entirely.

Output: mlx-lm chat-format JSONL (train.jsonl / valid.jsonl) in data/ next to
this script. mlx_lm.lora applies the checkpoint's own chat template to
messages-format data at training time, so no Gemma turn tags appear here.
"""

import json
import random
from pathlib import Path

XD_CLUES_PATH = Path('/Users/Shared/data/xd/clues.tsv')
OUTPUT_DIR = Path(__file__).parent / 'data'

# Answers the eval harness reserves: the 12-word iteration panel
# (scratch/eval_panel.py) and the 8 held-out words (ceiling-log.md). Training
# must never see them.
EXCLUDED_ANSWERS = {
    'SCORE', 'DAISY', 'GRANT', 'CHECK', 'GASP', 'AMBER',
    'TWENTY', 'GROSS', 'PAIR', 'VIOLET', 'ROBIN', 'STOCK',
    'COURT', 'SUE', 'HAZEL', 'SECOND', 'ZED', 'FORTY', 'DOZEN', 'NINETEEN',
}

TRAIN_ANSWER_COUNT = 500
VALID_ANSWER_COUNT = 50
RESERVOIR_SIZE = 20_000
SEED = 20260702

PROMPT_TEMPLATE = 'Write a crossword clue for the answer: {answer}'


def is_eligible(answer: str, clue: str) -> bool:
  """Cheap cleanliness filters — not curation, just obvious junk removal."""""
  return (answer.isalpha() and answer.isascii() and 3 <= len(answer) <= 10
          and answer.upper() not in EXCLUDED_ANSWERS
          and 5 <= len(clue) <= 120
          # Self-referential clues teach the wrong task.
          and answer.lower() not in clue.lower())


def sample_rows() -> list[tuple[str, str]]:
  """Reservoir-sample eligible (answer, clue) rows from the full corpus."""
  rng = random.Random(SEED)
  reservoir: list[tuple[str, str]] = []
  seen = 0
  with XD_CLUES_PATH.open(encoding='utf-8', errors='replace') as file:
    next(file)  # header: pubid, year, answer, clue
    for line in file:
      fields = line.rstrip('\n').split('\t')
      if len(fields) != 4:
        continue
      answer, clue = fields[2].strip().upper(), fields[3].strip()
      if not is_eligible(answer, clue):
        continue
      seen += 1
      if len(reservoir) < RESERVOIR_SIZE:
        reservoir.append((answer, clue))
      else:
        slot = rng.randrange(seen)
        if slot < RESERVOIR_SIZE:
          reservoir[slot] = (answer, clue)
  return reservoir


def main() -> None:
  rows = sample_rows()

  # One clue per answer: dedupe after shuffling so the kept clue is random.
  rng = random.Random(SEED + 1)
  rng.shuffle(rows)
  by_answer: dict[str, str] = {}
  for answer, clue in rows:
    by_answer.setdefault(answer, clue)

  answers = sorted(by_answer)
  rng.shuffle(answers)
  wanted = TRAIN_ANSWER_COUNT + VALID_ANSWER_COUNT
  if len(answers) < wanted:
    raise SystemExit(f'only {len(answers)} distinct answers, need {wanted}')
  train_answers = answers[:TRAIN_ANSWER_COUNT]
  valid_answers = answers[TRAIN_ANSWER_COUNT:wanted]

  OUTPUT_DIR.mkdir(exist_ok=True)
  for name, split in [('train', train_answers), ('valid', valid_answers)]:
    path = OUTPUT_DIR / f'{name}.jsonl'
    with path.open('w', encoding='utf-8') as file:
      for answer in split:
        record = {'messages': [
            {'role': 'user',
             'content': PROMPT_TEMPLATE.format(answer=answer)},
            {'role': 'assistant', 'content': by_answer[answer]},
        ]}
        file.write(json.dumps(record, ensure_ascii=False) + '\n')
    print(f'{path.name}: {len(split)} pairs')


if __name__ == '__main__':
  main()
