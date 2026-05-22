# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for clue_gen.cli pipeline helpers."""

import io
import json
from collections.abc import Sequence
from unittest.mock import MagicMock

import openai
import pytest

from clue_gen.cli import _run_pipeline, main
from clue_gen.client import ChatResult, Message
from clue_gen.prompt import Difficulty
from clue_gen.tests.fake_client import FakeChatClient


class _ConnectionErrorClient:
  """Stub ChatClient that always raises APIConnectionError on chat()."""

  def chat(self, messages: Sequence[Message]) -> ChatResult:
    raise openai.APIConnectionError(
      message='connection refused', request=MagicMock()
    )


def _make_words_input(words: Sequence[str]) -> io.StringIO:
  """Build an in-memory word list file from a Python list."""
  return io.StringIO('\n'.join(words) + '\n')


def test_connection_error_skips_word_and_continues() -> None:
  output = io.StringIO()
  _run_pipeline(
    _make_words_input(['ALPHA']),
    Difficulty.MON,
    _ConnectionErrorClient(),
    output,
  )
  assert json.loads(output.getvalue()) == []


# --- Individual-stage subcommands ---

# TODO: test_generate_subcommand_runs_only_brainstorm_and_extract
#   Invoke the `generate` subcommand with a single word. Assert that only the
#   brainstorm and extract client calls are made — no solvability or quality
#   calls — and that the resulting clue is printed to stdout.

# --- Solvability subcommand ---


def _make_solvability_replies(
  guesses: Sequence[str] = ('MATCH', 'LIGHT', 'FLAME', 'SWORD', 'TORCH'),
) -> list[str]:
  """Scripted replies for a solvability call; scratchpad reply is irrelevant."""
  return ['scratchpad', json.dumps({'guesses': list(guesses)})]


def _make_solvability_argv(
  clue: str = 'Starts a fire?',
  answer: str = 'MATCH',
  difficulty: str = 'Wed',
  max_answer_rank: int = 5,
) -> list[str]:
  """Build a `solvability` subcommand argv; defaults are valid but irrelevant."""
  return [
    'solvability',
    '--clue',
    clue,
    '--answer',
    answer,
    '--difficulty',
    difficulty,
    '--max-answer-rank',
    str(max_answer_rank),
  ]


@pytest.mark.xfail(
  strict=True, reason='validate_solvability not yet implemented'
)
def test_solvability_subcommand_makes_two_client_calls() -> None:
  # validate_solvability is two turns: Turn 1 scratchpad, Turn 2 guess list.
  with FakeChatClient(_make_solvability_replies()) as fake:
    main(_make_solvability_argv(), client=fake, output=io.StringIO())
  assert len(fake.calls) == 2


@pytest.mark.xfail(
  strict=True, reason='validate_solvability not yet implemented'
)
def test_solvability_subcommand_prints_result_as_json() -> None:
  output = io.StringIO()
  with FakeChatClient(_make_solvability_replies()) as fake:
    main(_make_solvability_argv(), client=fake, output=output)
  result = json.loads(output.getvalue())
  assert 'is_solvable' in result
  assert 'answer_rank' in result


@pytest.mark.xfail(
  strict=True, reason='validate_solvability not yet implemented'
)
def test_solvability_subcommand_prints_error_json_on_connection_error() -> None:
  output = io.StringIO()
  main(_make_solvability_argv(), client=_ConnectionErrorClient(), output=output)
  result = json.loads(output.getvalue())
  assert 'error' in result


@pytest.mark.xfail(
  strict=True, reason='validate_solvability not yet implemented'
)
def test_solvability_subcommand_prints_error_json_on_generation_error() -> None:
  output = io.StringIO()
  with FakeChatClient(['scratchpad', 'not valid json']) as fake:
    main(_make_solvability_argv(), client=fake, output=output)
  result = json.loads(output.getvalue())
  assert 'error' in result


# TODO: test_quality_subcommand_accepts_clue_answer_and_day
#   Invoke the `quality` subcommand with a clue string, answer word, and
#   difficulty day. Assert that a quality call is made (and only that call),
#   and that convention results and scale scores are printed to stdout.

# TODO: test_quality_subcommand_exits_on_parse_failure_after_retries
#   Same pattern as test_solvability_subcommand_exits_on_generation_error.


def test_generation_error_skips_word_and_continues() -> None:
  # ALPHA: empty extract triggers GenerationError — should be skipped.
  # BETA: valid replies — should appear in results despite ALPHA's failure.
  output = io.StringIO()
  with FakeChatClient(
    [
      'brainstorm',
      '[]',
      'brainstorm',
      '["A clue for beta"]',
      '{"valid": true}',
    ]
  ) as fake:
    _run_pipeline(
      _make_words_input(['ALPHA', 'BETA']), Difficulty.MON, fake, output
    )
  results = json.loads(output.getvalue())
  assert len(results) == 1
  assert results[0]['word'] == 'BETA'
