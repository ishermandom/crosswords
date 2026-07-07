# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Generate through the same direct-load path loss_gaps.py scores with.

The serve path produced a single degenerate output ('An double') for every
prompt even at temperature 1.0, which contradicts the 5.83-nat scoring of the
same adapter. This probe generates via mlx_lm.load(adapter_path=...) — the
scorer's exact load path — to tell a serve-side adapter misapplication apart
from a genuinely degenerate adapter.

Usage: python gen_probe.py [adapter_dir] [model_repo]
"""

import sys

from optiq.mlx_lm_patches._register import register
from prompts import PROMPT_TEMPLATE


def main() -> None:
  register()
  from mlx_lm import load, generate
  from mlx_lm.sample_utils import make_sampler

  adapter = sys.argv[1] if len(sys.argv) > 1 else 'adapters/adapters_12b_stage1/best'
  model_repo = (sys.argv[2] if len(sys.argv) > 2
                else 'mlx-community/gemma-4-12B-it-qat-OptiQ-4bit')
  model, tokenizer = load(model_repo, adapter_path=adapter)
  print(f'model: {model_repo}  adapter: {adapter}', flush=True)

  for answer in ('VIOLET', 'SCORE'):
    content = PROMPT_TEMPLATE.format(difficulty='medium', answer=answer)
    prompt = tokenizer.apply_chat_template(
        [{'role': 'user', 'content': content}], add_generation_prompt=True)
    for temperature in (0.0, 1.0, 1.0, 1.0):
      text = generate(model, tokenizer, prompt=prompt,
                      sampler=make_sampler(temp=temperature), max_tokens=30)
      print(f'{answer} temp={temperature}: {text!r}', flush=True)


main()
