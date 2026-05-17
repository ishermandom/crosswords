# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for clue_gen.word_parser."""

import io

import pytest

from clue_gen.word_parser import load_words, load_words_file


def _stream(text: str) -> io.StringIO:
  return io.StringIO(text)


def test_words_are_uppercased():
  result = load_words(_stream('alpha\nbravo\n'))
  assert result == ['ALPHA', 'BRAVO']


def test_blank_lines_are_skipped():
  result = load_words(_stream('\nalpha\n\nbravo\n'))
  assert result == ['ALPHA', 'BRAVO']


def test_full_line_comment_is_skipped():
  result = load_words(_stream('# comment\nalpha\n'))
  assert result == ['ALPHA']


def test_inline_comment_is_stripped():
  result = load_words(_stream('alpha # inline comment\n'))
  assert result == ['ALPHA']


def test_whitespace_around_word_is_stripped():
  result = load_words(_stream('  alpha  \n'))
  assert result == ['ALPHA']


def test_empty_stream_returns_empty_list():
  assert load_words(_stream('')) == []


def test_load_words_file_raises_for_missing_path():
  with pytest.raises(FileNotFoundError):
    load_words_file('/nonexistent/path/words.txt')
