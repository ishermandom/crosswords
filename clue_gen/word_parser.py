# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Word list loading."""

import io


def load_words(f: io.TextIOBase) -> list[str]:
  """Load and normalize answer words from an open text stream.

  Strips blank lines, full-line # comments, and inline # comments.
  Returns words uppercased.
  """
  words = []
  for line in f:
    word = line.split('#')[0].strip()
    if word:
      words.append(word.upper())
  return words


def load_words_file(path: str) -> list[str]:
  """Open `path` and delegate to `load_words`.

  Raises FileNotFoundError if path doesn't exist.
  """
  with open(path, encoding='utf-8') as f:
    return load_words(f)
