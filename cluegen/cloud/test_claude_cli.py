# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Tests for the `claude -p` command line and response envelope parsing."""

import json
from pathlib import Path

import pytest

from cluegen.cloud.claude_cli import (
  CallUsage,
  MalformedEnvelope,
  build_cli_command,
  describe_usage,
  parse_response_envelope,
)

# --- build_cli_command ---


def test_cli_command_includes_prompt_lean_flags() -> None:
  command = build_cli_command('claude', model=None, system_prompt_file=None)

  assert command[:2] == ['claude', '-p']
  assert command[command.index('--output-format') + 1] == 'json'
  assert '--disable-slash-commands' in command
  # "*" removes all tool definitions from the prompt (~16K tokens).
  assert command[command.index('--disallowedTools') + 1] == '*'
  assert '--model' not in command
  assert '--system-prompt-file' not in command


def test_cli_command_passes_model_and_system_prompt_file() -> None:
  command = build_cli_command(
    'claude',
    model='claude-fable-5',
    system_prompt_file=Path('/project/CLUE_SPEC.md'),
  )

  assert command[command.index('--model') + 1] == 'claude-fable-5'
  assert (
    command[command.index('--system-prompt-file') + 1]
    == '/project/CLUE_SPEC.md'
  )


def _make_envelope(**overrides: object) -> str:
  """A well-formed CLI result envelope, serialized as the CLI prints it."""
  envelope: dict[str, object] = {
    'type': 'result',
    'subtype': 'success',
    'is_error': False,
    'result': '{"word": "SOUTHWARD"}',
    'session_id': 'session-under-test',
    'total_cost_usd': 0.42,
    'usage': {
      'input_tokens': 100,
      'output_tokens': 2000,
      'cache_read_input_tokens': 15000,
      'cache_creation_input_tokens': 3000,
    },
  }
  envelope.update(overrides)
  return json.dumps(envelope)


# --- parse_response_envelope: well-formed envelopes ---


def test_result_text_is_extracted() -> None:
  response = parse_response_envelope(
    _make_envelope(result='line one\nline two')
  )

  assert response.text == 'line one\nline two'


def test_usage_token_counts_are_extracted() -> None:
  response = parse_response_envelope(
    _make_envelope(
      usage={
        'input_tokens': 7,
        'output_tokens': 11,
        'cache_read_input_tokens': 13,
        'cache_creation_input_tokens': 17,
      }
    )
  )

  assert response.usage == CallUsage(
    input_tokens=7,
    output_tokens=11,
    cache_read_input_tokens=13,
    cache_creation_input_tokens=17,
  )


def test_missing_usage_token_fields_default_to_zero() -> None:
  response = parse_response_envelope(_make_envelope(usage={'input_tokens': 7}))

  assert response.usage == CallUsage(
    input_tokens=7,
    output_tokens=0,
    cache_read_input_tokens=0,
    cache_creation_input_tokens=0,
  )


def test_session_id_and_cost_are_extracted() -> None:
  response = parse_response_envelope(
    _make_envelope(session_id='abc-123', total_cost_usd=1.25)
  )

  assert response.session_id == 'abc-123'
  assert response.cost_usd == 1.25


def test_error_flag_is_surfaced() -> None:
  response = parse_response_envelope(_make_envelope(is_error=True))

  assert response.is_error


# --- parse_response_envelope: degraded but usable envelopes ---


def test_envelope_with_only_result_text_parses() -> None:
  response = parse_response_envelope(json.dumps({'result': 'text'}))

  assert response.text == 'text'
  assert response.usage is None
  assert response.session_id is None
  assert response.cost_usd is None
  assert not response.is_error


def test_malformed_usage_value_yields_no_usage() -> None:
  response = parse_response_envelope(_make_envelope(usage='lots'))

  assert response.usage is None


# --- parse_response_envelope: malformed envelopes ---


def test_non_json_output_is_rejected() -> None:
  with pytest.raises(MalformedEnvelope, match='JSON'):
    parse_response_envelope('plain text, not an envelope')


def test_non_object_envelope_is_rejected() -> None:
  with pytest.raises(MalformedEnvelope, match='object'):
    parse_response_envelope(json.dumps(['not', 'an', 'object']))


def test_envelope_without_result_text_is_rejected() -> None:
  with pytest.raises(MalformedEnvelope, match='result'):
    parse_response_envelope(json.dumps({'subtype': 'success'}))


# --- describe_usage ---


def test_usage_line_includes_all_token_counts_and_cost() -> None:
  response = parse_response_envelope(
    _make_envelope(
      usage={
        'input_tokens': 100,
        'output_tokens': 2000,
        'cache_read_input_tokens': 15000,
        'cache_creation_input_tokens': 3000,
      },
      total_cost_usd=0.4567,
    )
  )

  assert describe_usage('generate', response) == (
    '[usage] generate: input=100 output=2000'
    ' cache_read=15000 cache_write=3000 cost=$0.4567'
  )


def test_usage_line_omits_cost_when_unreported() -> None:
  response = parse_response_envelope(
    _make_envelope(
      usage={
        'input_tokens': 1,
        'output_tokens': 2,
        'cache_read_input_tokens': 3,
        'cache_creation_input_tokens': 4,
      },
      total_cost_usd=None,
    )
  )

  assert describe_usage('verify', response) == (
    '[usage] verify: input=1 output=2 cache_read=3 cache_write=4'
  )


def test_usage_line_reports_unavailable_usage() -> None:
  response = parse_response_envelope(json.dumps({'result': 'text'}))

  assert describe_usage('verify', response) == '[usage] verify: unavailable'
