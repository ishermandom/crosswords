# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for the quality call's structural mechanics."""

import json

import pytest

from cluegen.local.prompt import Difficulty
from cluegen.local.quality import (
  QualityParseError,
  QualityResult,
  validate_quality,
)
from cluegen.local.tests.fake_client import FakeChatClient

# Scripted reply for both scratchpad turns; content is irrelevant to all tests.
_SCRATCHPAD = 'Evaluating the clue...'


def _make_reply(
  *,
  has_tense_agreement: bool = True,
  has_wordplay_indicator: bool = True,
  is_abbreviation_signaled: bool = True,
  uses_fill_format: bool = True,
  has_genuine_alternatives: bool = True,
  angle_craft: int = 4,
  misdirection: int = 2,
  elasticity: int = 2,
  reference_accessibility: int = 5,
  surface_coherence: int = 4,
  fairness_of_deception: int = 5,
  cross_check_payoff: int = 3,
) -> str:
  """Scripted JSON reply for a validate_quality call.

  Defaults produce a passing Monday profile: all conventions True, scale
  scores within Monday ranges (misdirection 1-2, elasticity 1-3,
  accessibility 4-5) and above the quality floor (≥ 4) for craft scales.
  The `cross_check_payoff` default of 3 is provisional; update once day-range
  profiles for this scale are finalised.
  """
  return json.dumps(
    {
      'conventions': {
        'has_tense_agreement': has_tense_agreement,
        'has_wordplay_indicator': has_wordplay_indicator,
        'is_abbreviation_signaled': is_abbreviation_signaled,
        'uses_fill_format': uses_fill_format,
        'has_genuine_alternatives': has_genuine_alternatives,
      },
      'scales': {
        'angle_craft': {'score': angle_craft, 'rationale': 'Deliberate angle.'},
        'misdirection': {
          'score': misdirection,
          'rationale': 'Low misdirection.',
        },
        'elasticity': {
          'score': elasticity,
          'rationale': 'Supports reinterpretation.',
        },
        'reference_accessibility': {
          'score': reference_accessibility,
          'rationale': 'Universal reference.',
        },
        'surface_coherence': {
          'score': surface_coherence,
          'rationale': 'Natural phrasing.',
        },
        'fairness_of_deception': {
          'score': fairness_of_deception,
          'rationale': 'Clean resolution.',
        },
        'cross_check_payoff': {
          'score': cross_check_payoff,
          'rationale': 'Moderate ambiguity for crosses.',
        },
      },
    }
  )


def _validate_quality(
  fake: FakeChatClient,
  *,
  clue: str = 'Long journey',
  answer: str = 'TREK',
  difficulty: Difficulty = Difficulty.MON,
) -> QualityResult:
  """Calls validate_quality with defaults for params irrelevant to the test."""
  return validate_quality(clue, answer, difficulty, fake)


# --- Input shape ---


def test_answer_word_present_in_quality_call() -> None:
  with FakeChatClient([_SCRATCHPAD, _SCRATCHPAD, _make_reply()]) as fake:
    _validate_quality(fake, answer='TREK')
  all_message_text = ' '.join(
    str(m['content']) for call in fake.calls for m in call
  )
  assert 'TREK' in all_message_text


def test_difficulty_day_present_in_quality_call() -> None:
  with FakeChatClient([_SCRATCHPAD, _SCRATCHPAD, _make_reply()]) as fake:
    _validate_quality(fake, difficulty=Difficulty.THU)
  all_message_text = ' '.join(
    str(m['content']) for call in fake.calls for m in call
  )
  assert 'Thursday' in all_message_text


def test_conventions_reply_is_in_rubric_call_context() -> None:
  conventions_reply = 'conventions scratchpad output'
  with FakeChatClient([conventions_reply, _SCRATCHPAD, _make_reply()]) as fake:
    _validate_quality(fake)
  rubric_call_text = ' '.join(str(m['content']) for m in fake.calls[1])
  assert conventions_reply in rubric_call_text


