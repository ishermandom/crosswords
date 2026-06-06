# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Minimal probe for diagnosing reasoning doubling and overhead.

Two boolean fields, no rubric scales, no format key. Intended to be the
smallest structured evaluation that still resembles the production task,
so we can observe whether doubling and overhead are tied to evaluation
structure vs. JSON schema enforcement.

Usage:
  python scripts/probe_minimal.py
  python scripts/probe_minimal.py --clue "Keeps time?" --answer CLOCK
  python scripts/probe_minimal.py --model gemma4:31b-mlx
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib import harness

_SYSTEM_PROMPT_TEMPLATE = """\
You are an experienced NYT crossword editor reviewing clues for
publication. Apply each standard rigorously.

Target day: {day}"""

_USER_PROMPT = """\
Respond with JSON only:
{"has_tense_agreement": boolean, "has_genuine_alternatives": boolean}

has_tense_agreement: the clue's grammatical form must agree with the
answer (plural answer → plural clue; verb answer → matching tense).

has_genuine_alternatives: alternative answers a solver would consider
must be real words or phrases, not invented by the clue.
"""

if __name__ == '__main__':
  harness.run(
    'minimal',
    _SYSTEM_PROMPT_TEMPLATE,
    _USER_PROMPT,
  )
