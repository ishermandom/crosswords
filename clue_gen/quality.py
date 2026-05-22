# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Answer-aware quality validation call."""

from dataclasses import dataclass

from clue_gen.client import ChatClient
from clue_gen.prompt import Difficulty


@dataclass(frozen=True)
class ConventionResult:
  """Binary pass/fail for each NYT crossword convention."""

  # Clue grammatical form matches the answer (tense, number).
  tense_agreement: bool
  # ? suffix present iff the clue uses misdirection or wordplay.
  wordplay_indicator: bool
  # Any abbreviation in the answer is explicitly flagged in the clue.
  abbreviation_signaled: bool
  # Fill-in-the-blank blanks rendered as ___.
  fill_format: bool

  @property
  def is_compliant(self) -> bool:
    """True only when all conventions are satisfied."""
    return (
      self.tense_agreement
      and self.wordplay_indicator
      and self.abbreviation_signaled
      and self.fill_format
    )


@dataclass(frozen=True)
class ScoreWithRationale:
  """A 1–5 rubric score with the model's stated reasoning."""

  # Scale score from 1 (low) to 5 (high).
  score: int
  # Model's stated reasoning for the score.
  rationale: str


@dataclass(frozen=True)
class RubricScores:
  """Six rubric scale scores from the quality call."""

  # Deliberateness of the angle chosen; 1 = obvious default, 5 = considered.
  angle_craft: ScoreWithRationale
  # Strength of misdirection; 1 = points directly at answer, 5 = strong feint.
  misdirection: ScoreWithRationale
  # Linguistic mechanism complexity; 1 = none, 5 = multi-layer wordplay.
  wordplay_complexity: ScoreWithRationale
  # Breadth of knowledge required; 1 = niche/specialist, 5 = universal.
  reference_accessibility: ScoreWithRationale
  # Polish of the surface reading; 1 = tortured syntax, 5 = natural phrase.
  surface_coherence: ScoreWithRationale
  # Cleanliness of the connection once seen; 1 = ambiguous trick, 5 = elegant.
  # Defaults to 5 for clues with no misdirection.
  fairness_of_deception: ScoreWithRationale


@dataclass(frozen=True)
class QualityResult:
  """Outcome of the answer-aware quality call for one clue."""

  # True if all conventions passed and all scale scores are in range for the day.
  is_acceptable: bool
  # Convention compliance results; always populated.
  conventions: ConventionResult
  # None when the clue failed convention compliance (scales are skipped).
  rubric: RubricScores | None


# --- Day profiles ---


@dataclass(frozen=True)
class ScoreRange:
  """Inclusive min–max range for a single rubric scale."""

  # Minimum acceptable score (inclusive).
  min: int
  # Maximum acceptable score (inclusive).
  max: int


@dataclass(frozen=True)
class DayProfile:
  """Expected score ranges for the three difficulty axes of a given NYT day.

  Craft and fairness are quality floors (see QUALITY_FLOOR), not day-specific
  ranges, so they are not included here.
  """

  misdirection: ScoreRange
  wordplay_complexity: ScoreRange
  reference_accessibility: ScoreRange


# Minimum score for day-agnostic quality floors: angle_craft, surface_coherence,
# fairness_of_deception. High scores are expected regardless of difficulty.
# TODO: validate against a golden set; see validation.md — "Open questions".
QUALITY_FLOOR: int = 4

# Expected rubric score ranges per difficulty day.
# TODO: validate and tighten against a golden set; see validation.md — "Open
#   questions".
DAY_PROFILES: dict[Difficulty, DayProfile] = {
  Difficulty.MON: DayProfile(
    misdirection=ScoreRange(1, 2),
    wordplay_complexity=ScoreRange(1, 3),
    reference_accessibility=ScoreRange(4, 5),
  ),
  Difficulty.TUE: DayProfile(
    misdirection=ScoreRange(1, 3),
    wordplay_complexity=ScoreRange(1, 3),
    reference_accessibility=ScoreRange(4, 5),
  ),
  Difficulty.WED: DayProfile(
    misdirection=ScoreRange(3, 3),
    wordplay_complexity=ScoreRange(3, 3),
    reference_accessibility=ScoreRange(3, 5),
  ),
  Difficulty.THU: DayProfile(
    misdirection=ScoreRange(4, 5),
    wordplay_complexity=ScoreRange(4, 5),
    reference_accessibility=ScoreRange(3, 3),
  ),
  Difficulty.FRI: DayProfile(
    misdirection=ScoreRange(4, 5),
    wordplay_complexity=ScoreRange(4, 5),
    reference_accessibility=ScoreRange(3, 3),
  ),
  Difficulty.SAT: DayProfile(
    misdirection=ScoreRange(4, 5),
    wordplay_complexity=ScoreRange(4, 5),
    reference_accessibility=ScoreRange(1, 3),
  ),
}


def validate_quality(
  clue_text: str,
  answer: str,
  difficulty: Difficulty,
  client: ChatClient,
) -> QualityResult:
  """Run the answer-aware quality call and return a structured result.

  Evaluates convention compliance first; a convention failure returns
  immediately with rubric=None. If conventions pass, scores the clue on six
  rubric scales and checks them against the expected day profile.
  """
  # TODO: build quality prompt (editor persona, day description, conventions,
  #   neutral framing sycophancy guard); see validation.md — "Quality call"
  # TODO: call client.chat(); strip fences; parse JSON with retry loop
  # TODO: parse ConventionResult; if not conventions.is_compliant, return early
  #   with is_acceptable=False, rubric=None
  # TODO: parse RubricScores (six ScoreWithRationale entries)
  # TODO: check rubric scores against DAY_PROFILES range for difficulty;
  #   check angle_craft and fairness_of_deception against quality floor
  # TODO: return QualityResult(is_acceptable=..., conventions=..., rubric=...)
  raise NotImplementedError
