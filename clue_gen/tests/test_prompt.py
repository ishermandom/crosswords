# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for clue_gen.prompt."""

from clue_gen.prompt import Difficulty, brainstorm_messages, validation_messages

# --- brainstorm_messages ---
# TODO: Phase 3 redesigns the brainstorm prompt and may introduce a
# multi-turn opening sequence — update message-count and content assertions.


def test_brainstorm_returns_single_user_message() -> None:
  msgs = brainstorm_messages('ALPHA', Difficulty.MON)
  assert len(msgs) == 1
  assert msgs[0]['role'] == 'user'


def test_brainstorm_content_includes_answer_word() -> None:
  msgs = brainstorm_messages('BRAVO', Difficulty.MON)
  content = msgs[0]['content']
  assert isinstance(content, str)
  assert 'BRAVO' in content


def test_brainstorm_content_includes_difficulty_label() -> None:
  msgs = brainstorm_messages('ALPHA', Difficulty.SAT)
  content = msgs[0]['content']
  assert isinstance(content, str)
  assert 'Sat' in content


def test_brainstorm_content_includes_difficulty_description() -> None:
  msgs = brainstorm_messages('ALPHA', Difficulty.SAT)
  # Checks that the human-readable description is present, not just the label.
  content = msgs[0]['content']
  assert isinstance(content, str)
  assert 'maximum difficulty' in content.lower()


# --- validation_messages ---
# TODO: Phase 3 redesigns the validation prompt — update content assertions.


def test_validation_returns_single_user_message() -> None:
  msgs = validation_messages('Capital of France', 5)
  assert len(msgs) == 1
  assert msgs[0]['role'] == 'user'


def test_validation_content_includes_clue() -> None:
  msgs = validation_messages('Capital of France', 5)
  content = msgs[0]['content']
  assert isinstance(content, str)
  assert 'Capital of France' in content


def test_validation_content_includes_answer_length() -> None:
  msgs = validation_messages('Capital of France', 5)
  content = msgs[0]['content']
  assert isinstance(content, str)
  assert '5' in content


def test_validation_content_includes_blank_placeholder() -> None:
  msgs = validation_messages('Some clue', 4)
  content = msgs[0]['content']
  assert isinstance(content, str)
  assert '____' in content


def test_validation_blank_placeholder_matches_answer_length() -> None:
  msgs = validation_messages('Some clue', 7)
  content = msgs[0]['content']
  assert isinstance(content, str)
  assert '_______' in content
