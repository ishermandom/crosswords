# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for clue_gen.prompt."""

from clue_gen.prompt import Difficulty, brainstorm_messages, validation_messages


class TestBrainstormMessages:
  # TODO: Phase 3 redesigns the brainstorm prompt and may introduce a
  # multi-turn opening sequence — update message-count and content assertions.
  def test_returns_single_user_message(self):
    msgs = brainstorm_messages('ALPHA', Difficulty.MON)
    assert len(msgs) == 1
    assert msgs[0]['role'] == 'user'

  def test_content_includes_answer_word(self):
    msgs = brainstorm_messages('BRAVO', Difficulty.MON)
    assert 'BRAVO' in msgs[0]['content']

  def test_content_includes_difficulty_label(self):
    msgs = brainstorm_messages('ALPHA', Difficulty.SAT)
    assert 'Sat' in msgs[0]['content']

  def test_content_includes_difficulty_description(self):
    msgs = brainstorm_messages('ALPHA', Difficulty.SAT)
    # Checks that the human-readable description is present, not just the label.
    assert 'maximum difficulty' in msgs[0]['content'].lower()


class TestValidationMessages:
  # TODO: Phase 3 redesigns the validation prompt — update content assertions.
  def test_returns_single_user_message(self):
    msgs = validation_messages('Capital of France', 5)
    assert len(msgs) == 1
    assert msgs[0]['role'] == 'user'

  def test_content_includes_clue(self):
    msgs = validation_messages('Capital of France', 5)
    assert 'Capital of France' in msgs[0]['content']

  def test_content_includes_answer_length(self):
    msgs = validation_messages('Capital of France', 5)
    assert '5' in msgs[0]['content']

  def test_content_includes_blank_placeholder(self):
    msgs = validation_messages('Some clue', 4)
    assert '____' in msgs[0]['content']

  def test_blank_placeholder_matches_answer_length(self):
    msgs = validation_messages('Some clue', 7)
    assert '_______' in msgs[0]['content']
