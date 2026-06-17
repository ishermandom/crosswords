# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for clue_gen.prompt."""

import pytest

from clue_gen.prompt import (
  Difficulty,
  brainstorm_messages,
  brainstorm_system_prompt,
  brainstorm_turns,
  validation_messages,
)

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


# --- brainstorm_system_prompt ---


# TODO: Tighten these assertions once day descriptions are calibrated against
# real clue examples — the current descriptions are initial estimates.
def test_brainstorm_system_prompt_differs_by_difficulty() -> None:
  assert brainstorm_system_prompt(Difficulty.MON) != brainstorm_system_prompt(
    Difficulty.SAT
  )


@pytest.mark.xfail(strict=True)
def test_brainstorm_system_prompt_sat_requires_misdirection() -> None:
  prompt = brainstorm_system_prompt(Difficulty.SAT)
  assert 'misdirection' in prompt.lower()


def test_brainstorm_system_prompt_mon_allows_direct_definitions() -> None:
  prompt = brainstorm_system_prompt(Difficulty.MON)
  assert 'direct' in prompt.lower()


# --- brainstorm_turns ---


@pytest.mark.xfail(strict=True)
def test_brainstorm_turns_returns_seven_turns() -> None:
  # Seven turns = one per cognitive phase (analysis → mechanisms → filter →
  # drafting → solver sim → refinement → extract).
  turns = brainstorm_turns('CRANE', Difficulty.MON)
  assert len(turns) == 7


@pytest.mark.xfail(strict=True)
def test_brainstorm_turns_first_turn_contains_answer_word() -> None:
  turns = brainstorm_turns('CRANE', Difficulty.MON)
  # Turn 1 is answer analysis — the word must be present for the model to
  # analyze its morphology and near-miss alternatives.
  assert 'CRANE' in turns[0]


@pytest.mark.xfail(strict=True)
def test_brainstorm_turns_mechanism_turn_forbids_clue_writing() -> None:
  turns = brainstorm_turns('CRANE', Difficulty.MON)
  # Turn 2 generates mechanisms only. The explicit prohibition is the primary
  # mitigation for the LLM failure mode of converging on one mechanism and
  # producing variations of it instead of exploring broadly.
  content = turns[1].lower()
  assert 'do not' in content or "don't" in content


@pytest.mark.xfail(strict=True)
def test_brainstorm_turns_solver_sim_turn_asks_for_real_alternatives() -> None:
  turns = brainstorm_turns('CRANE', Difficulty.MON)
  # Turn 5 is the Bullshit Rating check: it must ask the model to verify that
  # the alternative answers a solver would consider are real words or phrases.
  content = turns[4].lower()
  assert 'real' in content or 'actual' in content


@pytest.mark.xfail(strict=True)
def test_brainstorm_turns_extract_turn_references_clues_schema() -> None:
  turns = brainstorm_turns('CRANE', Difficulty.MON)
  # Turn 7 is the structured-output extract; it must name the {"clues": [...]}
  # schema so the model produces output the generator can parse.
  assert '"clues"' in turns[6]
