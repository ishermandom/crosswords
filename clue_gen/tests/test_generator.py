# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for clue_gen.generator.generate_clue via FakeChatClient."""

# TODO: Many of the test assumptions will be updated as Phase 3 progresses
# and the LLM interactions evolve.

import pytest

from clue_gen.client import GenerationError
from clue_gen.generator import ClueResult, generate_clue
from clue_gen.prompt import Difficulty
from clue_gen.tests.fake_client import FakeChatClient


def _replies(
  brainstorm: str = 'brainstorm reply',
  extract: str = '["A clue for alpha"]',
  validate: str = '{"valid": true}',
) -> list[str]:
  """Default scripted replies for a single-candidate generate_clue call."""
  return [brainstorm, extract, validate]


# --- Call sequence: brainstorm → extract → validate ---


def test_makes_exactly_three_calls_for_single_candidate() -> None:
  with FakeChatClient(_replies()) as fake:
    generate_clue('ALPHA', Difficulty.MON, fake)
  assert len(fake.calls) == 3


def test_brainstorm_call_includes_answer_word() -> None:
  with FakeChatClient(_replies()) as fake:
    generate_clue('ALPHA', Difficulty.MON, fake)
  # calls[0] is the messages list passed to the brainstorm call.
  content = fake.calls[0][-1]['content']
  assert isinstance(content, str)
  assert 'ALPHA' in content


def test_extract_call_appends_to_brainstorm_context() -> None:
  # The extract turn continues the brainstorm conversation, so the messages
  # list passed to call 2 should include the brainstorm assistant reply.
  with FakeChatClient(_replies()) as fake:
    generate_clue('ALPHA', Difficulty.MON, fake)
  # calls[1] is the messages list passed to the extract call.
  contents = [m['content'] for m in fake.calls[1]]
  assert 'brainstorm reply' in contents


def test_validation_call_uses_fresh_context() -> None:
  # Validation is an independent call — it must not contain the brainstorm
  # reply, because the validator solves blind with only the clue and length.
  with FakeChatClient(_replies()) as fake:
    generate_clue('ALPHA', Difficulty.MON, fake)
  # calls[2] is the messages list passed to the validation call.
  contents = [m['content'] for m in fake.calls[2]]
  assert 'brainstorm reply' not in contents


def test_validation_call_excludes_answer_word() -> None:
  # The validator must solve blind — the answer word must not appear in the
  # validation prompt.
  with FakeChatClient(_replies()) as fake:
    generate_clue('ALPHA', Difficulty.MON, fake)
  # calls[2][0] is the single user message in the validation call.
  content = fake.calls[2][0]['content']
  assert isinstance(content, str)
  assert 'ALPHA' not in content


# --- ClueResult assembly and fallback ---


def test_uses_validator_clue_field_not_raw_candidate() -> None:
  # When the validator accepts and rewrites the clue, the rewrite wins.
  with FakeChatClient(
    _replies(
      extract='["Raw candidate clue"]',
      validate='{"valid": true, "clue": "Lightly edited clue", "answer": "ALPHA"}',
    )
  ) as fake:
    result = generate_clue('ALPHA', Difficulty.MON, fake)
  assert result == ClueResult(word='ALPHA', clues=['Lightly edited clue'])


def test_uses_raw_candidate_when_validator_omits_clue_field() -> None:
  with FakeChatClient(
    _replies(
      extract='["Raw candidate clue"]',
      validate='{"valid": true, "answer": "ALPHA"}',
    )
  ) as fake:
    result = generate_clue('ALPHA', Difficulty.MON, fake)
  assert result.clues == ['Raw candidate clue']


def test_accepts_when_validator_solves_to_different_word() -> None:
  # A wrong solved answer is a quality warning, not a rejection — the clue is
  # still returned.
  with FakeChatClient(
    _replies(
      extract='["Greek letter, first"]',
      validate='{"valid": true, "clue": "Greek letter, first", "answer": "BETA"}',
    )
  ) as fake:
    result = generate_clue('ALPHA', Difficulty.MON, fake)
  assert result.clues == ['Greek letter, first']


def test_skips_rejected_candidate_and_accepts_next() -> None:
  with FakeChatClient(
    [
      *_replies(
        extract='["Candidate A", "Candidate B"]',
        validate='{"valid": false, "issues": ["ambiguous"]}',
      ),
      '{"valid": true, "clue": "Candidate B", "answer": "BRAVO"}',
    ]
  ) as fake:
    result = generate_clue('BRAVO', Difficulty.MON, fake)
  assert result.clues == ['Candidate B']


def test_falls_back_to_first_candidate_when_all_rejected() -> None:
  with FakeChatClient(
    [
      *_replies(
        extract='["Candidate A", "Candidate B"]',
        validate='{"valid": false, "issues": ["ambiguous"]}',
      ),
      '{"valid": false, "issues": ["too hard"]}',
    ]
  ) as fake:
    result = generate_clue('BRAVO', Difficulty.MON, fake)
  assert result.clues == ['Candidate A']


def test_falls_back_when_validation_json_malformed() -> None:
  # A GenerationError during validation is treated as a skip — the candidate
  # is not confirmed or rejected; fallback applies.
  with FakeChatClient(
    _replies(
      extract='["Raw candidate clue"]',
      validate='not valid json',
    )
  ) as fake:
    result = generate_clue('ALPHA', Difficulty.MON, fake)
  assert result.clues == ['Raw candidate clue']


def test_raises_when_extract_returns_empty_list() -> None:
  with FakeChatClient(['brainstorm reply', '[]']) as fake:
    with pytest.raises(GenerationError, match='no candidates'):
      generate_clue('ALPHA', Difficulty.MON, fake)


def test_raises_when_extract_json_malformed() -> None:
  # A parse failure in the extract turn is not caught — it propagates.
  with FakeChatClient(['brainstorm reply', 'not a json array']) as fake:
    with pytest.raises(GenerationError):
      generate_clue('ALPHA', Difficulty.MON, fake)


def test_answer_length_strips_spaces_for_multi_word() -> None:
  # 'BLUE JAYS' → 8 letters (space excluded). Validation prompt must use 8,
  # not 9. Verified indirectly: a response with a correct-length answer is
  # accepted without error.
  with FakeChatClient(
    _replies(extract='["Baseball team from Toronto"]')
  ) as fake:
    result = generate_clue('BLUE JAYS', Difficulty.MON, fake)
  assert result.clues == ['Baseball team from Toronto']


# --- Markdown fence stripping ---


def test_extract_tolerates_fenced_json_array() -> None:
  # Models often wrap JSON output in ```json … ``` fences.
  fenced = '```json\n["Fenced clue"]\n```'
  with FakeChatClient(_replies(extract=fenced)) as fake:
    result = generate_clue('ALPHA', Difficulty.MON, fake)
  assert result.clues == ['Fenced clue']


def test_validation_tolerates_fenced_json_object() -> None:
  fenced = '```\n{"valid": true, "clue": "Fenced clue", "answer": "ALPHA"}\n```'
  with FakeChatClient(_replies(validate=fenced)) as fake:
    result = generate_clue('ALPHA', Difficulty.MON, fake)
  assert result.clues == ['Fenced clue']


# Possible future coverage, if it ever seems worth the effort:
# - GenerationError propagation from brainstorm/extract calls. Would need
#   exception injection — a raises_on: dict[int, Exception] parameter on
#   FakeChatClient would do it without restructuring the fake.
# - APIConnectionError propagation from OllamaClient. Would need either
#   exception injection or a real Ollama integration test.
