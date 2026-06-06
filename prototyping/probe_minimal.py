# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Minimal probe for iterating on reasoning-length reduction techniques.

Uses the tense-agreement turn from probe_quality_multi as a representative
case: a binary PASS/FAIL check that produced ~287 reasoning tokens in the
baseline multi-turn run, well above what the question warrants.

System prompt uses the quality-gatekeeping persona from probe_quality_single.
User prompt is the tense-agreement convention check in isolation.

Usage:
  python prototyping/probe_minimal.py
  python prototyping/probe_minimal.py --clue "Keeps time?" --answer CLOCK
  python prototyping/probe_minimal.py --model gemma4:31b-mlx
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib import harness

_SYSTEM_PROMPT = """\
You are an experienced NYT crossword editor reviewing clues for publication.
Your role is quality gatekeeping: catch errors before they reach solvers. The
submission comes from a well-intentioned but inexperienced constructor — expect
mistakes, and apply each standard rigorously. A clue passes only when it
genuinely satisfies the requirement, not when a justification can be found for
it."""

_USER_PROMPT = """\
Tense agreement: the clue's grammatical form must agree with the answer
(plural answer → plural clue surface; verb answer → matching tense).

Reply PASS or FAIL with a reason in five words or fewer.
Example: FAIL: past tense mismatches present clue."""

if __name__ == '__main__':
  args = harness.parse_args('minimal')
  turns: list[harness.SystemTurn | harness.UserTurn] = [
    harness.SystemTurn(_SYSTEM_PROMPT),
    harness.UserTurn(
      f'Clue: {args.clue}\nAnswer: {args.answer}\n\n{_USER_PROMPT}',
      use_thinking=False,
    ),
  ]
  harness.run_messages('minimal', turns, args)
