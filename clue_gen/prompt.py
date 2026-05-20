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


_DIFFICULTY_DESCRIPTIONS: dict[Difficulty, str] = {
  Difficulty.MON: 'immediately gettable; plain definitions',
  Difficulty.TUE: 'slightly tricky; mild misdirection',
  Difficulty.WED: 'moderate; some wordplay required',
  Difficulty.THU: 'fair but requires thought; misdirection and wordplay',
  Difficulty.FRI: 'hard; creative constructions and indirect definitions',
  Difficulty.SAT: 'maximum difficulty; devious and multi-layered',
}


def brainstorm_messages(word: str, difficulty: Difficulty) -> Sequence[Message]:
  """Build the opening brainstorm turn for a given answer word.

  Returns a single-message list; the caller may append further turns to
  continue the conversation. Prompt content is a placeholder for Phase 3.
  """
  desc = _DIFFICULTY_DESCRIPTIONS[difficulty]
  return [
    {
      'role': 'user',
      'content': (
        f'Generate crossword clue candidates for the answer word: {word}\n'
        f'Target difficulty: {difficulty} ({desc})\n\n'
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