def test_rubric_reply_is_in_output_call_context() -> None:
  rubric_reply = 'rubric scratchpad output'
  with FakeChatClient([_SCRATCHPAD, rubric_reply, _make_reply()]) as fake:
    _validate_quality(fake)
  output_call_text = ' '.join(str(m['content']) for m in fake.calls[2])
  assert rubric_reply in output_call_text


# --- Convention compliance ---


def test_quality_fails_when_tense_agreement_is_false() -> None:
  with FakeChatClient(
    [_SCRATCHPAD, _SCRATCHPAD, _make_reply(has_tense_agreement=False)]
  ) as fake:
    result = _validate_quality(fake)
  assert not result.is_acceptable


def test_quality_fails_when_wordplay_indicator_is_false() -> None:
  with FakeChatClient(
    [_SCRATCHPAD, _SCRATCHPAD, _make_reply(has_wordplay_indicator=False)]
  ) as fake:
    result = _validate_quality(fake)
  assert not result.is_acceptable


def test_quality_fails_when_abbreviation_not_signaled() -> None:
  with FakeChatClient(
    [_SCRATCHPAD, _SCRATCHPAD, _make_reply(is_abbreviation_signaled=False)]
  ) as fake:
    result = _validate_quality(fake)
  assert not result.is_acceptable


def test_quality_fails_when_fill_format_is_false() -> None:
  with FakeChatClient(
    [_SCRATCHPAD, _SCRATCHPAD, _make_reply(uses_fill_format=False)]
  ) as fake:
    result = _validate_quality(fake)
  assert not result.is_acceptable


# --- Difficulty calibration ---


def test_quality_passes_when_all_conventions_pass_and_all_scales_in_range() -> (
  None
):
  with FakeChatClient([_SCRATCHPAD, _SCRATCHPAD, _make_reply()]) as fake:
    result = _validate_quality(fake)
  assert result.is_acceptable


def test_quality_fails_when_misdirection_score_out_of_range_for_day() -> None:
  # Monday expects misdirection 1-2; score 4 is too high.
  with FakeChatClient(
    [_SCRATCHPAD, _SCRATCHPAD, _make_reply(misdirection=4)]
  ) as fake:
    result = _validate_quality(fake, difficulty=Difficulty.MON)
  assert not result.is_acceptable


def test_quality_fails_when_elasticity_score_out_of_range_for_day() -> None:
  # Monday expects elasticity 1-3; score 5 is too high.
  with FakeChatClient(
    [_SCRATCHPAD, _SCRATCHPAD, _make_reply(elasticity=5)]
  ) as fake:
    result = _validate_quality(fake, difficulty=Difficulty.MON)
  assert not result.is_acceptable


def test_quality_fails_when_reference_accessibility_score_out_of_range() -> (
  None
):
  # Monday expects reference accessibility 4-5; score 2 is too low.
  with FakeChatClient(
    [_SCRATCHPAD, _SCRATCHPAD, _make_reply(reference_accessibility=2)]
  ) as fake:
    result = _validate_quality(fake, difficulty=Difficulty.MON)
  assert not result.is_acceptable


def test_craft_and_fairness_are_quality_floors_not_day_axes() -> None:
  # Thursday allows high misdirection and low accessibility — all day-axis
  # scales are in range — but a low angle_craft score (2) still fails because
  # craft is a day-agnostic quality floor (minimum 4), not a day range.
  with FakeChatClient(
    [
      _SCRATCHPAD,
      _SCRATCHPAD,
      _make_reply(
        misdirection=5,
        elasticity=5,
        reference_accessibility=3,
        angle_craft=2,
      ),
    ]
  ) as fake:
    result = _validate_quality(fake, difficulty=Difficulty.THU)
  assert not result.is_acceptable


# --- Parse error handling ---


def test_parse_error_on_malformed_json() -> None:
  with (
    FakeChatClient([_SCRATCHPAD, _SCRATCHPAD, 'not valid json']) as fake,
    pytest.raises(QualityParseError),
  ):
    _validate_quality(fake)


