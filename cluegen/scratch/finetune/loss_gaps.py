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

Inference only — no training. Usage: python loss_gaps.py [--adapter DIR]
[--limit N] [--seed N]
"""

import argparse
import json
import random
from pathlib import Path

import mlx.core as mx

from prompts import PROMPT_TEMPLATE

MODEL_REPO = 'mlx-community/gemma-4-12B-it-qat-OptiQ-4bit'
VALID_PATH = Path(__file__).parent / 'data_stage1' / 'valid.jsonl'

# The checkpoint's model_type (gemma4_unified) needs optiq's remap; mlx-lm
# 0.31.3 alone rejects it. Private import, acceptable at the scratch bar.
from optiq.mlx_lm_patches._register import register  # noqa: E402

DIFFICULTY_SWAP = {'easy': 'hard', 'medium': 'easy', 'hard': 'medium'}


def parse_prompt(content: str) -> tuple[str, str]:
  """Recover (difficulty, answer) from the frozen template rendering."""
  difficulty = content.split('Write a ', 1)[1].split(' ', 1)[0]
  answer = content.rsplit(': ', 1)[1]
  return difficulty, answer


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
  records = [json.loads(line) for line in VALID_PATH.open()]
  rng.shuffle(records)
  records = records[:args.limit]

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


if __name__ == '__main__':
  main()
