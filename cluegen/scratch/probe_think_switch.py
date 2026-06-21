# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Probe the cost of switching between thinking and non-thinking mode.

Runs 10 trivial tasks in an AABBAABB pattern (two consecutive turns per
mode before switching), so each mode has both a first-in-mode turn and a
warmed-up consecutive turn. This distinguishes switching overhead from
steady-state cost.

Measurement strategy: the key signal is excess wall time over norm_wall.
norm_wall accounts for prefill and generation token counts, so anything
above it reflects overhead not explained by compute — e.g. model
reconfiguration on a mode switch. Watch norm_wall rise across turns as
the shared history grows; that growth is expected and not a cost of
switching.

Caveats:
  - Turn 1 may be slow if the model isn't already warm from a prior run.
  - Tasks are non-crossword to avoid any domain-specific reasoning bias.
  - Clue/answer CLI args are accepted but unused (harness requirement).

Usage:
  python cluegen/scratch/probe_think_switch.py
  python cluegen/scratch/probe_think_switch.py --model gemma4:31b-mlx
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cluegen.scratch.lib import harness

# AABBAABB pattern: (use_thinking, question)
_TURNS: list[tuple[bool, str]] = [
  (True, 'Is 7 a prime number? Reply Yes or No.'),
  (True, 'Is Antarctica a continent? Reply Yes or No.'),
  (False, 'What is 3 x 4? Reply with the number only.'),
  (False, 'What color is grass? One word.'),
  (True, 'Is a whale a mammal? Reply Yes or No.'),
  (True, 'Is 1000 greater than 999? Reply Yes or No.'),
  (False, 'What is 100 ÷ 4? Reply with the number only.'),
  (False, 'What is the opposite of wet? One word.'),
  (True, 'Is the sun a star? Reply Yes or No.'),
  (False, 'What is 8 x 8? Reply with the number only.'),
]

if __name__ == '__main__':
  args = harness.parse_args('think-switch')
  turns: list[harness.SystemTurn | harness.UserTurn] = [
    harness.SystemTurn('Answer each question directly and briefly.'),
    *[
      harness.UserTurn(question, use_thinking=use_thinking)
      for use_thinking, question in _TURNS
    ],
  ]
  harness.run_messages('think-switch', turns, args)
