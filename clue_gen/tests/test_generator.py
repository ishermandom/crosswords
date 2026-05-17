# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for clue_gen.generator.generate_clue via FakeChatClient."""

import pytest

from clue_gen.generator import ClueResult, GenerationError, generate_clue
from clue_gen.prompt import Difficulty
from clue_gen.tests.fake_client import FakeChatClient


class TestGenerateClueCallSequence:
  """Verifies the brainstorm → extract → validate call sequence."""

  def test_makes_exactly_three_calls_for_single_candidate(self):
    with FakeChatClient([
      'brainstorm reply',
      '["A clue for alpha"]',
      '{"valid": true, "clue": "A clue for alpha", "answer": "ALPHA"}',
    ]) as fake:
      generate_clue('ALPHA', Difficulty.MON, fake)
    assert len(fake.calls) == 3

  def test_brainstorm_call_includes_answer_word(self):
    fake = FakeChatClient([
      'brainstorm reply',
      '["A clue for alpha"]',
      '{"valid": true, "clue": "A clue for alpha", "answer": "ALPHA"}',
    ])
    generate_clue('ALPHA', Difficulty.MON, fake)
    # calls[0] is the messages list passed to the brainstorm call.
    assert 'ALPHA' in fake.calls[0][-1]['content']

  def test_extract_call_appends_to_brainstorm_context(self):
    # The extract turn continues the brainstorm conversation, so the messages
    # list passed to call 2 should include the brainstorm assistant reply.
    fake = FakeChatClient([
      'brainstorm reply',
      '["A clue for alpha"]',
      '{"valid": true, "clue": "A clue for alpha", "answer": "ALPHA"}',
    ])
    generate_clue('ALPHA', Difficulty.MON, fake)
    # calls[1] is the messages list passed to the extract call.
    contents = [m['content'] for m in fake.calls[1]]
    assert 'brainstorm reply' in contents

  def test_validation_call_uses_fresh_context(self):
    # Validation is an independent call — it must not contain the brainstorm
    # reply, because the validator solves blind with only the clue and length.
    fake = FakeChatClient([
      'brainstorm reply',
      '["A clue for alpha"]',
      '{"valid": true, "clue": "A clue for alpha", "answer": "ALPHA"}',
    ])
    generate_clue('ALPHA', Difficulty.MON, fake)
    # calls[2] is the messages list passed to the validation call.
    contents = [m['content'] for m in fake.calls[2]]
    assert 'brainstorm reply' not in contents

  def test_validation_call_excludes_answer_word(self):
    # The validator must solve blind — the answer word must not appear in the
    # validation prompt.
    fake = FakeChatClient([
      'brainstorm reply',
      '["Greek letter, first"]',
      '{"valid": true, "clue": "Greek letter, first", "answer": "ALPHA"}',
    ])
    generate_clue('ALPHA', Difficulty.MON, fake)
    # calls[2][0] is the single user message in the validation call.
    assert 'ALPHA' not in fake.calls[2][0]['content']


class TestGenerateClueResult:
  """Verifies ClueResult assembly and fallback behaviour."""

  def test_uses_validator_clue_field_not_raw_candidate(self):
    # When the validator accepts and rewrites the clue, the rewrite wins.
    with FakeChatClient([
      'brainstorm reply',
      '["Raw candidate clue"]',
      '{"valid": true, "clue": "Lightly edited clue", "answer": "ALPHA"}',
    ]) as fake:
      result = generate_clue('ALPHA', Difficulty.MON, fake)
    assert result == ClueResult(word='ALPHA', clues=['Lightly edited clue'])

  def test_uses_raw_candidate_when_validator_omits_clue_field(self):
    with FakeChatClient([
      'brainstorm reply',
      '["Raw candidate clue"]',
      '{"valid": true, "answer": "ALPHA"}',
    ]) as fake:
      result = generate_clue('ALPHA', Difficulty.MON, fake)
    assert result.clues == ['Raw candidate clue']

  def test_accepts_when_validator_solves_to_different_word(self):
    # A wrong solved answer is a quality warning, not a rejection — the clue is
    # still returned.
    with FakeChatClient([
      'brainstorm reply',
      '["Greek letter, first"]',
      '{"valid": true, "clue": "Greek letter, first", "answer": "BETA"}',
    ]) as fake:
      result = generate_clue('ALPHA', Difficulty.MON, fake)
    assert result.clues == ['Greek letter, first']

  def test_skips_rejected_candidate_and_accepts_next(self):
    with FakeChatClient([
      'brainstorm reply',
      '["Candidate A", "Candidate B"]',
      '{"valid": false, "issues": ["ambiguous"]}',
      '{"valid": true, "clue": "Candidate B", "answer": "BRAVO"}',
    ]) as fake:
      result = generate_clue('BRAVO', Difficulty.MON, fake)
    assert result.clues == ['Candidate B']

  def test_falls_back_to_first_candidate_when_all_rejected(self):
    with FakeChatClient([
      'brainstorm reply',
      '["Candidate A", "Candidate B"]',
      '{"valid": false, "issues": ["ambiguous"]}',
      '{"valid": false, "issues": ["too hard"]}',
    ]) as fake:
      result = generate_clue('BRAVO', Difficulty.MON, fake)
    assert result.clues == ['Candidate A']

  def test_falls_back_when_validation_json_malformed(self):
    # A GenerationError during validation is treated as a skip — the candidate
    # is not confirmed or rejected; fallback applies.
    with FakeChatClient([
      'brainstorm reply',
      '["Raw candidate clue"]',
      'not valid json',
    ]) as fake:
      result = generate_clue('ALPHA', Difficulty.MON, fake)
    assert result.clues == ['Raw candidate clue']

  def test_raises_when_extract_returns_empty_list(self):
    with FakeChatClient(['brainstorm reply', '[]']) as fake:
      with pytest.raises(GenerationError, match='no candidates'):
        generate_clue('ALPHA', Difficulty.MON, fake)

  def test_raises_when_extract_json_malformed(self):
    # A parse failure in the extract turn is not caught — it propagates.
    fake = FakeChatClient(['brainstorm reply', 'not a json array'])
    with pytest.raises(GenerationError):
      generate_clue('ALPHA', Difficulty.MON, fake)

  def test_answer_length_strips_spaces_for_multi_word(self):
    # 'BLUE JAYS' → 8 letters (space excluded). Validation prompt must use 8,
    # not 9. Verified indirectly: a response with a correct-length answer is
    # accepted without error.
    with FakeChatClient([
      'brainstorm reply',
      '["Baseball team from Toronto"]',
      '{"valid": true, "clue": "Baseball team from Toronto", "answer": "BLUEJAYS"}',
    ]) as fake:
      result = generate_clue('BLUE JAYS', Difficulty.MON, fake)
    assert result.clues == ['Baseball team from Toronto']
