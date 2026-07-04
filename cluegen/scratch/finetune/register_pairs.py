# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Matched-pair register preference: given one answer's flat (Monday) and lively
(Saturday) real clues under the SAME hard prompt, which does the model prefer?

The loss-gap register separation says the tuned model prices real clues below
definitions, but that contrast confounds register with clue-ness. This
instrument holds the answer fixed and varies only the register: both members are
genuine NYT clues for the same answer, differing in weekday origin. A model that
has internalized difficulty conditioning should, under the hard prompt, put more
mass on the Saturday member.

Reported per model: the lively member's win rate on sequence-level NLL, the mean
sequence-level margin, and the mean per-token margin (Saturday clues skew terse,
so total NLL structurally favors them; per-token controls for length).

Usage: python register_pairs.py [--adapter DIR] [--dry-run]
"""

import argparse
import csv
import datetime
import random
import re

from abbr_probe import CSV_PATH, RESERVED_ANSWERS, stage1_answers
from loss_gaps import MODEL_REPO, response_loss
from optiq.mlx_lm_patches._register import register
from prompts import PROMPT_TEMPLATE

# Grid cross-references are meaningless outside their puzzle.
CROSS_REFERENCE = re.compile(r'\d+-(Across|Down)|\bSee \d+\b', re.IGNORECASE)

MONDAY, SATURDAY = 0, 5


def bank_weekday_clues() -> dict[str, dict[int, tuple[datetime.date, str]]]:
  """Latest clean Monday and Saturday clue per alphabetic answer."""
  latest: dict[str, dict[int, tuple[datetime.date, str]]] = {}
  with CSV_PATH.open(encoding='latin-1') as file:
    for row in csv.DictReader(file):
      answer, clue = row['Word'].strip(), row['Clue'].strip()
      if not answer or not clue or not answer.isalpha():
        continue
      # ASCII-only: the bank carries mojibake beyond the standard markers ('?Æ'
      # apostrophes), and with 16k+ pairs available purity is free.
      if not clue.isascii():
        continue
      if CROSS_REFERENCE.search(clue):
        continue
      date = datetime.datetime.strptime(row['Date'], '%m/%d/%Y').date()
      weekday = date.weekday()
      if weekday not in (MONDAY, SATURDAY):
        continue
      slot = latest.setdefault(answer, {})
      if weekday not in slot or date > slot[weekday][0]:
        slot[weekday] = (date, clue)
  return latest


def build_pairs(count: int, seed: int) -> list[dict]:
  """`count` sampled {answer, flat, lively} pairs with distinct members."""
  excluded = stage1_answers() | RESERVED_ANSWERS
  pairs = []
  for answer, slot in bank_weekday_clues().items():
    if answer in excluded or MONDAY not in slot or SATURDAY not in slot:
      continue
    flat, lively = slot[MONDAY][1], slot[SATURDAY][1]
    if flat == lively:
      continue
    pairs.append({'answer': answer, 'flat': flat, 'lively': lively})
  print(f'{len(pairs)} matched pairs available')
  rng = random.Random(seed)
  return rng.sample(pairs, min(count, len(pairs)))


def hard_messages(answer: str, clue: str) -> list[dict]:
  """Prompt/response pair in the training shape, at hard difficulty."""
  content = PROMPT_TEMPLATE.format(difficulty='hard', answer=answer)
  return [{'role': 'user', 'content': content},
          {'role': 'assistant', 'content': clue}]


def score_pairs(model, tokenizer, pairs: list[dict]) -> None:
  """Win rate and margins for the lively member under the hard prompt."""
  wins = 0
  margins = []
  per_token_margins = []
  for pair in pairs:
    flat_nll, flat_tokens = response_loss(
        model, tokenizer, hard_messages(pair['answer'], pair['flat']))
    lively_nll, lively_tokens = response_loss(
        model, tokenizer, hard_messages(pair['answer'], pair['lively']))
    margins.append(flat_nll - lively_nll)
    per_token_margins.append(
        flat_nll / flat_tokens - lively_nll / lively_tokens)
    if margins[-1] > 0:
      wins += 1
  n = len(pairs)
  print(f'lively win rate (sequence NLL): {wins}/{n} ({wins / n:.0%})')
  print(f'mean sequence margin: {sum(margins) / n:+.3f} nats '
        '(positive = prefers lively)')
  print(f'mean per-token margin: {sum(per_token_margins) / n:+.3f} '
        'nats/token')


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--adapter', default=None)
  parser.add_argument('--model', default=MODEL_REPO)
  parser.add_argument('--pair-count', type=int, default=100)
  parser.add_argument('--seed', type=int, default=20260704)
  parser.add_argument('--dry-run', action='store_true',
                      help='build and print sample pairs; no model load')
  args = parser.parse_args()

  pairs = build_pairs(args.pair_count, args.seed)
  for pair in pairs[:5]:
    print(f'  {pair["answer"]}: flat {pair["flat"]!r} '
          f'vs lively {pair["lively"]!r}')
  if args.dry_run:
    return

  register()
  from mlx_lm import load
  model, tokenizer = load(args.model, adapter_path=args.adapter)
  print(f'model: {args.model}  adapter: {args.adapter or "base"}')
  score_pairs(model, tokenizer, pairs)


if __name__ == '__main__':
  main()
