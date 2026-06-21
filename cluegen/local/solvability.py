# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Blind solvability validation call."""

import json
import logging
from collections.abc import Sequence

from cluegen.local.client import ChatClient, Message
from cluegen.local.parsing import strip_markdown_fences
from cluegen.local.prompt import Difficulty
from openai.types.shared_params import ResponseFormatJSONSchema

_log = logging.getLogger(__name__)


def _section(label: str) -> str:
  """Format a dashes section header for log output (60 chars total)."""
  return f'\n--- {label} {"-" * max(0, 55 - len(label))}'


class SolvabilityParseError(Exception):
  """Raised when the guesses reply cannot be parsed as valid JSON."""


# Rank threshold for a solvability pass; answer must appear at or above this
# position in the length-filtered guess list.
# TODO: calibrate against a golden set; see validation.md — "Open questions".
DEFAULT_MAX_ANSWER_RANK: int = 10

_SYSTEM_PROMPT = (
  'You are an experienced NYT crossword solver. '
  'NYT crossword clues often exploit wordplay, double meanings, and '
  'deliberate misdirection — the surface reading of a clue is rarely '
  'the whole story.'
)

# Style hints calibrate solver persistence without naming the difficulty day.
# Per validation.md — "Solvability call / Persona and context".
_STYLE_HINTS: dict[Difficulty, str] = {
  Difficulty.MON: (
    'The clue is direct; a single clear interpretation should lead to the '
    'answer.'
  ),
  Difficulty.TUE: (
    'The clue may have mild misdirection; consider more than one reading.'
  ),
  Difficulty.WED: (
    'The clue likely uses wordplay or misdirection; consider multiple '
    'interpretations before committing.'
  ),
  Difficulty.THU: (
    'The clue uses wordplay or misdirection; consider multiple '
    'interpretations before committing.'
  ),
  Difficulty.FRI: (
    'The clue almost certainly uses wordplay or misdirection; explore many '
    'interpretations before committing.'
  ),
  Difficulty.SAT: (
    'The clue is devious; explore all possible wordplay angles and '
    'interpretations before committing.'
  ),
}

_GUESSES_PROMPT = (
  'Based on your reasoning above, commit to a ranked list of your best '
  'guesses, most confident first. Include significantly more guesses than '
  'you think you need — aim for 30 or more. '
  'Respond with JSON only, no explanation:\n'
  '{"guesses": ["WORD", "WORD", ...]}'
)

# JSON schema for the guesses structured output call.
_GUESSES_FORMAT: dict[str, object] = {
  'type': 'object',
  'properties': {
    'guesses': {
      'type': 'array',
      'items': {'type': 'string'},
    },
  },
  'required': ['guesses'],
}


def _build_scratchpad_messages(
  clue_text: str, answer_length: int, difficulty: Difficulty
) -> Sequence[Message]:
  """Build the scratchpad messages for the solvability call."""
  style_hint = _STYLE_HINTS[difficulty]
  return [
    {'role': 'system', 'content': _SYSTEM_PROMPT},
    {
      'role': 'user',
      'content': (
        f'Clue: {clue_text}\n'
        f'Answer length: {answer_length} letters\n\n'
        f'Style hint: {style_hint}\n\n'
        'Reason through the clue: consider multiple interpretations, '
        'possible wordplay angles, and candidate answers.'
      ),
    },
  ]


def _parse_guesses(reply: str) -> list[str]:
  """Strip markdown fences and parse the JSON guesses list from the guesses reply.

  Raises SolvabilityParseError if the reply is not valid JSON or is missing the
  'guesses' key.
  """
  text = strip_markdown_fences(reply)
  try:
    data = json.loads(text)
    return [str(guess).strip() for guess in data['guesses']]
  except (json.JSONDecodeError, KeyError) as error:
    _log.error(f'failed to parse guesses reply: {error}\nRaw reply: {reply}')
    raise SolvabilityParseError(
      f'failed to parse guesses reply: {error}'
    ) from error


def validate_solvability(
  clue_text: str,
  answer: str,
  difficulty: Difficulty,
  client: ChatClient,
  max_answer_rank: int = DEFAULT_MAX_ANSWER_RANK,
) -> bool:
  """Run the blind solvability call and return pass/fail.

  The answer word is withheld from the prompt; the model guesses as a solver
  would. Returns True if the answer appears within the top max_answer_rank
  length-filtered guesses.
  """
  answer_length = len(answer)

  # Scratchpad: model reasons through interpretations and candidates.
  scratchpad_messages = _build_scratchpad_messages(
    clue_text, answer_length, difficulty
  )
  scratchpad_result = client.chat(scratchpad_messages)
  _log.debug(f'{_section("scratchpad")}\n\n{scratchpad_result.reply}\n')

  # Guesses: extends the conversation so the model sees its own scratchpad
  # reasoning before committing to a ranked list.
  guesses_messages: Sequence[Message] = [
    *scratchpad_result.messages,
    {'role': 'user', 'content': _GUESSES_PROMPT},
  ]
  guesses_result = client.chat(
    guesses_messages,
    response_format=ResponseFormatJSONSchema(
      type='json_schema',
      json_schema={
        'name': 'guesses',
        'strict': True,
        'schema': _GUESSES_FORMAT,
      },
    ),
  )

  # TODO: retry loop on JSON parse failure; see validation.md — "Error handling
  #   and logging".
  guesses = _parse_guesses(guesses_result.reply)

  # Normalize to uppercase and filter to correct letter count.
  answer_upper = answer.upper()
  filtered = [g.upper() for g in guesses if len(g) == answer_length]

  if guesses:
    raw_lines = '\n  '.join(
      f'{i + 1}. {g.upper()}' for i, g in enumerate(guesses)
    )
    _log.debug(f'Raw guesses ({len(guesses)}):\n  {raw_lines}')
  else:
    _log.debug('Raw guesses (0): (none)')
  if filtered:
    filtered_lines = '\n  '.join(
      f'{i + 1}. {g}' for i, g in enumerate(filtered)
    )
    _log.debug(
      f'Length-{answer_length} guesses ({len(filtered)}):\n  {filtered_lines}'
    )
  else:
    _log.debug(f'Length-{answer_length} guesses (0): (none)')

  try:
    rank = filtered.index(answer_upper) + 1  # 1-indexed
  except ValueError:
    _log.debug(f'Answer {answer_upper!r} absent from filtered guesses')
    return False

  _log.debug(f'Answer {answer_upper!r} at rank {rank} (max {max_answer_rank})')
  return rank <= max_answer_rank
