# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Loss-gap diagnostics: is the model learning content, or only shape?

Scores the validation set's response tokens under three conditions:

- true: the real (difficulty, answer, clue) triples
- answer-shuffle: each clue paired with a random wrong answer
- difficulty-swap: each clue paired with a wrong difficulty word

A model that only learned clue *shape* scores all three about the same. The
true-vs-shuffled gap measures answer-conditional content knowledge; the
true-vs-swapped gap measures whether the difficulty token is load-bearing.
Compare the gaps for the base model vs a trained adapter: shape-only learning
shows up as "val loss fell but the gaps didn't grow".

Register control (quality, not just relevance): WordNet glosses terse enough to
pass as clue-shaped — accurate, flat definitions by construction — are scored as
the response under both 'easy' and 'hard' prompts. Absolute levels are
confounded by flat text being intrinsically predictable, so read only the
*changes* across models: a model learning quality (not flatness) lowers loss on
real clues faster than on definitions, and a working difficulty token penalizes
flat text under 'hard' more than under 'easy'.

Inference only — no training. Usage: python loss_gaps.py [--adapter DIR]
[--limit N] [--seed N]
"""

import argparse
import json
import random
import re
from pathlib import Path

import mlx.core as mx
import wn

from prompts import PROMPT_TEMPLATE

MODEL_REPO = 'mlx-community/gemma-4-12B-it-qat-OptiQ-4bit'
VALID_PATH = Path(__file__).parent / 'data_stage1' / 'valid.jsonl'
WORDNET_DATA = '/Users/Shared/data/wordnet'

# Above this, a gloss reads as prose rather than a clue — it would score badly
# on shape as well as register, which is the mismeasurement the control exists
# to avoid.
GLOSS_WORD_LIMIT = 8

# The checkpoint's model_type (gemma4_unified) needs optiq's remap; mlx-lm
# 0.31.3 alone rejects it. Private import, acceptable at the scratch bar.
from optiq.mlx_lm_patches._register import register  # noqa: E402

DIFFICULTY_SWAP = {'easy': 'hard', 'medium': 'easy', 'hard': 'medium'}


def parse_prompt(content: str) -> tuple[str, str]:
  """Recover (difficulty, answer) from the frozen template rendering."""
  difficulty = content.split('Write a ', 1)[1].split(' ', 1)[0]
  answer = content.rsplit(': ', 1)[1]
  return difficulty, answer


def terse_gloss(word: str) -> str | None:
  """A clue-shaped flat definition for `word`, or None if none is terse.

  Prefers the most-common sense; falls back to the shortest gloss. Light
  normalization mimics flat-clue conventions: leading article and trailing
  period dropped, first letter capitalized.
  """
  glosses = []
  for synset in wn.synsets(word.lower()):
    gloss = (synset.definition() or '').strip().rstrip('.')
    gloss = re.sub(r'^(a|an|the) ', '', gloss, flags=re.I)
    if gloss and '(' not in gloss:
      glosses.append(gloss)
  terse = [g for g in glosses if len(g.split()) <= GLOSS_WORD_LIMIT]
  if not terse:
    return None
  # glosses[0] is the most-common sense's; use it when it qualifies.
  best = glosses[0] if glosses[0] in terse else min(terse, key=len)
  return best[0].upper() + best[1:]


def definition_records(records: list[dict],
                       difficulty: str) -> list[list[dict]]:
  """Flat-definition controls: gloss as the response, one per answer."""
  answers = sorted({parse_prompt(r['messages'][0]['content'])[1]
                    for r in records})
  conditioned = []
  for answer in answers:
    gloss = terse_gloss(answer)
    if gloss is None:
      continue
    content = PROMPT_TEMPLATE.format(difficulty=difficulty, answer=answer)
    conditioned.append([
        {'role': 'user', 'content': content},
        {'role': 'assistant', 'content': gloss},
    ])
  return conditioned


def response_loss(model, tokenizer, messages: list[dict]) -> tuple[float, int]:
  """Per-token negative log-likelihood over the assistant response tokens."""
  prompt_ids = tokenizer.apply_chat_template(
      messages[:-1], add_generation_prompt=True)
  full_ids = tokenizer.apply_chat_template(messages)
  assert full_ids[:len(prompt_ids)] == prompt_ids, 'template prefix broke'

  logits = model(mx.array(full_ids)[None]).astype(mx.float32)
  logprobs = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
  targets = mx.array(full_ids[1:])
  per_token = logprobs[0, mx.arange(len(full_ids) - 1), targets]
  response_logprobs = per_token[len(prompt_ids) - 1:]
  negative_ll = -response_logprobs.sum()
  mx.eval(negative_ll)
  return float(negative_ll), int(response_logprobs.shape[0])


def condition_records(records: list[dict], condition: str,
                      rng: random.Random) -> list[list[dict]]:
  """Build the messages lists for one scoring condition."""
  answers = sorted({parse_prompt(r['messages'][0]['content'])[1]
                    for r in records})
  conditioned = []
  for record in records:
    difficulty, answer = parse_prompt(record['messages'][0]['content'])
    if condition == 'answer-shuffle':
      answer = rng.choice([a for a in answers if a != answer])
    elif condition == 'difficulty-swap':
      difficulty = DIFFICULTY_SWAP[difficulty]
    content = PROMPT_TEMPLATE.format(difficulty=difficulty, answer=answer)
    conditioned.append([
        {'role': 'user', 'content': content},
        record['messages'][1],
    ])
  return conditioned


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--adapter', default=None,
                      help='adapter directory; omit to score the base model')
  parser.add_argument('--limit', type=int, default=200)
  parser.add_argument('--seed', type=int, default=20260702)
  args = parser.parse_args()

  register()
  from mlx_lm import load
  model, tokenizer = load(MODEL_REPO, adapter_path=args.adapter)

  rng = random.Random(args.seed)
  all_records = [json.loads(line) for line in VALID_PATH.open()]
  rng.shuffle(all_records)
  records = all_records[:args.limit]

  label = args.adapter or 'base'
  print(f'model: {MODEL_REPO}  adapter: {label}  n={len(records)}')
  results = {}
  for condition in ('true', 'answer-shuffle', 'difficulty-swap'):
    total_nll = 0.0
    total_tokens = 0
    for messages in condition_records(records, condition, rng):
      nll, token_count = response_loss(model, tokenizer, messages)
      total_nll += nll
      total_tokens += token_count
    results[condition] = total_nll / total_tokens
    print(f'{condition:>16}: {results[condition]:.3f}')
  print(f'{"answer gap":>16}: '
        f'{results["answer-shuffle"] - results["true"]:+.3f}')
  print(f'{"difficulty gap":>16}: '
        f'{results["difficulty-swap"] - results["true"]:+.3f}')

  # Definition controls run over every val answer with a terse gloss — coverage
  # is ~20%, so subsampling by --limit would starve them.
  wn.config.data_directory = WORDNET_DATA
  for condition_label, difficulty in (('definition|easy', 'easy'),
                                      ('definition|hard', 'hard')):
    scored = definition_records(all_records, difficulty)
    total_nll = 0.0
    total_tokens = 0
    for messages in scored:
      nll, token_count = response_loss(model, tokenizer, messages)
      total_nll += nll
      total_tokens += token_count
    results[condition_label] = total_nll / total_tokens
    print(f'{condition_label:>16}: {results[condition_label]:.3f} '
          f'(n={len(scored)})')
  print(f'{"register sep":>16}: '
        f'{results["definition|easy"] - results["true"]:+.3f} '
        '(definitions minus real clues; growth across models = quality)')
  print(f'{"flat@hard penalty":>17}: '
        f'{results["definition|hard"] - results["definition|easy"]:+.3f}')


if __name__ == '__main__':
  main()
