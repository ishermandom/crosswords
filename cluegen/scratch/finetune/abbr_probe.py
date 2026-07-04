# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Abbreviation-conditioning probe: has the model internalized the style rule
"abbreviated clue forms go with abbreviated answers"?

Case study for semantic style-rule learning generally (NYT style guide), with
the ': Abbr.' suffix as the cleanly measurable marker.

Two views:

- Likelihood (marker cost): for each item, score the clue with and without a ':
  Abbr.' suffix under the true answer. Delta = NLL(marked) - NLL(bare) in total
  nats. The intrinsic cost of the extra suffix tokens is common to both groups,
  so the rule shows up as delta(full-word answers) >> delta (abbreviation
  answers) — the diff-of-diffs. Compare base vs tuned to see what fine-tuning
  taught.

- Generation: sample clues per answer and count explicit 'Abbr' markers. Rule
  internalized = high marker rate for abbreviation answers, ~zero for full-word
  answers.

Groups are drawn bank-wide from the Kaggle NYT CSV, excluding every stage-1
train/valid answer (no memorized clues) and the panel/held-out words.
Abbreviation group: clues ending ': Abbr.' (bare variant = suffix stripped).
Full-word group: WordNet-known answers with terse, marker-free clues.

Usage: python abbr_probe.py [--adapter DIR] [--skip-generate]
"""

import argparse
import csv
import datetime
import json
import random
import re
from pathlib import Path

import wn

from loss_gaps import MODEL_REPO, WORDNET_DATA, response_loss
from optiq.mlx_lm_patches._register import register
from prompts import PROMPT_TEMPLATE

CSV_PATH = Path('/Users/Shared/data/kaggle-nyt/nytcrosswords.csv')
DATA_DIR = Path(__file__).parent / 'data_stage1'

MARKER = ': Abbr.'
MARKER_SUFFIX = re.compile(r':\s*Abbr\.$')
MARKER_ANYWHERE = re.compile(r'\bAbbr\b')
MOJIBAKE_MARKERS = ('â€', 'Â', '�')

# Panel + held-out answers (build_stage1_slice.py EXCLUDED_ANSWERS): reserved
# for evals, keep them out of instrument data too.
RESERVED_ANSWERS = {
    'SCORE', 'DAISY', 'GRANT', 'CHECK', 'GASP', 'AMBER',
    'TWENTY', 'GROSS', 'PAIR', 'VIOLET', 'ROBIN', 'STOCK',
    'COURT', 'SUE', 'HAZEL', 'SECOND', 'ZED', 'FORTY', 'DOZEN', 'NINETEEN',
}


def stage1_answers() -> set[str]:
  """Every answer in the stage-1 train/valid sets (their clues may be memorized,
  which would contaminate likelihood scores).
  """
  answers = set()
  for name in ('train.jsonl', 'valid.jsonl'):
    for line in (DATA_DIR / name).open():
      content = json.loads(line)['messages'][0]['content']
      answers.add(content.rsplit(': ', 1)[1])
  return answers


def bank_rows() -> dict[str, tuple[datetime.date, str]]:
  """Most-recent clean clue per answer from the bank CSV."""
  latest: dict[str, tuple[datetime.date, str]] = {}
  with CSV_PATH.open(encoding='latin-1') as file:
    for row in csv.DictReader(file):
      answer, clue = row['Word'].strip(), row['Clue'].strip()
      if not answer or not clue:
        continue
      if any(marker in clue for marker in MOJIBAKE_MARKERS):
        continue
      date = datetime.datetime.strptime(row['Date'], '%m/%d/%Y').date()
      if answer not in latest or date > latest[answer][0]:
        latest[answer] = (date, clue)
  return latest


def build_groups(group_size: int, seed: int) -> dict[str, list[dict]]:
  """Sampled (answer, bare clue) items for both groups."""
  wn.config.data_directory = WORDNET_DATA
  excluded = stage1_answers() | RESERVED_ANSWERS
  abbreviation, full_word = [], []
  for answer, (date, clue) in bank_rows().items():
    if answer in excluded or not answer.isalpha():
      continue
    if MARKER_SUFFIX.search(clue):
      bare = MARKER_SUFFIX.sub('', clue).strip()
      if bare and not MARKER_ANYWHERE.search(bare):
        abbreviation.append({'answer': answer, 'clue': bare})
    elif (4 <= len(answer) <= 8
          and not MARKER_ANYWHERE.search(clue)
          and '.' not in clue and ':' not in clue
          and len(clue.split()) <= 8
          and wn.synsets(answer.lower())):
      full_word.append({'answer': answer, 'clue': clue})
  rng = random.Random(seed)
  return {'abbreviation': rng.sample(abbreviation, group_size),
          'full_word': rng.sample(full_word, group_size)}


def clue_messages(answer: str, clue: str) -> list[dict]:
  """Prompt/response pair in the training shape, at medium difficulty."""
  content = PROMPT_TEMPLATE.format(difficulty='medium', answer=answer)
  return [{'role': 'user', 'content': content},
          {'role': 'assistant', 'content': clue}]


def score_marker_cost(model, tokenizer, groups: dict) -> None:
  """Per-group marker cost and the diff-of-diffs."""
  means = {}
  for group_name, items in groups.items():
    deltas = []
    for item in items:
      bare_nll, _ = response_loss(
          model, tokenizer, clue_messages(item['answer'], item['clue']))
      marked_nll, _ = response_loss(
          model, tokenizer,
          clue_messages(item['answer'], item['clue'] + MARKER))
      deltas.append(marked_nll - bare_nll)
    means[group_name] = sum(deltas) / len(deltas)
    prefer_marked = sum(1 for d in deltas if d < 0) / len(deltas)
    print(f'{group_name:>14}: marker cost {means[group_name]:+.3f} nats '
          f'(n={len(deltas)}, prefers marked {prefer_marked:.0%})')
  print(f'{"diff-of-diffs":>14}: '
        f'{means["full_word"] - means["abbreviation"]:+.3f} '
        '(rule internalized => strongly positive)')


def sample_generations(model, tokenizer, groups: dict, per_group: int,
                       samples: int) -> None:
  """Marker rate in sampled clues, per answer group."""
  from mlx_lm import generate
  from mlx_lm.sample_utils import make_sampler

  for group_name, items in groups.items():
    marked = 0
    examples = []
    for item in items[:per_group]:
      content = PROMPT_TEMPLATE.format(difficulty='medium',
                                       answer=item['answer'])
      prompt = tokenizer.apply_chat_template(
          [{'role': 'user', 'content': content}], add_generation_prompt=True)
      for _ in range(samples):
        text = generate(model, tokenizer, prompt=prompt,
                        sampler=make_sampler(temp=1.0), max_tokens=25)
        if MARKER_ANYWHERE.search(text):
          marked += 1
          examples.append(f'{item["answer"]}: {text!r}')
    total = per_group * samples
    print(f'{group_name:>14}: marker rate {marked}/{total} '
          f'({marked / total:.0%})')
    for example in examples[:5]:
      print(f'                {example}')


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--adapter', default=None)
  parser.add_argument('--model', default=MODEL_REPO)
  parser.add_argument('--group-size', type=int, default=40)
  parser.add_argument('--generate-count', type=int, default=20)
  parser.add_argument('--samples', type=int, default=3)
  parser.add_argument('--seed', type=int, default=20260704)
  parser.add_argument('--skip-generate', action='store_true')
  args = parser.parse_args()

  groups = build_groups(args.group_size, args.seed)
  for group_name, items in groups.items():
    print(f'{group_name}: {len(items)} items, e.g. '
          f'{items[0]["answer"]} / {items[0]["clue"]!r}')

  register()
  from mlx_lm import load
  model, tokenizer = load(args.model, adapter_path=args.adapter)
  print(f'model: {args.model}  adapter: {args.adapter or "base"}')

  score_marker_cost(model, tokenizer, groups)
  if not args.skip_generate:
    sample_generations(model, tokenizer, groups, args.generate_count,
                       args.samples)


if __name__ == '__main__':
  main()
