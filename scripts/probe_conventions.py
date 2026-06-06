# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Probe all five conventions in a single turn.

Compare against probe_wordplay.py to see whether multi-convention context
affects reasoning quality on convention 2 (wordplay indicator).

Usage:
  python scripts/probe_conventions.py
  python scripts/probe_conventions.py --clue "Keeps time?" --answer CLOCK
  python scripts/probe_conventions.py --day fri --model gemma4:31b-mlx
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
For each convention below: is it satisfied by this clue? Reason step by step,
then give a verdict: PASS or FAIL.

1. Tense and number agreement: the clue's grammatical form must agree with the
   answer (plural answer → plural clue surface; verb answer → matching tense).
2. Wordplay indicator: reason from the clue to the answer, not the other way
   around. Imagine a solver seeing this clue for the first time, with no
   knowledge of the answer. Ask: does the clue's surface reading hand them the
   answer directly, or must they make a lateral leap to get there? A ? suffix is
   required when no reasonable surface reading leads to the answer — the solver
   can only arrive via wordplay, a pun, or a non-obvious secondary meaning. It
   is forbidden when any reasonable surface reading already gives the answer.
   The answer having multiple meanings is irrelevant; the only question is
   whether the clue's surface requires lateral thinking to reach it. A ? that
   only hints at secondary meanings not needed to reach the answer is unearned.
   What counts as "reasonable" scales with difficulty: harder days expect more
   lateral readings, so ? appears less often on Friday/Saturday.
3. Abbreviation signaling: any abbreviation in the answer must be signaled in
   the clue (e.g. "Abbr.", "briefly", or an abbreviated word in the clue). If
   the answer is not an abbreviation, this passes automatically.
4. Fill-in-the-blank format: blanks must be rendered as ___. If the clue has
   no fill blank, this passes automatically.
5. Genuine alternatives: the alternative answers a solver would consider must
   be real words or phrases, not invented by the clue."""

if __name__ == '__main__':
  harness.run('conventions', _SYSTEM_PROMPT_TEMPLATE, _USER_PROMPT)
