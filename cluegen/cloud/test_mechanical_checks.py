# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Tests for the pure-code mechanical clue checks."""

from collections.abc import Set

from cluegen.cloud import mechanical_checks


def _make_american(**overrides: object) -> dict[str, object]:
  """An American clue for SOUTHWARD that passes every check."""
  clue: dict[str, object] = {
    'style': 'american',
    'difficulty': 'hard',
    'clue': 'Which way the north wind blows',
    'trap': 'NORTHWARD fits; wind-naming convention is the escape',
    'confidence': 'high',
  }
  clue.update(overrides)
  return clue


def _make_cryptic(**overrides: object) -> dict[str, object]:
  """A cryptic anagram clue for SOUTHWARD that passes every check."""
  clue: dict[str, object] = {
    'style': 'cryptic',
    'difficulty': 'medium',
    'clue': 'Spilled Tudor wash going down, on most maps (9)',
    'definition': 'going down, on most maps',
    'mechanism': 'anagram',
    'anagram_fodder': 'Tudor wash',
    'hidden_string': None,
    'parse': "anagram of TUDOR WASH, indicator 'spilled'; def at end",
    'confidence': 'high',
  }
  clue.update(overrides)
  return clue


def check(
  answer: str, clue: object, accepted: Set[str] = frozenset()
) -> mechanical_checks.CheckedClue:
  """Shorthand for check_clue."""
  return mechanical_checks.check_clue(answer, clue, accepted)


# --- Enumeration helpers ---


def test_expected_enumeration_single_word() -> None:
  assert mechanical_checks.expected_enumeration('SOUTHWARD') == '(9)'


def test_expected_enumeration_multiword_and_hyphen() -> None:
  assert mechanical_checks.expected_enumeration('ESCAPE ROOM') == '(6,4)'
  assert mechanical_checks.expected_enumeration('MERRY-GO-ROUND') == '(5-2-5)'


# --- Schema checks ---


def test_clean_american_passes() -> None:
  result = check('SOUTHWARD', _make_american())
  assert result.failures == []
  assert result.soft_flags == []


def test_clean_cryptic_passes() -> None:
  assert check('SOUTHWARD', _make_cryptic()).failures == []


def test_invalid_style_fails() -> None:
  assert check('SOUTHWARD', _make_american(style='quick')).failures


def test_invalid_difficulty_fails() -> None:
  assert check('SOUTHWARD', _make_american(difficulty='fiendish')).failures


def test_missing_confidence_fails() -> None:
  clue = _make_american()
  del clue['confidence']
  assert check('SOUTHWARD', clue).failures


def test_non_object_clue_fails() -> None:
  assert check('SOUTHWARD', 'not a dict').failures


def test_american_hard_requires_trap() -> None:
  assert check('SOUTHWARD', _make_american(trap=None)).failures


def test_american_easy_allows_null_trap() -> None:
  clue = _make_american(
    difficulty='easy',
    clue="Like a snowbird's November flight",
    trap=None,
  )
  assert check('SOUTHWARD', clue).failures == []


def test_cryptic_requires_parse_fields() -> None:
  for field in ('definition', 'mechanism', 'parse'):
    clue = _make_cryptic(**{field: None})
    assert check('SOUTHWARD', clue).failures, field


# --- Cryptic letter math ---


def test_enumeration_mismatch_fails() -> None:
  clue = _make_cryptic(clue='Spilled Tudor wash going down (8)')
  assert any('enumeration' in f for f in check('SOUTHWARD', clue).failures)


def test_missing_enumeration_fails() -> None:
  clue = _make_cryptic(clue='Spilled Tudor wash going down')
  assert any('enumeration' in f for f in check('SOUTHWARD', clue).failures)


def test_anagram_fodder_multiset_mismatch_fails() -> None:
  clue = _make_cryptic(
    clue='Spilled Tudor wish going down, on most maps (9)',
    anagram_fodder='Tudor wish',
  )
  assert any('fodder' in f for f in check('SOUTHWARD', clue).failures)


def test_anagram_fodder_absent_from_clue_fails() -> None:
  # "draw shout" is a correct multiset but does not appear in the clue.
  clue = _make_cryptic(anagram_fodder='draw shout')
  assert any('fodder' in f for f in check('SOUTHWARD', clue).failures)


def test_anagram_mechanism_requires_fodder() -> None:
  clue = _make_cryptic(anagram_fodder=None)
  assert check('SOUTHWARD', clue).failures


def test_compound_anagram_accepts_partial_fodder() -> None:
  # TIFF* + Y: the fodder anagrams to FIFT, the charade supplies the Y.
  clue = _make_cryptic(
    clue='Wild tiff, then unknown — the bull, in darts (5)',
    definition='the bull, in darts',
    mechanism='anagram+charade',
    anagram_fodder='tiff',
    parse="anagram of TIFF ('wild') + Y ('unknown') = FIFT + Y",
  )
  assert check('FIFTY', clue).failures == []


def test_compound_anagram_fodder_outside_answer_letters_fails() -> None:
  # 'taffy' brings an A that FIFTY has no use for.
  clue = _make_cryptic(
    clue='Wild taffy, then unknown — the bull, in darts (5)',
    mechanism='anagram+charade',
    anagram_fodder='taffy',
  )
  assert any('fodder' in f for f in check('FIFTY', clue).failures)


