# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for the solvability call's structural mechanics."""

import json
from collections.abc import Sequence

from cluegen.local.prompt import Difficulty
from cluegen.local.solvability import validate_solvability
from cluegen.local.tests.fake_client import FakeChatClient


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


def test_answer_word_absent_from_solvability_call() -> None:
  # The solver must be blind — the answer word must not leak into any message.
  with FakeChatClient(_make_replies(guesses=['MOON', 'STAR', 'SUNS'])) as fake:
    _validate_solvability(fake, answer='STAR')
  all_message_text = ' '.join(
    str(m['content']) for call in fake.calls for m in call
  )
  assert 'STAR' not in all_message_text


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


# --- Call structure ---


def test_solvability_makes_scratchpad_and_guesses_calls() -> None:
  # One call for scratchpad reasoning, one for the committed guess list.
  with FakeChatClient(_make_replies()) as fake:
    _validate_solvability(fake)
  assert len(fake.calls) == 2


def test_guesses_call_includes_scratchpad_reply() -> None:
  # The model must see its own scratchpad reasoning before committing to guesses.
  scratchpad = 'Thinking through the clue...'
  with FakeChatClient(_make_replies(scratchpad=scratchpad)) as fake:
    _validate_solvability(fake)
  guesses_call_text = ' '.join(str(m['content']) for m in fake.calls[1])
  assert scratchpad in guesses_call_text


# --- Length filtering ---


def test_guesses_shorter_than_answer_length_excluded_before_rank_check() -> (
  None
):
  # SUN, ORB, RAY are shorter than STAR (4 letters) and rank above it in the
  # raw list. After filtering to 4-letter words, STAR rises into the top N.
  guesses = ['SUN', 'ORB', 'RAY', 'STAR']
  with FakeChatClient(_make_replies(guesses=guesses)) as fake:
    result = _validate_solvability(fake, answer='STAR')
  assert result is True


def test_guesses_longer_than_answer_length_excluded_before_rank_check() -> None:
  # PLANET, COMET are longer than STAR (4 letters) and rank above it in the
  # raw list. After filtering to 4-letter words, STAR rises into the top N.
  guesses = ['PLANET', 'COMET', 'STAR']
  with FakeChatClient(_make_replies(guesses=guesses)) as fake:
    result = _validate_solvability(fake, answer='STAR')
  assert result is True


def test_whitespace_stripped_from_guesses_before_length_filter() -> None:
  # 'ORB ' is 3 letters + a trailing space: without stripping, len('ORB ') == 4
  # passes the filter and pushes STAR to rank 2, failing a max_answer_rank=1
  # check. With stripping, ORB is excluded and STAR is rank 1.
  guesses = ['ORB ', 'STAR']
  with FakeChatClient(_make_replies(guesses=guesses)) as fake:
    result = _validate_solvability(fake, answer='STAR', max_answer_rank=1)
  assert result is True


# --- Pass / fail criterion ---


def test_pass_when_answer_is_within_top_n_filtered_guesses() -> None:
  guesses = ['MOON', 'GLOW', 'STAR']
  with FakeChatClient(_make_replies(guesses=guesses)) as fake:
    result = _validate_solvability(fake, answer='STAR')
  assert result is True


def test_fail_when_answer_is_beyond_top_n_filtered_guesses() -> None:
  # STAR is at position 3 in a max_answer_rank=2 window — one past the cutoff.
  guesses = ['MOON', 'GLOW', 'STAR']
  with FakeChatClient(_make_replies(guesses=guesses)) as fake:
    result = _validate_solvability(fake, answer='STAR', max_answer_rank=2)
  assert result is False


def test_fail_when_answer_absent_from_guesses_entirely() -> None:
  with FakeChatClient(_make_replies(guesses=['MOON', 'GLOW'])) as fake:
    result = _validate_solvability(fake, answer='STAR')
  assert result is False


# --- Parse error handling ---

# TODO: test_parse_error_on_malformed_json
#   Script the guesses reply as invalid JSON. Assert SolvabilityParseError is
#   raised. (Currently covered only at the CLI level in test_cli.py.)

# TODO: test_parse_error_on_missing_guesses_key
#   Script the guesses reply as valid JSON without a 'guesses' key (e.g.
#   '{"words": [...]}'). Assert SolvabilityParseError is raised.

# TODO: test_markdown_fences_stripped_before_parsing
#   Script the guesses reply wrapped in ```json\n...\n``` fences. Assert the
#   answer is found at the expected rank (i.e. parsing did not fail).

# TODO: test_lowercase_guesses_normalized_before_rank_check
#   Script guesses with mixed case (e.g. ['star', 'Star', 'MOON']). Assert
#   'STAR' is found at rank 1 — lowercase entries match the uppercase answer.


# --- Structured output format ---

# TODO: test_guesses_call_passes_structured_output_format
#   Assert that the guesses call passes _GUESSES_FORMAT and the scratchpad call
#   passes format=None. Prerequisite: extend FakeChatClient to record the
#   format argument alongside calls (see TODO in fake_client.py).


# --- Logging ---

# TODO: test_scratchpad_reply_is_logged
#   Use pytest's caplog fixture at DEBUG level. Assert the scratchpad reply text
#   appears in a debug log message after the call.

# TODO: test_raw_guesses_logged_with_count_and_values
#   Use caplog. Assert a debug message records both the total count and the
#   uppercased guess words.

# TODO: test_filtered_guesses_logged_with_count_and_values
#   Use caplog. Assert a debug message records the length-filtered count and
#   the matching words. Include a case where no guesses match the length (logged
#   as '(none)').

# TODO: test_answer_rank_logged_on_pass
#   Use caplog. Assert a debug message records the answer word and its 1-indexed
#   rank when the answer is found within the threshold.

# TODO: test_answer_absent_logged_on_fail
#   Use caplog. Assert a debug message notes the answer word is absent when it
#   does not appear in the filtered guesses.

# TODO: test_truncation_warning_logged_when_completion_hits_max_tokens
#   Assert a WARNING is emitted when completion_tokens == max_tokens. This fires
#   in OllamaClient, not FakeChatClient, so the test requires either a custom
#   fake that returns usage metadata or a lightweight integration test against a
#   mocked HTTP layer. Prerequisite: decide the fake strategy.
