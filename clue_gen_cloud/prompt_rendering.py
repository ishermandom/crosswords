# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Assembly of the generation and verification prompts from template files.

All prompt text lives in CLUE_SPEC.md and prompts/*.md — this module only
substitutes the template variables. No prompt wording is defined in code.

The spec is NOT part of the rendered prompts: it travels separately as the
CLI's system prompt (see claude_cli.build_cli_command), where its stable,
byte-identical prefix is cached across calls. The rendered prompts carry
only the per-task instructions and the per-batch variables.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

NUMBER_WORDS = (
  'zero',
  'one',
  'two',
  'three',
  'four',
  'five',
  'six',
  'seven',
  'eight',
  'nine',
  'ten',
  'eleven',
  'twelve',
)


@dataclass(frozen=True)
class PromptTemplates:
  """The three template texts every prompt is assembled from."""

  specification: str
  generation_template: str
  verification_template: str


@dataclass(frozen=True)
class WordEntry:
  """One word slated for a batch, with retry context if this is its
  second (and final) generation attempt."""

  word: str
  retry_reasons: Sequence[str] = ()


def load_templates(root: Path) -> PromptTemplates:
  """Read the spec and prompt templates from the project directory."""
  return PromptTemplates(
    specification=(root / 'CLUE_SPEC.md').read_text(),
    generation_template=(root / 'prompts' / 'generate.md').read_text(),
    verification_template=(root / 'prompts' / 'verify.md').read_text(),
  )


def number_word(count: int) -> str:
  """The English word for a small count, falling back to digits."""
  if 0 <= count < len(NUMBER_WORDS):
    return NUMBER_WORDS[count]
  return str(count)


def difficulty_split(count: int) -> str:
  """Difficulty tags for a style, split roughly evenly: medium-heavy.

  E.g. 3 -> "two medium, one hard".
  """
  medium_count = (count + 1) // 2
  hard_count = count // 2
  parts = []
  if medium_count:
    parts.append(f'{number_word(medium_count)} medium')
  if hard_count:
    parts.append(f'{number_word(hard_count)} hard')
  return ', '.join(parts)


def render_clue_mix(american_per_word: int, cryptic_per_word: int) -> str:
  """The {{CLUE_MIX}} sentence for the requested per-word clue counts.

  The default 2+2 mix renders exactly as the kickoff specifies; other
  counts split difficulty tags roughly evenly between medium and hard.
  """
  if (american_per_word, cryptic_per_word) == (2, 2):
    return '2 American-style (one medium, one hard) and 2 cryptic-style'
  parts = []
  if american_per_word:
    parts.append(
      f'{american_per_word} American-style'
      f' ({difficulty_split(american_per_word)})'
    )
  if cryptic_per_word:
    parts.append(
      f'{cryptic_per_word} cryptic-style ({difficulty_split(cryptic_per_word)})'
    )
  if not parts:
    raise ValueError('at least one style must have a nonzero count')
  return ' and '.join(parts)


def render_word_line(entry: WordEntry) -> str:
  """One word's line in the {{WORDS}} list.

  Retry entries carry their previous failures inline, on a single line
  so the list stays one-word-per-line for the generator.
  """
  if not entry.retry_reasons:
    return entry.word
  reasons = '; '.join(' '.join(r.split()) for r in entry.retry_reasons)
  return (
    f'{entry.word} — RETRY (second and final attempt; the previous'
    f' attempt failed, generate a fresh set avoiding these failures):'
    f' {reasons}'
  )


def build_generation_prompt(
  templates: PromptTemplates,
  entries: Sequence[WordEntry],
  american_per_word: int,
  cryptic_per_word: int,
  category_note: str,
) -> str:
  """The user-turn prompt for one GENERATE call (filled template)."""
  return (
    templates.generation_template.replace(
      '{{CLUE_MIX}}', render_clue_mix(american_per_word, cryptic_per_word)
    )
    .replace('{{CATEGORY_NOTE}}', category_note)
    .replace('{{WORDS}}', '\n'.join(render_word_line(e) for e in entries))
  )


def build_verification_prompt(
  templates: PromptTemplates, clue_lines: Sequence[str]
) -> str:
  """The user-turn prompt for one VERIFY call (filled template)."""
  return templates.verification_template.replace(
    '{{CLUES_JSONL}}', '\n'.join(clue_lines)
  )
