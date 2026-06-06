# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Probe the wordplay-indicator convention in isolation.

Evaluates whether a clue's ? suffix is earned or unearned, without the
distraction of the other four conventions. Compare against probe_conventions.py
to see whether multi-convention context affects reasoning quality.

Usage:
  python scripts/probe_wordplay.py
  python scripts/probe_wordplay.py --clue "Keeps time?" --answer CLOCK
  python scripts/probe_wordplay.py --day fri --model qwen3.5:9b
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib import harness

_SYSTEM_PROMPT_TEMPLATE = """\
You are an experienced NYT crossword editor reviewing clues for publication.
Your role is quality gatekeeping: catch errors before they reach solvers. The
submission comes from a well-intentioned but inexperienced constructor — expect
mistakes, and apply each standard rigorously. A clue passes only when it
genuinely satisfies the requirement, not when a justification can be found for
it.

Target day: {day}"""

_USER_PROMPT = """\
Evaluate the wordplay indicator convention for this clue. Reason step by step,
then give a verdict: PASS or FAIL.

Wordplay indicator: reason from the clue to the answer, not the other way
around. Imagine a solver seeing this clue for the first time, with no knowledge
of the answer. Ask: does the clue's surface reading hand them the answer
directly, or must they make a lateral leap to get there? A ? suffix is required
when no reasonable surface reading leads to the answer — the solver can only
arrive via wordplay, a pun, or a non-obvious secondary meaning. It is forbidden
when any reasonable surface reading already gives the answer. The answer having
multiple meanings is irrelevant; the only question is whether the clue's surface
requires lateral thinking to reach it. A ? that only hints at secondary meanings
not needed to reach the answer is unearned. What counts as "reasonable" scales
with difficulty: harder days expect more lateral readings, so ? appears less
often on Friday/Saturday.

Examples:

Earned (? required):
- "Semi professional?" → TEAMSTER: The surface ("partly professional") gives
  no path to TEAMSTER. Only once you pivot — "semi" = semi-truck, TEAMSTER =
  professional truck driver — does the answer emerge. ? is required.
- "Perpetual homebody?" → SNAIL: The surface ("someone who never goes out")
  gives no path to SNAIL. The pivot: take "homebody" literally — a snail
  carries its home on its body. ? is required.

Unearned (? forbidden):
- "Keeps time?" → CLOCK: Keeping time is a clock's primary function. The
  surface delivers directly. ? is unearned even though CLOCK has other meanings;
  those meanings aren't needed to reach the answer.
- "Points the way?" → COMPASS: Pointing a direction is what a compass does.
  The surface leads straight to the answer. ? is unearned.
- "Draws blood?" → NEEDLE: Drawing blood is what a needle does in its most
  common use. The surface delivers directly. ? is unearned."""

if __name__ == '__main__':
  harness.run('wordplay', _SYSTEM_PROMPT_TEMPLATE, _USER_PROMPT)
