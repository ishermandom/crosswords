# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Parsing for CLI input formats: word lists and clue entry files."""

from dataclasses import dataclass
from typing import TextIO


def _strip_comment(line: str) -> str:
  """Strip an inline # comment and surrounding whitespace from a line.

  Everything from the first # to end-of-line is treated as a comment,
  so a full-line comment (# ...) becomes an empty string.
  """
  return line.split('#')[0].strip()


def load_words(f: TextIO) -> list[str]:
  """Load and normalize answer words from an open text stream.

  Strips blank lines and # comments (full-line and inline).
  Returns words uppercased.
  """
  words = []
  for line in f:
    word = _strip_comment(line)
    if word:
      words.append(word.upper())
  return words


@dataclass(frozen=True)
class ClueEntry:
  """A single answer/clue pair from a batch clue-entry file."""

  answer: str
  clue_text: str


def load_clue_entries(f: TextIO) -> list[ClueEntry]:
  """Load clue entries from an open text stream.

  Each non-blank, non-comment line must be: ANSWER clue text
  The answer is the first whitespace-delimited token; the rest is the clue.
  Strips blank lines and # comments (full-line and inline).
  Returns answers uppercased.
  """
  entries = []
  for line in f:
    line = _strip_comment(line)
    if not line:
      continue
    answer, _, clue_text = line.partition(' ')
    entries.append(
      ClueEntry(answer=answer.upper(), clue_text=clue_text.strip())
    )
  return entries
