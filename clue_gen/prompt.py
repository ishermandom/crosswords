# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Prompt construction for clue generation.

Prompt content is placeholder — actual prompt design is Phase 3.
"""

import enum
from collections.abc import Sequence

from clue_gen.client import Message


class Difficulty(enum.StrEnum):
  """NYT crossword difficulty levels, from easiest to hardest."""

  MON = 'Mon'
  TUE = 'Tue'
  WED = 'Wed'
  THU = 'Thu'
  FRI = 'Fri'
  SAT = 'Sat'


# TODO: Calibrate day descriptions against real clue examples. The key axes
# are misdirection level, whether the obvious reading should be correct, and
# what reference breadth is appropriate. Update after prototyping validation.
_DAY_DESCRIPTIONS: dict[Difficulty, str] = {
  Difficulty.MON: (
    'Target: Monday. Write direct, unambiguous clues. The surface reading '
    'should lead to the answer without lateral thinking. Wordplay is '
    'acceptable only when the mechanism is immediately apparent.'
  ),
  Difficulty.TUE: (
    'Target: Tuesday. Mild misdirection is welcome — the surface can suggest '
    'one domain while the answer comes from another, but the connection '
    'should click quickly for a practiced solver.'
  ),
  Difficulty.WED: (
    'Target: Wednesday. Deliberate misdirection or wordplay is expected. '
    'The surface should confidently suggest one reading before the answer '
    'snaps into place. References may be moderately niche.'
  ),
  Difficulty.THU: (
    'Target: Thursday. Strong misdirection is the goal. The surface should '
    'lead firmly elsewhere before the pivot. Clues reward lateral thinking; '
    'a novice solver should struggle, an experienced one should enjoy the '
    'aha. Aim for elegant ambiguity that resolves through crosses — a small '
    'cloud of plausible answers that collapses to one.'
  ),
  Difficulty.FRI: (
    'Target: Friday. Complex wordplay and creative angles. The surface '
    'should feel natural while pointing decisively wrong. The obvious answer '
    'is usually wrong. References can draw on mid-range specialist knowledge. '
    'Aim for elegant ambiguity that resolves through crosses.'
  ),
  Difficulty.SAT: (
    'Target: Saturday. Maximum difficulty. The surface should be polished '
    'and natural while misleading as completely as possible. Specialist or '
    'niche references are fair game. Every angle of wordplay is available. '
    'The obvious answer is almost always wrong.'
  ),
}

_BRAINSTORM_SYSTEM_PROMPT_TEMPLATE = """\
You are an experienced NYT crossword constructor. You write clues that are \
fair and rewarding to solve — once the trick is seen, the connection must \
be clear and unambiguous in hindsight.

{day_description}"""


def brainstorm_system_prompt(difficulty: Difficulty) -> str:
  """Build the system prompt for the multi-turn brainstorm conversation."""
  return _BRAINSTORM_SYSTEM_PROMPT_TEMPLATE.format(
    day_description=_DAY_DESCRIPTIONS[difficulty]
  )


def brainstorm_turns(word: str, difficulty: Difficulty) -> Sequence[str]:
  """Return the 7 user-turn strings for the multi-turn brainstorm sequence.

  Each string is one user message in the accumulated conversation. The caller
  is responsible for appending assistant replies and building the messages list.
  Turn order: answer analysis → mechanism brainstorm → mechanism filter →
  clue drafting → solver simulation → refinement/diversity → extract.
  """
  raise NotImplementedError


def brainstorm_messages(word: str, difficulty: Difficulty) -> Sequence[Message]:
  """Build the opening brainstorm turn for a given answer word.

  Returns a single-message list; the caller may append further turns to
  continue the conversation. Prompt content is a placeholder for Phase 3.
  """
  desc = _DAY_DESCRIPTIONS[difficulty]
  return [
    {
      'role': 'user',
      'content': (
        f'Generate crossword clue candidates for the answer word: {word}\n'
        f'Target difficulty: {difficulty}\n{desc}\n\n'
        'Consider a variety of styles: straight definition, '
        'fill-in-the-blank, wordplay or double meaning, light cryptic '
        'element, and trivia. Produce three to five distinct candidate clues.'
      ),
    },
  ]


def validation_messages(clue: str, answer_length: int) -> Sequence[Message]:
  """Build the opening validation turn for a single candidate clue.

  Presents only what a real solver would see: the clue and the answer length.
  The answer word and difficulty target are intentionally excluded — the
  validator must solve blind. Returns a single-message list for an independent
  API call; the caller may append further turns. Prompt is a placeholder for
  Phase 3.
  """
  blanks = '_' * answer_length
  return [
    {
      'role': 'user',
      'content': (
        'You are solving a crossword clue. '
        f'The answer is {answer_length} letters long ({blanks}).\n\n'
        f'Clue: {clue}\n\n'
        'Generate several candidate answers. For each candidate, evaluate '
        'whether this clue would be fair, unambiguous, and compelling if that '
        'were the correct answer. Respond with JSON only:\n'
        '{"valid": true, "clue": "the clue as given or lightly edited", '
        '"answer": "your best candidate answer", '
        '"candidates": [{"answer": "...", "evaluation": "..."}]}\n'
        'If you cannot solve the clue or no candidate produces a quality clue:\n'
        '{"valid": false, "issues": ["reason 1", "reason 2"]}'
      ),
    },
  ]
