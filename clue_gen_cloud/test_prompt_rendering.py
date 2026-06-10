# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Tests for prompt template loading and rendering."""

from pathlib import Path

import prompt_rendering
from prompt_rendering import PromptTemplates, WordEntry

FAKE_TEMPLATES = PromptTemplates(
  specification='THE SPEC',
  generation_template=(
    'Mix: {{CLUE_MIX}}\nNote: {{CATEGORY_NOTE}}\nWords:\n{{WORDS}}'
  ),
  verification_template='Review:\n{{CLUES_JSONL}}',
)


def test_default_clue_mix_matches_kickoff_sentence() -> None:
  assert (
    prompt_rendering.render_clue_mix(2, 2)
    == '2 American-style (one medium, one hard) and 2 cryptic-style'
  )


def test_non_default_mix_splits_difficulty_evenly() -> None:
  assert prompt_rendering.render_clue_mix(3, 1) == (
    '3 American-style (two medium, one hard) and 1 cryptic-style (one medium)'
  )


def test_zero_count_style_is_omitted() -> None:
  assert (
    prompt_rendering.render_clue_mix(0, 2)
    == '2 cryptic-style (one medium, one hard)'
  )


def test_generation_prompt_substitutes_everything() -> None:
  prompt = prompt_rendering.build_generation_prompt(
    FAKE_TEMPLATES,
    [WordEntry('ZERO'), WordEntry('NIL')],
    american_per_word=2,
    cryptic_per_word=2,
    category_note='watch for digit leaks',
  )
  assert 'ZERO' in prompt and 'NIL' in prompt
  assert 'watch for digit leaks' in prompt
  assert '{{' not in prompt


def test_generation_prompt_excludes_the_spec() -> None:
  # The spec travels as the system prompt (a stable, cacheable prefix),
  # so the user-turn prompt must not duplicate it.
  prompt = prompt_rendering.build_generation_prompt(
    FAKE_TEMPLATES,
    [WordEntry('ZERO')],
    american_per_word=2,
    cryptic_per_word=2,
    category_note='',
  )
  assert 'THE SPEC' not in prompt


def test_retry_entry_carries_failure_reasons_on_one_line() -> None:
  line = prompt_rendering.render_word_line(
    WordEntry('SOUTHWARD', ['[cryptic] definition is mid-clue'])
  )
  assert line.startswith('SOUTHWARD')
  assert 'RETRY' in line
  assert 'definition is mid-clue' in line
  assert '\n' not in line


def test_verification_prompt_includes_clue_lines() -> None:
  prompt = prompt_rendering.build_verification_prompt(
    FAKE_TEMPLATES, ['{"word": "ZERO"}', '{"word": "NIL"}']
  )
  assert '{"word": "ZERO"}' in prompt
  assert '{{' not in prompt


def test_verification_prompt_excludes_the_spec() -> None:
  # Same contract as generation: the spec rides in the system prompt.
  prompt = prompt_rendering.build_verification_prompt(
    FAKE_TEMPLATES, ['{"word": "ZERO"}']
  )
  assert 'THE SPEC' not in prompt


def test_load_templates_from_project_directory() -> None:
  templates = prompt_rendering.load_templates(Path(__file__).parent)
  assert '{{WORDS}}' in templates.generation_template
  assert '{{CLUE_MIX}}' in templates.generation_template
  assert '{{CATEGORY_NOTE}}' in templates.generation_template
  assert '{{CLUES_JSONL}}' in templates.verification_template
  assert 'crossword' in templates.specification
