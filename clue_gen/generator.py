# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Per-word clue generation pipeline."""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from collections.abc import Sequence

from clue_gen.client import ChatClient, GenerationError, Message
from clue_gen.prompt import Difficulty, brainstorm_messages, validation_messages

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClueResult:
  """Generated clue(s) for a single answer word."""

  word: str
  clues: list[str]


def generate_clue(
  word: str,
  difficulty: Difficulty,
  client: ChatClient,
) -> ClueResult:
  """Run the two-stage pipeline for a single word.

  Stage 1: multi-turn brainstorm conversation producing candidate clues.
  Stage 2: independent validation call per candidate, solving blind.

  Warns if the validator solves a clue to the wrong answer, or if no candidate
  passes validation (first candidate is used as fallback).
  """
  # Stage 1: brainstorm, then extract candidates as a structured list.
  messages: Sequence[Message] = brainstorm_messages(word, difficulty)
  messages = client.chat(messages).messages

  # TODO: Phase 3 — replace with multi-turn brainstorm sequence.
  extract_turn: Message = {
    'role': 'user',
    'content': (
      'Output only your candidate clues as a JSON array of strings, '
      'with no other text. Example: ["Clue one", "Clue two"]'
    ),
  }
  extract_reply = client.chat([*messages, extract_turn]).reply
  candidates = _extract_json_list(extract_reply)

  # Stage 2: validate each candidate with a blind solver (independent call).
  answer_length = len(word.replace(' ', ''))
  for clue in candidates:
    try:
      val_result = client.chat(validation_messages(clue, answer_length))
      parsed = _extract_json_object(val_result.reply)
    except GenerationError as e:
      # Validation is a quality signal, not a correctness gate — a malformed
      # response means we lose signal for this candidate, not that the clue
      # itself is wrong. Skip and try the next candidate; the fallback below
      # handles the case where all are skipped.
      _log.warning(
        'validation unparseable for %r: %s; skipping candidate', word, e
      )
      continue
    if not parsed.get('valid'):
      continue
    raw_answer = parsed.get('answer', '')
    if not isinstance(raw_answer, str):
      # Same reasoning as the GenerationError case above: a schema violation
      # in the validator's response is the validator's failure, not the clue's.
      _log.warning(
        'validator returned non-string answer for %r: %r; skipping candidate',
        word,
        raw_answer,
      )
      continue
    solved = raw_answer.upper().replace(' ', '')
    if solved != word.upper().replace(' ', ''):
      # The validator accepted the clue but solved it to a different word —
      # logged so prompt quality issues are visible, but not fatal since the
      # clue may still be usable.
      _log.warning('validator solved clue for %r as %r', word, solved)
    return ClueResult(word=word, clues=[parsed.get('clue', clue)])

  if not candidates:
    raise GenerationError(f'no candidates extracted for {word!r}')
  _log.warning('no valid clue found for %r; using first candidate', word)
  return ClueResult(word=word, clues=[candidates[0]])


def _strip_fences(text: str) -> str:
  """Strip leading/trailing markdown code fences from model output."""
  text = re.sub(r'^```(?:json)?\s*\n?', '', text.strip())
  return re.sub(r'\n?```\s*$', '', text)


def _extract_json_list(text: str) -> list[str]:
  """Extract a JSON array of strings from model output."""
  text = _strip_fences(text).strip()
  try:
    parsed = json.loads(text)
  except json.JSONDecodeError as e:
    raise GenerationError(
      f'Expected a JSON array of strings, got: {text[:120]!r}'
    ) from e
  if not isinstance(parsed, list) or not all(
    isinstance(item, str) for item in parsed
  ):
    raise GenerationError(
      f'Expected a JSON array of strings, got: {text[:120]!r}'
    )
  return parsed


def _extract_json_object(text: str) -> dict[str, Any]:
  """Extract a JSON object from model output, tolerating markdown fences."""
  text = _strip_fences(text).strip()
  try:
    parsed = json.loads(text)
  except json.JSONDecodeError as e:
    raise GenerationError(f'Expected a JSON object, got: {text[:120]!r}') from e
  if not isinstance(parsed, dict):
    raise GenerationError(
      f'Expected a JSON object, got {type(parsed).__name__}: {text[:120]!r}'
    )
  return parsed
