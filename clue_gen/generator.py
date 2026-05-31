# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Per-word clue generation pipeline."""

import json
import logging
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass

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
  t_word = time.perf_counter()

  # Stage 1: brainstorm, then extract candidates as a structured list.
  _log.info(f'[{word}] brainstorm start')
  messages: Sequence[Message] = brainstorm_messages(word, difficulty)
  messages = client.chat(messages).messages
  _log.info(f'[{word}] brainstorm done ({time.perf_counter() - t_word:.1f}s)')
  _log.debug(f'[{word}] brainstorm reply:\n{messages[-1]["content"]}')

  # TODO: Phase 3 — replace with multi-turn brainstorm sequence.
  extract_turn: Message = {
    'role': 'user',
    'content': (
      'Output only your candidate clues as a JSON array of strings, '
      'with no other text. Example: ["Clue one", "Clue two"]'
    ),
  }
  t_extract = time.perf_counter()
  _log.info(f'[{word}] extract start')
  extract_reply = client.chat([*messages, extract_turn]).reply
  _log.debug(f'[{word}] extract reply:\n{extract_reply}')
  candidates = _extract_json_list(extract_reply)
  _log.info(
    f'[{word}] extract done ({time.perf_counter() - t_extract:.1f}s):'
    f' {len(candidates)} candidate(s)'
  )

  # Stage 2: validate each candidate with a blind solver (independent call).
  answer_length = len(word.replace(' ', ''))
  for i, clue in enumerate(candidates):
    _log.info(f'[{word}] validate candidate {i + 1}/{len(candidates)}')
    try:
      val_result = client.chat(validation_messages(clue, answer_length))
      _log.debug(f'[{word}] validation reply:\n{val_result.reply}')
      parsed = _extract_json_object(val_result.reply)
    except GenerationError as e:
      # Validation is a quality signal, not a correctness gate — a malformed
      # response means we lose signal for this candidate, not that the clue
      # itself is wrong. Skip and try the next candidate; the fallback below
      # handles the case where all are skipped.
      _log.warning(
        f'validation unparseable for {word!r}: {e}; skipping candidate'
      )
      continue
    if not parsed.get('valid'):
      continue
    raw_answer = parsed.get('answer', '')
    if not isinstance(raw_answer, str):
      # Same reasoning as the GenerationError case above: a schema violation
      # in the validator's response is the validator's failure, not the clue's.
      _log.warning(
        f'validator returned non-string answer for {word!r}:'
        f' {raw_answer!r}; skipping candidate'
      )
      continue
    solved = raw_answer.upper().replace(' ', '')
    if solved != word.upper().replace(' ', ''):
      # The validator accepted the clue but solved it to a different word —
      # logged so prompt quality issues are visible, but not fatal since the
      # clue may still be usable.
      _log.warning(f'validator solved clue for {word!r} as {solved!r}')
    elapsed = time.perf_counter() - t_word
    _log.info(f'[{word}] done ({elapsed:.1f}s total)')
    raw_clue = parsed.get('clue')
    return ClueResult(
      word=word,
      clues=[raw_clue if isinstance(raw_clue, str) else clue],
    )

  if not candidates:
    raise GenerationError(f'no candidates extracted for {word!r}')
  _log.warning(f'no valid clue found for {word!r}; using first candidate')
  elapsed = time.perf_counter() - t_word
  _log.info(f'[{word}] done with fallback ({elapsed:.1f}s total)')
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


def _extract_json_object(text: str) -> dict[str, object]:
  # object rather than Any: forces explicit type narrowing at each use site.
  # TODO: replace with a TypedDict once the validator response schema
  # stabilizes in Phase 3 — that would eliminate all the isinstance checks.
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