def test_compound_anagram_fodder_covering_whole_answer_fails() -> None:
  # The fodder alone spells the answer, leaving the charade nothing to add.
  clue = _make_cryptic(
    clue='Spilled draws thou going down, on most maps (9)',
    mechanism='anagram+charade',
    anagram_fodder='draws thou',
  )
  assert any('fodder' in f for f in check('SOUTHWARD', clue).failures)


def test_compound_anagram_fodder_absent_from_clue_fails() -> None:
  clue = _make_cryptic(
    clue='Wild row, then unknown — the bull, in darts (5)',
    mechanism='anagram+charade',
    anagram_fodder='tiff',
  )
  assert any('fodder' in f for f in check('FIFTY', clue).failures)


def test_pure_anagram_rejects_partial_fodder() -> None:
  # A lone anagram must account for every letter; 'tiff' leaves the Y short.
  clue = _make_cryptic(
    clue='Wild tiff — the bull, in darts (5)',
    mechanism='anagram',
    anagram_fodder='tiff',
  )
  assert any('fodder' in f for f in check('FIFTY', clue).failures)


def test_hidden_clue_passes() -> None:
  clue = _make_cryptic(
    clue='Cut some becalmed items (4)',
    definition='cut',
    mechanism='hidden',
    anagram_fodder=None,
    hidden_string='becalmed items',
    parse="hidden in 'becalmED ITems', indicator 'some'",
  )
  assert check('EDIT', clue).failures == []


def test_hidden_string_missing_answer_fails() -> None:
  clue = _make_cryptic(
    clue='Cut some becalmed gems (4)',
    mechanism='hidden',
    anagram_fodder=None,
    hidden_string='becalmed gems',
  )
  assert any('hidden' in f for f in check('EDIT', clue).failures)


def test_hidden_string_absent_from_clue_fails() -> None:
  clue = _make_cryptic(
    clue='Cut some becalmed items (4)',
    mechanism='hidden',
    anagram_fodder=None,
    hidden_string='becalm editor',
  )
  assert any('hidden' in f for f in check('EDIT', clue).failures)


def test_compound_hidden_skips_containment_check() -> None:
  # Hidden yields EDIT, the charade appends OR; the hidden string need not
  # contain the whole answer, and code can't isolate the hidden part.
  clue = _make_cryptic(
    clue='Some becalmed items take gold — boss (6)',
    definition='boss',
    mechanism='hidden+charade',
    anagram_fodder=None,
    hidden_string='becalmed items',
    parse="EDIT hidden in 'becalmED ITems' + OR ('gold')",
  )
  assert check('EDITOR', clue).failures == []


def test_compound_hidden_string_absent_from_clue_fails() -> None:
  clue = _make_cryptic(
    clue='Some quiet rooms take gold — boss (6)',
    mechanism='hidden+charade',
    anagram_fodder=None,
    hidden_string='becalmed items',
  )
  assert any('hidden' in f for f in check('EDITOR', clue).failures)


# --- Answer leakage ---


def test_answer_word_in_clue_hard_fails() -> None:
  clue = _make_american(clue='A southward push')
  assert any('answer' in f for f in check('SOUTHWARD', clue).failures)


def test_inflection_in_clue_hard_fails() -> None:
  clue = _make_american(
    clue='Pushes to the rear', difficulty='medium', trap='some ambiguity'
  )
  assert any('answer' in f for f in check('PUSH', clue).failures)


def test_e_drop_ing_inflection_hard_fails() -> None:
  clue = _make_american(
    clue='Scoring play', difficulty='medium', trap='some ambiguity'
  )
  assert any('answer' in f for f in check('SCORE', clue).failures)


def test_answer_inside_longer_word_is_not_a_leak() -> None:
  clue = _make_american(
    clue='Money talks', difficulty='medium', trap='some ambiguity'
  )
  assert check('ONE', clue).failures == []


def test_stem_soft_flag() -> None:
  clue = _make_american(
    clue='Southerly heading, say', difficulty='medium', trap='some ambiguity'
  )
  result = check('SOUTHWARD', clue)
  assert result.failures == []
  assert any('south' in flag for flag in result.soft_flags)


def test_short_stem_not_flagged() -> None:
  clue = _make_american(
    clue='One for the money', difficulty='medium', trap='some ambiguity'
  )
  assert check('ONES', clue).soft_flags == []


# --- Uniqueness ---


def test_duplicate_clue_text_fails() -> None:
  duplicate = mechanical_checks.normalize_clue_text(
    'Which way  the NORTH wind blows'
  )
  result = check('SOUTHWARD', _make_american(), accepted={duplicate})
  assert any('duplicate' in f for f in result.failures)


# --- Whole-word output ---


def test_check_word_output_partitions_clues_and_skips() -> None:
  word_object = {
    'word': 'SOUTHWARD',
    'enumeration': '(9)',
    'clues': [_make_american(), _make_american(clue='A southward push')],
    'skips': [{'style': 'cryptic', 'reason': 'no fair wordplay'}],
  }
  result = mechanical_checks.check_word_output(
    'SOUTHWARD', word_object, frozenset()
  )
  assert len(result.checked_clues) == 2
  assert len(result.survivors) == 1
  assert result.skips == [{'style': 'cryptic', 'reason': 'no fair wordplay'}]


def test_check_word_output_rejects_malformed_clues_list() -> None:
  result = mechanical_checks.check_word_output(
    'SOUTHWARD', {'word': 'SOUTHWARD', 'clues': 'oops'}, frozenset()
  )
  assert result.word_failures
  assert result.survivors == []
