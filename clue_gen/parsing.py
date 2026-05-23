# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Utilities for parsing raw LLM output text."""

import re

_FENCE_RE = re.compile(
  r"""
  ```        # opening fence
  [a-z]*     # optional language tag (e.g. "json", "python"); greedy — if
             # the tag is absent and content starts with lowercase letters,
             # those letters are consumed here. Safe for JSON (starts with {)
  \n?        # optional newline after the language tag
  (.*?)      # fence content (captured)
  \n?        # optional newline before the closing fence
  ```        # closing fence
  """,
  re.DOTALL | re.VERBOSE,
)


def strip_markdown_fences(text: str) -> str:
  """Return text with any leading/trailing markdown code fences removed.

  If the text contains a fenced block, returns the content inside the fences.
  Otherwise returns the text stripped of leading and trailing whitespace.
  """
  stripped = text.strip()
  fence_match = _FENCE_RE.search(stripped)
  if fence_match:
    return fence_match.group(1).strip()
  return stripped
