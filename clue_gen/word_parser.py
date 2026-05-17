# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Word list loading."""


def load_words(path: str) -> list[str]:
  """Load and normalize answer words from a file.

  Strips blank lines, full-line # comments, and inline # comments.
  Returns words uppercased. Raises FileNotFoundError if path doesn't exist.
  """
  words = []
  with open(path, encoding='utf-8') as f:
    for line in f:
      word = line.split('#')[0].strip()
      if word:
        words.append(word.upper())
  return words
