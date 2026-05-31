# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for clue_gen.input_parsing."""

import io

from clue_gen.input_parsing import ClueEntry, load_clue_entries, load_words


def _stream(text: str) -> io.StringIO:
  return io.StringIO(text)


# --- load_words ---


def test_words_are_uppercased() -> None:
  result = load_words(_stream('alpha\nbravo\n'))
  assert result == ['ALPHA', 'BRAVO']


def test_blank_lines_are_skipped() -> None:
  result = load_words(_stream('\nalpha\n\nbravo\n'))
  assert result == ['ALPHA', 'BRAVO']


def test_full_line_comment_is_skipped() -> None:
  result = load_words(_stream('# comment\nalpha\n'))
  assert result == ['ALPHA']


def test_inline_comment_is_stripped() -> None:
  result = load_words(_stream('alpha # inline comment\n'))
  assert result == ['ALPHA']


def test_whitespace_around_word_is_stripped() -> None:
  result = load_words(_stream('  alpha  \n'))
  assert result == ['ALPHA']


def test_empty_stream_returns_empty_list() -> None:
  assert load_words(_stream('')) == []


# --- load_clue_entries ---


def test_clue_entry_answer_is_uppercased() -> None:
  result = load_clue_entries(_stream('match Starts a fire?\n'))
  assert result == [ClueEntry(answer='MATCH', clue_text='Starts a fire?')]


def test_clue_entry_preserves_multi_word_clue_text() -> None:
  result = load_clue_entries(_stream('MATCH Starts a fire?\n'))
  assert result[0].clue_text == 'Starts a fire?'


def test_clue_entries_skips_blank_lines() -> None:
  result = load_clue_entries(_stream('\nMATCH Starts a fire?\n\n'))
  assert len(result) == 1


def test_clue_entries_skips_full_line_comments() -> None:
  result = load_clue_entries(_stream('# comment\nMATCH Starts a fire?\n'))
  assert len(result) == 1


def test_clue_entries_strips_inline_comments() -> None:
  result = load_clue_entries(_stream('MATCH Starts a fire? # inline\n'))
  assert result[0].clue_text == 'Starts a fire?'


def test_clue_entries_empty_stream_returns_empty_list() -> None:
  assert load_clue_entries(_stream('')) == []
