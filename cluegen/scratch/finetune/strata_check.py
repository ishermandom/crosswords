# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Stratified false-signal check: where do spurious abbreviation signals
cluster?

The flat n=60 probe put the false-signal rate on full-word answers at 0/60, yet
the founding observations (SCORE -> 'Rating: Abbr.', VIOLET -> 'Chrys.
relative') show they happen. Hypothesis (the VIOLET collision theory): the
strongly-learned terseness rule beats the weakly-held form-matching rule
precisely when the answer's best clue ideas need a long word — the model
truncates it. If so, false signals should concentrate in a stratum of answers
whose natural clue vocabulary is long words, and stay near zero elsewhere.

Three disjoint strata of full-word answers (never ': Abbr.'-tagged bank-wide,
WordNet-known, stage-1 and reserved answers excluded):

- long_word_concept: at least half the answer's distinct bank clues contain a
  10+-letter word (flower/genus, occupation, nationality territory).
- polysemous: many distinct bank clues (many senses to clue from — the SCORE
  shape).
- easy: terse latest clue (<= 3 words), qualifying for neither stratum above —
  the baseline population.

Draw N clues per answer from the tuned model, count abbreviation signals via the
probe's `is_signaled`, and compare rates across strata.

Usage: python strata_check.py [--adapter DIR] [--dry-run]
"""

import argparse
import csv
import random
import re

import wn

from abbr_probe import (CSV_PATH, MARKER_SUFFIX, MOJIBAKE_MARKERS,
                        RESERVED_ANSWERS, is_signaled, stage1_answers)
from loss_gaps import MODEL_REPO, WORDNET_DATA
from optiq.mlx_lm_patches._register import register
from prompts import PROMPT_TEMPLATE

LONG_WORD = re.compile(r'[A-Za-z]{10,}')

# Distinct-clue count that qualifies an answer as polysemous. Crossword
# workhorses (ERA, ALOE) clear 50+; 15 keeps the stratum to genuinely many-sense
# words without starving it.
POLYSEMOUS_MINIMUM_CLUES = 15

TERSE_WORD_LIMIT = 3


def bank_full_word_answers() -> dict[str, list[str]]:
  """Distinct clean clues per candidate answer (4-8 letters, alphabetic, never
  ': Abbr.'-tagged anywhere in the bank).
  """
  clues: dict[str, set[str]] = {}
  tagged: set[str] = set()
  with CSV_PATH.open(encoding='latin-1') as file:
    for row in csv.DictReader(file):
      answer, clue = row['Word'].strip(), row['Clue'].strip()
      if not answer or not clue:
        continue
      if any(marker in clue for marker in MOJIBAKE_MARKERS):
        continue
      if MARKER_SUFFIX.search(clue):
        tagged.add(answer)
      if not answer.isalpha() or not 4 <= len(answer) <= 8:
        continue
      clues.setdefault(answer, set()).add(clue)
  return {answer: sorted(clue_set) for answer, clue_set in clues.items()
          if answer not in tagged}


def build_strata(stratum_size: int, seed: int) -> dict[str, list[str]]:
  """Sampled answer lists per stratum, disjoint by construction.

  Priority long_word_concept > polysemous > easy: an answer qualifying for an
  earlier stratum is removed from later ones, so `easy` is a clean baseline.
  """
  wn.config.data_directory = WORDNET_DATA
  excluded = stage1_answers() | RESERVED_ANSWERS
  bank = bank_full_word_answers()

  strata: dict[str, list[str]] = {
      'long_word_concept': [], 'polysemous': [], 'easy': []}
  for answer, clues in bank.items():
    if answer in excluded or not wn.synsets(answer.lower()):
      continue
    long_word_share = sum(
        1 for clue in clues if LONG_WORD.search(clue)) / len(clues)
    if len(clues) >= 3 and long_word_share >= 0.5:
      strata['long_word_concept'].append(answer)
    elif len(clues) >= POLYSEMOUS_MINIMUM_CLUES:
      strata['polysemous'].append(answer)
    elif len(clues[-1].split()) <= TERSE_WORD_LIMIT:
      # Note: clues are sorted, so [-1] is an arbitrary stable pick, not the
      # most recent — terseness of any one clue suffices for the baseline.
      strata['easy'].append(answer)

  rng = random.Random(seed)
  sampled = {}
  for stratum, answers in strata.items():
    print(f'{stratum}: {len(answers)} candidates')
    sampled[stratum] = sorted(rng.sample(answers,
                                         min(stratum_size, len(answers))))
  return sampled


def show_strata(strata: dict[str, list[str]],
                bank: dict[str, list[str]]) -> None:
  """Print each stratum's answers with one example bank clue apiece."""
  for stratum, answers in strata.items():
    print(f'\n{stratum} ({len(answers)} answers):')
    for answer in answers:
      example = bank[answer][0]
      print(f'  {answer}: {example!r} ({len(bank[answer])} distinct clues)')


def sample_stratum(model, tokenizer, answers: list[str],
                   samples: int) -> None:
  """Signal rate over `samples` draws per answer; every hit printed."""
  from mlx_lm import generate
  from mlx_lm.sample_utils import make_sampler

  signaled = 0
  hits = []
  for answer in answers:
    content = PROMPT_TEMPLATE.format(difficulty='medium', answer=answer)
    prompt = tokenizer.apply_chat_template(
        [{'role': 'user', 'content': content}], add_generation_prompt=True)
    for _ in range(samples):
      text = generate(model, tokenizer, prompt=prompt,
                      sampler=make_sampler(temp=1.0), max_tokens=25)
      if is_signaled(text):
        signaled += 1
        hits.append(f'{answer}: {text!r}')
  total = len(answers) * samples
  print(f'  signal rate {signaled}/{total} ({signaled / total:.0%})')
  for hit in hits:
    print(f'    {hit}')


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--adapter', default=None)
  parser.add_argument('--model', default=MODEL_REPO)
  parser.add_argument('--stratum-size', type=int, default=20)
  parser.add_argument('--samples', type=int, default=5)
  parser.add_argument('--seed', type=int, default=20260704)
  parser.add_argument('--dry-run', action='store_true',
                      help='build and print strata; no model load')
  args = parser.parse_args()

  strata = build_strata(args.stratum_size, args.seed)
  if args.dry_run:
    show_strata(strata, bank_full_word_answers())
    return

  register()
  from mlx_lm import load
  model, tokenizer = load(args.model, adapter_path=args.adapter)
  print(f'model: {args.model}  adapter: {args.adapter or "base"}')

  for stratum, answers in strata.items():
    print(f'\n{stratum}:')
    sample_stratum(model, tokenizer, answers, args.samples)


if __name__ == '__main__':
  main()
