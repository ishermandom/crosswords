# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Answer-aware quality validation call."""

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass

from clue_gen.client import ChatClient, Message
from clue_gen.parsing import strip_markdown_fences
from clue_gen.prompt import Difficulty

_log = logging.getLogger(__name__)


class QualityParseError(Exception):
  """Raised when the quality reply cannot be parsed as valid JSON."""


@dataclass(frozen=True)
class ConventionResult:
  """Binary pass/fail for each NYT crossword convention."""

  # Clue grammatical form matches the answer (tense, number).
  has_tense_agreement: bool
  # ? suffix present iff the clue uses misdirection or wordplay.
  has_wordplay_indicator: bool
  # Any abbreviation in the answer is explicitly flagged in the clue.
  is_abbreviation_signaled: bool
  # Fill-in-the-blank blanks rendered as ___.
  uses_fill_format: bool

  @property
  def is_compliant(self) -> bool:
    """True only when all conventions are satisfied."""
    return (
      self.has_tense_agreement
      and self.has_wordplay_indicator
      and self.is_abbreviation_signaled
      and self.uses_fill_format
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


# --- Prompt construction ---


# Per-day editor persona descriptions for the quality system prompt.
_DAY_DESCRIPTIONS: dict[Difficulty, str] = {
  Difficulty.MON: (
    'Monday — the most accessible day. Clues are direct and unambiguous, '
    'with little or no misdirection and common vocabulary. Wordplay is '
    'acceptable when the mechanism is obvious.'
  ),
  Difficulty.TUE: (
    'Tuesday — one step up from Monday. Mild misdirection or wordplay is '
    'acceptable, but clues should resolve easily for a practiced solver. '
    'Vocabulary and references remain broadly accessible.'
  ),
  Difficulty.WED: (
    'Wednesday — mid-week difficulty. Deliberate misdirection or wordplay is '
    'expected. References may be moderately niche. A practiced solver should '
    'need to consider multiple interpretations before the answer clicks.'
  ),
  Difficulty.THU: (
    'Thursday — one of the hardest days. Strong misdirection and multi-layer '
    'wordplay are expected. References may be moderately specialized. Novice '
    'solvers should struggle; experienced solvers should enjoy the aha moment.'
  ),
  Difficulty.FRI: (
    'Friday — among the hardest. Strong misdirection, complex wordplay, and '
    'mid-range reference knowledge. Clues reward lateral thinking and '
    'persistence.'
  ),
  Difficulty.SAT: (
    'Saturday — the hardest themeless day. Strong misdirection, complex '
    'wordplay, and references that may be niche or specialist. Solvers expect '
    'to be genuinely challenged.'
  ),
}

_SYSTEM_PROMPT_TEMPLATE = """\
You are an experienced NYT crossword editor evaluating a submitted clue.

Target day: {day_description}

Evaluate whether this clue meets these criteria. Do not express a preference
for a particular verdict.

Conventions (binary pass/fail):
- Tense and number agreement: the clue's grammatical form must agree with the
  answer (plural answer → plural clue surface; verb answer → matching tense)
- Wordplay indicator: a ? suffix is required when the clue uses misdirection
  or wordplay; it must not appear on a straight definition clue
- Abbreviation signaling: any abbreviation in the answer must be signaled in
  the clue (e.g. "Abbr.", "briefly", or an abbreviated word in the clue)
- Fill-in-the-blank format: blanks must be rendered as ___

Rubric scales (score each 1–5 with a brief rationale):
- angle_craft: deliberateness of the chosen angle (1 = obvious default/trivial
  antonym, 5 = unexpected and considered)
- misdirection: strength of surface misdirection (1 = points directly at the
  answer, 5 = strong deliberate feint)
- wordplay_complexity: linguistic mechanism complexity (1 = none, 5 = multi-
  layer wordplay)
- reference_accessibility: breadth of required knowledge (1 = niche/specialist,
  5 = universal)
- surface_coherence: polish of the surface reading (1 = tortured syntax,
  5 = natural, idiomatic phrase)
- fairness_of_deception: cleanliness of the connection once seen (1 = ambiguity
  that doesn't resolve, 5 = elegant and unambiguous). Score 5 by default for
  clues with no misdirection.\
"""

_SCRATCHPAD_PROMPT = (
  'Reason through your evaluation: assess each convention and work through '
  'each rubric dimension with evidence from the clue text.'
)

_STRUCTURED_OUTPUT_PROMPT = (
  'Based on your reasoning above, provide your final evaluation. '
  'Respond with JSON only, no explanation:\n'
  '{"conventions": {...}, "scales": {...}}'
)

# JSON schema for structured quality output.
_QUALITY_FORMAT: dict[str, object] = {
  'type': 'object',
  'properties': {
    'conventions': {
      'type': 'object',
      'properties': {
        'has_tense_agreement': {'type': 'boolean'},
        'has_wordplay_indicator': {'type': 'boolean'},
        'is_abbreviation_signaled': {'type': 'boolean'},
        'uses_fill_format': {'type': 'boolean'},
      },
      'required': [
        'has_tense_agreement',
        'has_wordplay_indicator',
        'is_abbreviation_signaled',
        'uses_fill_format',
      ],
    },
    'scales': {
      'type': 'object',
      'properties': {
        'angle_craft': {'$ref': '#/$defs/scale'},
        'misdirection': {'$ref': '#/$defs/scale'},
        'wordplay_complexity': {'$ref': '#/$defs/scale'},
        'reference_accessibility': {'$ref': '#/$defs/scale'},
        'surface_coherence': {'$ref': '#/$defs/scale'},
        'fairness_of_deception': {'$ref': '#/$defs/scale'},
      },
      'required': [
        'angle_craft',
        'misdirection',
        'wordplay_complexity',
        'reference_accessibility',
        'surface_coherence',
        'fairness_of_deception',
      ],
    },
  },
  'required': ['conventions', 'scales'],
  '$defs': {
    'scale': {
      'type': 'object',
      'properties': {
        'score': {'type': 'integer', 'minimum': 1, 'maximum': 5},
        'rationale': {'type': 'string'},
      },
      'required': ['score', 'rationale'],
    },
  },
}


# --- Parsing ---


def _require_mapping(mapping: dict[str, object], key: str) -> dict[str, object]:
  """Extract mapping[key] and assert it is a JSON object."""
  if key not in mapping:
    raise QualityParseError(f'missing required field {key!r}')
  value = mapping[key]
  if not isinstance(value, dict):
    raise QualityParseError(
      f'{key!r}: expected object, got {type(value).__name__!r}'
    )
  return value


def _require_bool(mapping: dict[str, object], key: str) -> bool:
  """Extract mapping[key] and assert it is a boolean."""
  if key not in mapping:
    raise QualityParseError(f'missing required field {key!r}')
  value = mapping[key]
  if not isinstance(value, bool):
    raise QualityParseError(
      f'{key!r}: expected boolean, got {type(value).__name__!r}'
    )
  return value


def _require_str(mapping: dict[str, object], key: str) -> str:
  """Extract mapping[key] and assert it is a string."""
  if key not in mapping:
    raise QualityParseError(f'missing required field {key!r}')
  value = mapping[key]
  if not isinstance(value, str):
    raise QualityParseError(
      f'{key!r}: expected string, got {type(value).__name__!r}'
    )
  return value


def _require_score(mapping: dict[str, object], key: str) -> int:
  """Extract mapping[key] and assert it is an integer score in 1–5."""
  if key not in mapping:
    raise QualityParseError(f'missing required field {key!r}')
  value = mapping[key]
  # bool is a subclass of int in Python; reject it explicitly.
  if isinstance(value, bool) or not isinstance(value, int):
    raise QualityParseError(
      f'{key!r}: expected integer score, got {type(value).__name__!r}'
    )
  if not 1 <= value <= 5:
    raise QualityParseError(f'{key!r}: score {value} out of range 1–5')
  return value


def _parse_conventions(data: dict[str, object]) -> ConventionResult:
  """Parse and validate the conventions block from the quality JSON."""
  conv = _require_mapping(data, 'conventions')
  return ConventionResult(
    has_tense_agreement=_require_bool(conv, 'has_tense_agreement'),
    has_wordplay_indicator=_require_bool(conv, 'has_wordplay_indicator'),
    is_abbreviation_signaled=_require_bool(conv, 'is_abbreviation_signaled'),
    uses_fill_format=_require_bool(conv, 'uses_fill_format'),
  )


def _parse_scale(scales: dict[str, object], key: str) -> ScoreWithRationale:
  """Parse and validate one named rubric scale entry."""
  scale = _require_mapping(scales, key)
  try:
    return ScoreWithRationale(
      score=_require_score(scale, 'score'),
      rationale=_require_str(scale, 'rationale'),
    )
  except QualityParseError as error:
    raise QualityParseError(f'{key}: {error}') from error


def _parse_rubric(data: dict[str, object]) -> RubricScores:
  """Parse and validate the scales block from the quality JSON."""
  scales = _require_mapping(data, 'scales')
  return RubricScores(
    angle_craft=_parse_scale(scales, 'angle_craft'),
    misdirection=_parse_scale(scales, 'misdirection'),
    wordplay_complexity=_parse_scale(scales, 'wordplay_complexity'),
    reference_accessibility=_parse_scale(scales, 'reference_accessibility'),
    surface_coherence=_parse_scale(scales, 'surface_coherence'),
    fairness_of_deception=_parse_scale(scales, 'fairness_of_deception'),
  )


def _parse_reply(reply: str) -> dict[str, object]:
  """Strip fences, parse JSON, and assert the top level is a JSON object.

  Raises QualityParseError on malformed JSON or a non-object top-level value.
  """
  text = strip_markdown_fences(reply)
  try:
    data = json.loads(text)
  except json.JSONDecodeError as error:
    _log.error('failed to parse quality reply: %s\nRaw reply: %s', error, reply)
    raise QualityParseError(
      f'failed to parse quality reply: {error}'
    ) from error
  if not isinstance(data, dict):
    raise QualityParseError(
      f'expected JSON object, got {type(data).__name__!r}'
    )
  return data


def _in_range(score: int, score_range: ScoreRange) -> bool:
  """True if score falls within score_range's inclusive bounds."""
  return score_range.min <= score <= score_range.max


def _scores_match_day(rubric: RubricScores, difficulty: Difficulty) -> bool:
  """True if all rubric scores satisfy the day profile and quality floors."""
  profile = DAY_PROFILES[difficulty]
  return (
    _in_range(rubric.misdirection.score, profile.misdirection)
    and _in_range(rubric.wordplay_complexity.score, profile.wordplay_complexity)
    and _in_range(
      rubric.reference_accessibility.score, profile.reference_accessibility
    )
    and rubric.angle_craft.score >= QUALITY_FLOOR
    and rubric.surface_coherence.score >= QUALITY_FLOOR
    and rubric.fairness_of_deception.score >= QUALITY_FLOOR
  )


def validate_quality(
  clue_text: str,
  answer: str,
  difficulty: Difficulty,
  client: ChatClient,
) -> QualityResult:
  """Run the answer-aware quality call and return a structured result.

  Uses a two-turn structure: a free-form scratchpad turn for reasoning, then a
  constrained structured-output turn. Evaluates convention compliance first; a
  convention failure returns immediately with rubric=None. If conventions pass,
  scores the clue on six rubric scales and checks them against the expected day
  profile.
  """
  system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
    day_description=_DAY_DESCRIPTIONS[difficulty]
  )
  scratchpad_messages: Sequence[Message] = [
    {'role': 'system', 'content': system_prompt},
    {
      'role': 'user',
      'content': f'Clue: {clue_text}\nAnswer: {answer}\n\n{_SCRATCHPAD_PROMPT}',
    },
  ]
  scratchpad_result = client.chat(scratchpad_messages)
  _log.debug('Scratchpad:\n%s', scratchpad_result.reply)

  output_messages: Sequence[Message] = [
    *scratchpad_result.messages,
    {'role': 'user', 'content': _STRUCTURED_OUTPUT_PROMPT},
  ]
  # TODO: retry loop on JSON parse failure; see validation.md — "Error
  #   handling and logging".
  output_result = client.chat(output_messages, format=_QUALITY_FORMAT)

  data = _parse_reply(output_result.reply)
  conventions = _parse_conventions(data)
  if not conventions.is_compliant:
    return QualityResult(
      is_acceptable=False, conventions=conventions, rubric=None
    )

  rubric = _parse_rubric(data)
  return QualityResult(
    is_acceptable=_scores_match_day(rubric, difficulty),
    conventions=conventions,
    rubric=rubric,
  )
