# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Blind solvability validation call."""

from dataclasses import dataclass

from clue_gen.client import ChatClient
from clue_gen.prompt import Difficulty

# Rank threshold for a solvability pass; answer must appear at or above this
# position in the length-filtered guess list.
# TODO: calibrate against a golden set; see validation.md — "Open questions".
DEFAULT_MAX_ANSWER_RANK: int = 10


@dataclass(frozen=True)
class SolvabilityResult:
  """Outcome of the blind solvability call for one clue."""

  # True if the answer appeared within the top max_answer_rank filtered guesses.
  is_solvable: bool
  # Position of the target answer among length-filtered guesses (1-indexed).
  # None if the answer did not appear in the guess list at all.
  answer_rank: int | None


def validate_solvability(
  clue_text: str,
  answer: str,
  difficulty: Difficulty,
  client: ChatClient,
  max_answer_rank: int = DEFAULT_MAX_ANSWER_RANK,
) -> SolvabilityResult:
  """Run the blind solvability call and return a pass/fail result with rank.

  The answer word is withheld from the prompt; the model guesses as a solver
  would. Passes if the answer appears within the top max_answer_rank
  length-filtered guesses.
  """
  # TODO: build multi-turn solvability prompt (system persona + style hint,
  #   Turn 1 scratchpad, Turn 2 guess list); see validation.md — "Solvability
  #   call"
  # TODO: call client.chat() for Turn 1 (scratchpad), then Turn 2 (guesses)
  # TODO: strip markdown fences; parse guesses list with retry loop on failure
  # TODO: filter guesses to len(answer) characters
  # TODO: find answer_rank in filtered list (1-indexed; None if absent)
  # TODO: return SolvabilityResult(is_solvable=answer_rank <= max_answer_rank,
  #   answer_rank=answer_rank)
  raise NotImplementedError