def test_parse_error_when_convention_field_is_not_boolean() -> None:
  data = json.loads(_make_reply())
  data['conventions']['has_tense_agreement'] = 'yes'
  with (
    FakeChatClient([_SCRATCHPAD, _SCRATCHPAD, json.dumps(data)]) as fake,
    pytest.raises(QualityParseError, match='has_tense_agreement'),
  ):
    _validate_quality(fake)


def test_parse_error_when_scale_score_is_out_of_range() -> None:
  data = json.loads(_make_reply())
  data['scales']['angle_craft']['score'] = 6
  with (
    FakeChatClient([_SCRATCHPAD, _SCRATCHPAD, json.dumps(data)]) as fake,
    pytest.raises(QualityParseError, match='angle_craft'),
  ):
    _validate_quality(fake)


def test_parse_error_when_scale_score_is_boolean() -> None:
  # bool is a subclass of int; True would pass isinstance(v, int) without an
  # explicit bool check. json.dumps(True) → "true" → json.loads → True (bool).
  data = json.loads(_make_reply())
  data['scales']['misdirection']['score'] = True
  with (
    FakeChatClient([_SCRATCHPAD, _SCRATCHPAD, json.dumps(data)]) as fake,
    pytest.raises(QualityParseError, match='misdirection'),
  ):
    _validate_quality(fake)


def test_parse_error_when_required_field_is_missing() -> None:
  data = json.loads(_make_reply())
  del data['conventions']
  with (
    FakeChatClient([_SCRATCHPAD, _SCRATCHPAD, json.dumps(data)]) as fake,
    pytest.raises(QualityParseError, match='conventions'),
  ):
    _validate_quality(fake)


# --- has_genuine_alternatives convention ---


def test_quality_fails_when_has_genuine_alternatives_is_false() -> None:
  with FakeChatClient(
    [_SCRATCHPAD, _SCRATCHPAD, _make_reply(has_genuine_alternatives=False)]
  ) as fake:
    result = _validate_quality(fake)
  assert not result.is_acceptable


def test_parse_error_when_has_genuine_alternatives_is_not_boolean() -> None:
  data = json.loads(_make_reply())
  data['conventions']['has_genuine_alternatives'] = 'yes'
  with (
    FakeChatClient([_SCRATCHPAD, _SCRATCHPAD, json.dumps(data)]) as fake,
    pytest.raises(QualityParseError, match='has_genuine_alternatives'),
  ):
    _validate_quality(fake)


# --- elasticity (renamed from wordplay_complexity) ---


def test_parse_error_when_old_wordplay_complexity_field_used() -> None:
  # After the rename, the old field name is unknown and should raise a parse
  # error rather than silently succeeding with missing data.
  data = json.loads(_make_reply())
  # Simulate a response using the old field name.
  data['scales']['wordplay_complexity'] = data['scales'].pop('elasticity')
  with (
    FakeChatClient([_SCRATCHPAD, _SCRATCHPAD, json.dumps(data)]) as fake,
    pytest.raises(QualityParseError, match='elasticity'),
  ):
    _validate_quality(fake)


# --- cross_check_payoff scale ---


def test_parse_error_when_cross_check_payoff_is_missing() -> None:
  data = json.loads(_make_reply())
  del data['scales']['cross_check_payoff']
  with (
    FakeChatClient([_SCRATCHPAD, _SCRATCHPAD, json.dumps(data)]) as fake,
    pytest.raises(QualityParseError, match='cross_check_payoff'),
  ):
    _validate_quality(fake)


def test_parse_error_when_cross_check_payoff_score_is_out_of_range() -> None:
  data = json.loads(_make_reply())
  data['scales']['cross_check_payoff']['score'] = 6
  with (
    FakeChatClient([_SCRATCHPAD, _SCRATCHPAD, json.dumps(data)]) as fake,
    pytest.raises(QualityParseError, match='cross_check_payoff'),
  ):
    _validate_quality(fake)
