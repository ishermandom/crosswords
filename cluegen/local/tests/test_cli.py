# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for cluegen.cli pipeline helpers."""

import io
import json
from collections.abc import Sequence
from unittest.mock import MagicMock

import openai
from cluegen.local.cli import main
from cluegen.local.client import ChatResult, Message
from cluegen.local.input_parsing import ClueEntry
from cluegen.local.tests.fake_client import FakeChatClient


class _ConnectionErrorClient:
  """Stub ChatClient that always raises APIConnectionError on chat()."""

  def chat(
    self,
    messages: Sequence[Message],
    format: object | None = None,
  ) -> ChatResult:
    raise openai.APIConnectionError(
      message='connection refused', request=MagicMock()
    )


def _make_words_stream(words: Sequence[str]) -> io.StringIO:
  """Build an in-memory word-list stream from a Python list."""
  return io.StringIO('\n'.join(words) + '\n')


def _make_clues_stream(entries: Sequence[ClueEntry]) -> io.StringIO:
  """Build an in-memory clue-entry stream from ClueEntry values."""
  return io.StringIO(
    '\n'.join(f'{e.answer} {e.clue_text}' for e in entries) + '\n'
  )


def test_connection_error_prints_error_and_continues() -> None:
  output = io.StringIO()
  main(
    ['run', '--words', '-'],
    client=_ConnectionErrorClient(),
    stdin=_make_words_stream(['ALPHA']),
    output=output,
    logs_dir=None,
  )
  result = json.loads(output.getvalue())
  assert 'error' in result


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


def test_solvability_subcommand_prints_result_as_json() -> None:
  output = io.StringIO()
  with FakeChatClient(_make_solvability_replies()) as fake:
    main(_make_solvability_argv(), client=fake, output=output, logs_dir=None)
  result = json.loads(output.getvalue())
  assert 'is_solvable' in result


def test_solvability_subcommand_prints_error_json_on_connection_error() -> None:
  output = io.StringIO()
  main(
    _make_solvability_argv(),
    client=_ConnectionErrorClient(),
    output=output,
    logs_dir=None,
  )
  result = json.loads(output.getvalue())
  assert 'error' in result


def test_solvability_subcommand_prints_error_json_on_generation_error() -> None:
  output = io.StringIO()
  with FakeChatClient(['scratchpad', 'not valid json']) as fake:
    main(_make_solvability_argv(), client=fake, output=output, logs_dir=None)
  result = json.loads(output.getvalue())
  assert 'error' in result


# --- Quality subcommand ---


def _make_quality_replies() -> list[str]:
  """Scripted replies for a quality call; scratchpad replies are irrelevant."""
  return [
    'scratchpad',
    'scratchpad',
    json.dumps(
      {
        'conventions': {
          'has_tense_agreement': True,
          'has_wordplay_indicator': True,
          'is_abbreviation_signaled': True,
          'uses_fill_format': False,
          'has_genuine_alternatives': True,
        },
        'scales': {
          'angle_craft': {'score': 3, 'rationale': 'ok'},
          'misdirection': {'score': 4, 'rationale': 'ok'},
          'elasticity': {'score': 3, 'rationale': 'ok'},
          'reference_accessibility': {'score': 4, 'rationale': 'ok'},
          'surface_coherence': {'score': 4, 'rationale': 'ok'},
          'fairness_of_deception': {'score': 3, 'rationale': 'ok'},
          'cross_check_payoff': {'score': 3, 'rationale': 'ok'},
        },
      }
    ),
  ]


def _make_quality_argv(
  clue: str = 'Starts a fire?',
  answer: str = 'MATCH',
  difficulty: str = 'Wed',
) -> list[str]:
  """Build a `quality` subcommand argv; defaults are valid but irrelevant."""
  return [
    'quality',
    '--clue',
    clue,
    '--answer',
    answer,
    '--difficulty',
    difficulty,
  ]


def test_quality_subcommand_prints_result_as_json() -> None:
  output = io.StringIO()
  with FakeChatClient(_make_quality_replies()) as fake:
    main(_make_quality_argv(), client=fake, output=output, logs_dir=None)
  result = json.loads(output.getvalue())
  assert 'conventions' in result
  assert 'is_acceptable' in result


def test_quality_subcommand_prints_error_json_on_connection_error() -> None:
  output = io.StringIO()
  main(
    _make_quality_argv(),
    client=_ConnectionErrorClient(),
    output=output,
    logs_dir=None,
  )
  result = json.loads(output.getvalue())
  assert 'error' in result


# --- Batch mode (--clues) ---


def test_solvability_clues_batch_prints_one_result_per_entry() -> None:
  entries = [
    ClueEntry(answer='MATCH', clue_text='Starts a fire?'),
    ClueEntry(answer='LIGHT', clue_text='Turn on?'),
  ]
  output = io.StringIO()
  with FakeChatClient(
    _make_solvability_replies() + _make_solvability_replies()
  ) as fake:
    main(
      ['solvability', '--clues', '-', '--difficulty', 'Wed'],
      client=fake,
      stdin=_make_clues_stream(entries),
      output=output,
      logs_dir=None,
    )
  lines = [line for line in output.getvalue().splitlines() if line.strip()]
  assert len(lines) == 2
  assert all('is_solvable' in json.loads(line) for line in lines)


def test_quality_clues_batch_prints_one_result_per_entry() -> None:
  entries = [
    ClueEntry(answer='MATCH', clue_text='Starts a fire?'),
    ClueEntry(answer='LIGHT', clue_text='Turn on?'),
  ]
  output = io.StringIO()
  with FakeChatClient(
    _make_quality_replies() + _make_quality_replies()
  ) as fake:
    main(
      ['quality', '--clues', '-', '--difficulty', 'Wed'],
      client=fake,
      stdin=_make_clues_stream(entries),
      output=output,
      logs_dir=None,
    )
  lines = [line for line in output.getvalue().splitlines() if line.strip()]
  assert len(lines) == 2
  assert all('is_acceptable' in json.loads(line) for line in lines)


# --- run subcommand ---


def test_generation_error_prints_error_and_continues() -> None:
  # ALPHA: empty extract triggers GenerationError — emits error JSONL.
  # BETA: valid replies — emits result JSONL despite ALPHA's failure.
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
    main(
      ['run', '--words', '-'],
      client=fake,
      stdin=_make_words_stream(['ALPHA', 'BETA']),
      output=output,
      logs_dir=None,
    )
  lines = [line for line in output.getvalue().splitlines() if line.strip()]
  results = [json.loads(line) for line in lines]
  assert len(results) == 2
  assert 'error' in results[0]
  assert results[1]['word'] == 'BETA'
