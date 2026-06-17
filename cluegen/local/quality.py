# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Answer-aware quality validation call."""

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass

from openai.types.shared_params import ResponseFormatJSONSchema

from cluegen.local.client import ChatClient, Message
from cluegen.local.parsing import strip_markdown_fences
from cluegen.local.prompt import Difficulty

_log = logging.getLogger(__name__)


def _section(label: str) -> str:
  """Format a dashes section header for log output (60 chars total)."""
  return f'\n--- {label} {"-" * max(0, 55 - len(label))}'


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
  # Clue's supposed alternatives are real words/phrases a solver would consider.
  has_genuine_alternatives: bool

  @property
  def is_compliant(self) -> bool:
    """True only when all conventions are satisfied."""
    return (
      self.has_tense_agreement
      and self.has_wordplay_indicator
      and self.is_abbreviation_signaled
      and self.uses_fill_format
      and self.has_genuine_alternatives
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
  # Supports multiple coherent interpretations; 1 = single obvious meaning,
  # 5 = rich reinterpretation space.
  elasticity: ScoreWithRationale
  # Breadth of knowledge required; 1 = niche/specialist, 5 = universal.
  reference_accessibility: ScoreWithRationale
  # Polish of the surface reading; 1 = tortured syntax, 5 = natural phrase.
  surface_coherence: ScoreWithRationale
  # Cleanliness of the connection once seen; 1 = ambiguous trick, 5 = elegant.
  # Defaults to 5 for clues with no misdirection.
  fairness_of_deception: ScoreWithRationale
  # Degree of genuine ambiguity left for crosses to resolve; 1 = clue already
  # determines the answer, 5 = several plausible fills collapse to one.
  cross_check_payoff: ScoreWithRationale


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
  elasticity: ScoreRange
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
    elasticity=ScoreRange(1, 3),
    reference_accessibility=ScoreRange(4, 5),
  ),
  Difficulty.TUE: DayProfile(
    misdirection=ScoreRange(1, 3),
    elasticity=ScoreRange(1, 3),
    reference_accessibility=ScoreRange(4, 5),
  ),
  Difficulty.WED: DayProfile(
    misdirection=ScoreRange(3, 3),
    elasticity=ScoreRange(3, 3),
    reference_accessibility=ScoreRange(3, 5),
  ),
  Difficulty.THU: DayProfile(
    misdirection=ScoreRange(4, 5),
    elasticity=ScoreRange(4, 5),
    reference_accessibility=ScoreRange(3, 3),
  ),
  Difficulty.FRI: DayProfile(
    misdirection=ScoreRange(4, 5),
    elasticity=ScoreRange(4, 5),
    reference_accessibility=ScoreRange(3, 3),
  ),
  Difficulty.SAT: DayProfile(
    misdirection=ScoreRange(4, 5),
    elasticity=ScoreRange(4, 5),
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

Target day: {day_description}\
"""

_CONVENTIONS_SCRATCHPAD_PROMPT = """\
Evaluate each convention below. For each, reason step by step, then state PASS
or FAIL on its own line.

1. Tense and number agreement: the clue's grammatical form must agree with the
   answer (plural answer → plural clue surface; verb answer → matching tense).
2. Wordplay indicator: a ? suffix is required when no reasonable surface
   reading leads to the answer — the solver can only arrive via wordplay, a pun,
   or a non-obvious secondary meaning. It is forbidden when any reasonable
   surface reading already gives the answer, even if extra meanings exist. A ?
   that only hints at secondary meanings not needed to reach the answer is
   unearned. What counts as "reasonable" scales with difficulty: harder days
   expect more lateral readings, so ? appears less often on Friday/Saturday.
3. Abbreviation signaling: any abbreviation in the answer must be signaled in
   the clue (e.g. "Abbr.", "briefly", or an abbreviated word in the clue). If
   the answer is not an abbreviation, this passes automatically.
4. Fill-in-the-blank format: blanks must be rendered as ___. If the clue has
   no fill blank, this passes automatically.
5. Genuine alternatives: the alternative answers a solver would consider must
   be real words or phrases, not invented by the clue.\
"""

_RUBRIC_SCRATCHPAD_PROMPT = """\
Score each rubric dimension below. For each, reason step by step with evidence
from the clue text, then give a score from 1–5.

- angle_craft: deliberateness of the chosen angle (1 = obvious default/trivial
  antonym, 5 = unexpected and considered)
- misdirection: strength of surface misdirection (1 = points directly at the
  answer, 5 = strong deliberate feint)
- elasticity: supports multiple coherent interpretations (1 = single obvious
  meaning, 5 = rich reinterpretation space)
- reference_accessibility: breadth of required knowledge (1 = niche/specialist,
  5 = universal)
- surface_coherence: polish of the surface reading (1 = tortured syntax,
  5 = natural, idiomatic phrase)
- fairness_of_deception: cleanliness of the connection once seen (1 = ambiguity
  that doesn't resolve, 5 = elegant and unambiguous). Score 5 by default for
  clues with no misdirection.
- cross_check_payoff: degree of genuine ambiguity left for crosses to resolve
  (1 = clue already determines the answer, 5 = several plausible fills collapse
  to one)\
"""

_STRUCTURED_OUTPUT_PROMPT = (
  'Based on your reasoning above, provide your final evaluation. '
  'Respond with JSON only, no explanation:\n'
  '{\n'
  '  "conventions": {\n'
  '    "has_tense_agreement": false,\n'
  '    "has_wordplay_indicator": false,\n'
  '    "is_abbreviation_signaled": false,\n'
  '    "uses_fill_format": false,\n'
  '    "has_genuine_alternatives": false\n'
  '  },\n'
  '  "scales": {\n'
  '    "angle_craft": {"score": 3, "rationale": "..."},\n'
  '    "misdirection": {"score": 3, "rationale": "..."},\n'
  '    "elasticity": {"score": 3, "rationale": "..."},\n'
  '    "reference_accessibility": {"score": 3, "rationale": "..."},\n'
  '    "surface_coherence": {"score": 3, "rationale": "..."},\n'
  '    "fairness_of_deception": {"score": 3, "rationale": "..."},\n'
  '    "cross_check_payoff": {"score": 3, "rationale": "..."}\n'
  '  }\n'
  '}'
)

# Ollama's grammar converter does not reliably support $ref/$defs — it can
# silently fall back to unconstrained output. Inline the scale schema instead.
_SCALE_SCHEMA: dict[str, object] = {
  'type': 'object',
  'properties': {
    'score': {'type': 'integer', 'minimum': 1, 'maximum': 5},
    'rationale': {'type': 'string'},
  },
  'required': ['score', 'rationale'],
  'additionalProperties': False,
}

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
        'has_genuine_alternatives': {'type': 'boolean'},
      },
      'required': [
        'has_tense_agreement',
        'has_wordplay_indicator',
        'is_abbreviation_signaled',
        'uses_fill_format',
        'has_genuine_alternatives',
      ],
      'additionalProperties': False,
    },
    'scales': {
      'type': 'object',
      'properties': {
        'angle_craft': _SCALE_SCHEMA,
        'misdirection': _SCALE_SCHEMA,
        'elasticity': _SCALE_SCHEMA,
        'reference_accessibility': _SCALE_SCHEMA,
        'surface_coherence': _SCALE_SCHEMA,
        'fairness_of_deception': _SCALE_SCHEMA,
        'cross_check_payoff': _SCALE_SCHEMA,
      },
      'required': [
        'angle_craft',
        'misdirection',
        'elasticity',
        'reference_accessibility',
        'surface_coherence',
        'fairness_of_deception',
        'cross_check_payoff',
      ],
      'additionalProperties': False,
    },
  },
  'required': ['conventions', 'scales'],
  'additionalProperties': False,
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
    has_genuine_alternatives=_require_bool(conv, 'has_genuine_alternatives'),
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
    elasticity=_parse_scale(scales, 'elasticity'),
    reference_accessibility=_parse_scale(scales, 'reference_accessibility'),
    surface_coherence=_parse_scale(scales, 'surface_coherence'),
    fairness_of_deception=_parse_scale(scales, 'fairness_of_deception'),
    cross_check_payoff=_parse_scale(scales, 'cross_check_payoff'),
  )


def _parse_reply(reply: str) -> dict[str, object]:
  """Strip fences, parse JSON, and assert the top level is a JSON object.

  Raises QualityParseError on malformed JSON or a non-object top-level value.
  """
  text = strip_markdown_fences(reply)
  try:
    data = json.loads(text)
  except json.JSONDecodeError as error:
    _log.error(f'failed to parse quality reply: {error}\nRaw reply: {reply}')
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
    and _in_range(rubric.elasticity.score, profile.elasticity)
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

  Uses a three-turn structure: a focused conventions scratchpad, a rubric
  scratchpad, then a constrained structured-output turn. Convention definitions
  are carried in the conventions turn and rubric definitions in the rubric turn,
  keeping each turn self-contained. A convention failure returns immediately
  with rubric=None; if conventions pass, scores the clue on rubric scales and
  checks them against the expected day profile.
  """
  system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
    day_description=_DAY_DESCRIPTIONS[difficulty]
  )
  conventions_messages: Sequence[Message] = [
    {'role': 'system', 'content': system_prompt},
    {
      'role': 'user',
      'content': (
        f'Clue: {clue_text}\nAnswer: {answer}\n\n'
        + _CONVENTIONS_SCRATCHPAD_PROMPT
      ),
    },
  ]
  conventions_result = client.chat(conventions_messages)
  _log.debug(
    f'{_section("conventions scratchpad")}\n\n{conventions_result.reply}\n'
  )

  rubric_messages: Sequence[Message] = [
    *conventions_result.messages,
    {'role': 'user', 'content': _RUBRIC_SCRATCHPAD_PROMPT},
  ]
  rubric_result = client.chat(rubric_messages)
  _log.debug(f'{_section("rubric scratchpad")}\n\n{rubric_result.reply}\n')

  output_messages: Sequence[Message] = [
    *rubric_result.messages,
    {'role': 'user', 'content': _STRUCTURED_OUTPUT_PROMPT},
  ]
  # TODO: retry loop on JSON parse failure; see validation.md — "Error
  #   handling and logging".
  output_result = client.chat(
    output_messages,
    response_format=ResponseFormatJSONSchema(
      type='json_schema',
      json_schema={
        'name': 'quality',
        'strict': True,
        'schema': _QUALITY_FORMAT,
      },
    ),
  )

  data = _parse_reply(output_result.reply)
  _log.debug(
    f'{_section("structured output")}\n\n{json.dumps(data, indent=2)}\n'
  )
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
