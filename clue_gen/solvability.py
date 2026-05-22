# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Blind solvability validation call."""

from clue_gen.client import ChatClient
from clue_gen.prompt import Difficulty

# Rank threshold for a solvability pass; answer must appear at or above this
# position in the length-filtered guess list.
# TODO: calibrate against a golden set; see validation.md — "Open questions".
DEFAULT_MAX_ANSWER_RANK: int = 10


def validate_solvability(
  clue_text: str,
  answer: str,
  difficulty: Difficulty,
  client: ChatClient,
  max_answer_rank: int = DEFAULT_MAX_ANSWER_RANK,
) -> bool:
  """Run the blind solvability call and return pass/fail.

  The answer word is withheld from the prompt; the model guesses as a solver
  would. Returns True if the answer appears within the top max_answer_rank
  length-filtered guesses.
  """
  # TODO: build multi-turn solvability prompt (system persona + style hint,
  #   Turn 1 scratchpad, Turn 2 guess list); see validation.md — "Solvability
  #   call"
  # TODO: call client.chat() for Turn 1 (scratchpad), then Turn 2 (guesses)
  # TODO: strip markdown fences; parse guesses list with retry loop on failure
  # TODO: filter guesses to len(answer) characters
  # TODO: find answer position in filtered list (1-indexed); return whether
  #   it is present and at or above max_answer_rank
  raise NotImplementedError
