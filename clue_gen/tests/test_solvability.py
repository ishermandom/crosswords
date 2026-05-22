# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for the solvability call's structural mechanics."""

import json
from collections.abc import Sequence

import pytest

from clue_gen.prompt import Difficulty
from clue_gen.solvability import validate_solvability
from clue_gen.tests.fake_client import FakeChatClient


def _make_replies(
  scratchpad: str = 'Thinking through the clue...',
  guesses: Sequence[str] = ['CRANE'],
) -> list[str]:
  """Scripted replies for a validate_solvability call."""
  return [scratchpad, json.dumps({'guesses': list(guesses)})]


def _validate_solvability(
  fake: FakeChatClient,
  *,
  clue: str = 'Celestial body',
  answer: str = 'CRANE',
  difficulty: Difficulty = Difficulty.MON,
  max_answer_rank: int = 10,
) -> bool:
  """Calls validate_solvability with defaults for params irrelevant to the test."""
  return validate_solvability(clue, answer, difficulty, fake, max_answer_rank)


# --- Input shape ---


@pytest.mark.xfail(strict=True)
def test_answer_word_absent_from_solvability_call() -> None:
  # The solver must be blind — the answer word must not leak into any message.
  with FakeChatClient(_make_replies(guesses=['MOON', 'STAR', 'SUNS'])) as fake:
    _validate_solvability(fake, answer='STAR')
  all_message_text = ' '.join(
    str(m['content']) for call in fake.calls for m in call
  )
  assert 'STAR' not in all_message_text


@pytest.mark.xfail(strict=True)
def test_answer_length_present_in_solvability_call() -> None:
  # The solver needs the letter count to constrain its guesses — without it,
  # length filtering would be the only signal, and wrong-length guesses pollute
  # the raw list. 'STAR' has 4 letters.
  with FakeChatClient(_make_replies()) as fake:
    _validate_solvability(fake, answer='STAR')
  all_message_text = ' '.join(
    str(m['content']) for call in fake.calls for m in call
  )
  assert '4' in all_message_text


# --- Multi-turn structure ---


@pytest.mark.xfail(strict=True)
def test_solvability_makes_two_turns() -> None:
  # One call for the scratchpad turn, one for the guess-list turn.
  with FakeChatClient(_make_replies()) as fake:
    _validate_solvability(fake)
  assert len(fake.calls) == 2


@pytest.mark.xfail(strict=True)
def test_second_turn_appends_to_first_turn_reply() -> None:
  # The model must see its own scratchpad reasoning before committing to guesses.
  scratchpad = 'Thinking through the clue...'
  with FakeChatClient(_make_replies(scratchpad=scratchpad)) as fake:
    _validate_solvability(fake)
  second_call_text = ' '.join(str(m['content']) for m in fake.calls[1])
  assert scratchpad in second_call_text


# --- Length filtering ---


@pytest.mark.xfail(strict=True)
def test_guesses_shorter_than_answer_length_excluded_before_rank_check() -> (
  None
):
  # SUN, ORB, RAY are shorter than STAR (4 letters) and rank above it in the
  # raw list. After filtering to 4-letter words, STAR rises into the top N.
  guesses = ['SUN', 'ORB', 'RAY', 'STAR']
  with FakeChatClient(_make_replies(guesses=guesses)) as fake:
    result = _validate_solvability(fake, answer='STAR')
  assert result is True


@pytest.mark.xfail(strict=True)
def test_guesses_longer_than_answer_length_excluded_before_rank_check() -> None:
  # PLANET, COMET are longer than STAR (4 letters) and rank above it in the
  # raw list. After filtering to 4-letter words, STAR rises into the top N.
  guesses = ['PLANET', 'COMET', 'STAR']
  with FakeChatClient(_make_replies(guesses=guesses)) as fake:
    result = _validate_solvability(fake, answer='STAR')
  assert result is True


# --- Pass / fail criterion ---


@pytest.mark.xfail(strict=True)
def test_pass_when_answer_is_within_top_n_filtered_guesses() -> None:
  guesses = ['MOON', 'GLOW', 'STAR']
  with FakeChatClient(_make_replies(guesses=guesses)) as fake:
    result = _validate_solvability(fake, answer='STAR')
  assert result is True


@pytest.mark.xfail(strict=True)
def test_fail_when_answer_is_beyond_top_n_filtered_guesses() -> None:
  # STAR is at position 3 in a max_answer_rank=2 window — one past the cutoff.
  guesses = ['MOON', 'GLOW', 'STAR']
  with FakeChatClient(_make_replies(guesses=guesses)) as fake:
    result = _validate_solvability(fake, answer='STAR', max_answer_rank=2)
  assert result is False


@pytest.mark.xfail(strict=True)
def test_fail_when_answer_absent_from_guesses_entirely() -> None:
  with FakeChatClient(_make_replies(guesses=['MOON', 'GLOW'])) as fake:
    result = _validate_solvability(fake, answer='STAR')
  assert result is False
