# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Combined validation: wires solvability and quality calls into one result."""

from dataclasses import dataclass

from clue_gen.client import ChatClient
from clue_gen.prompt import Difficulty
from clue_gen.quality import QualityResult
from clue_gen.solvability import DEFAULT_MAX_ANSWER_RANK


@dataclass(frozen=True)
class ValidationResult:
  """Combined outcome of both validation calls for one clue."""

  # True only when both the solvability and quality calls passed.
  is_valid: bool
  # Result of the blind solvability call; None if the call failed unrecoverably.
  solvability: bool | None
  # Result of the answer-aware quality call; None if the call failed unrecoverably.
  quality: QualityResult | None
  # Non-empty when a call failed unrecoverably (parse errors after retries,
  # network error, etc.). The pipeline continues; this surfaces the failure.
  error: str


def validate_clue(
  clue_text: str,
  answer: str,
  difficulty: Difficulty,
  solvability_client: ChatClient,
  quality_client: ChatClient,
  max_answer_rank: int = DEFAULT_MAX_ANSWER_RANK,
) -> ValidationResult:
  """Run both validation calls and return a combined result.

  Both calls must pass for the overall verdict to pass. A recoverable failure
  in either call (e.g. parse errors exhausting retries) records an error and
  returns is_valid=False without raising.
  """
  # TODO: call validate_solvability; catch errors, record in error field
  # TODO: call validate_quality; catch errors, record in error field
  # TODO: return ValidationResult(
  #   is_valid=solvability.is_solvable and quality.is_acceptable,
  #   solvability=solvability, quality=quality, error=error)
  raise NotImplementedError
