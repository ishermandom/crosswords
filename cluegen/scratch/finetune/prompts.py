# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""The frozen prompt interface between training data and eval.

The adapter learns this exact instruction; the eval client must reproduce it
verbatim, varying only the difficulty word (spec: finetune.md, "Training
prompt"). Change it and the trained adapter's behavior no longer matches — so
both the slice builder and the eval client import from here.
"""

PROMPT_TEMPLATE = 'Write a {difficulty} crossword clue for the answer: {answer}'

DIFFICULTIES = ('easy', 'medium', 'hard')
