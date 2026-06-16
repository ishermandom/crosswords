# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Tests for persistent bank state: append-only records and resume logic."""

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from bank_state import BankState

GOOD_CLUE: dict[str, object] = {
  'style': 'american',
  'difficulty': 'hard',
  'clue': 'Which way the north wind blows',
  'trap': 'NORTHWARD fits',
  'confidence': 'high',
}
OTHER_CLUE: dict[str, object] = {
  'style': 'american',
  'difficulty': 'medium',
  'clue': 'Down, to a cartographer?',
  'trap': "map orientation sense of 'down'",
  'confidence': 'medium',
}


@pytest.fixture
def state(tmp_path: Path) -> BankState:
  """A fresh BankState over an empty out/ directory."""
  return BankState(tmp_path / 'out')


def _record_attempt(
  state: BankState,
  word: str,
  attempt: int,
  clues: Sequence[Mapping[str, object]],
  skips: Sequence[Mapping[str, object]] = (),
) -> None:
  """Record a generation containing the given clues."""
  state.record_generation(
    batch=1,
    batch_size=3,
    attempt=attempt,
    word=word,
    word_object={'word': word, 'clues': list(clues), 'skips': list(skips)},
  )


def test_fresh_state_is_empty(state: BankState) -> None:
  assert state.completed_words() == set()
  assert state.retry_entries() == []
  assert state.pending_verifications() == []


def test_all_accepted_completes_word(state: BankState) -> None:
  _record_attempt(state, 'SOUTHWARD', 1, [GOOD_CLUE])
  state.record_verdict(
    batch=1,
    batch_size=3,
    attempt=1,
    word='SOUTHWARD',
    clue_text='Which way the north wind blows',
    style='american',
    verdict='accept',
    reason=None,
  )
  state.settle_word_attempt('SOUTHWARD', 1)

  assert 'SOUTHWARD' in state.completed_words()
  assert len(state.accepted_records) == 1
  assert state.retry_entries() == []


def test_revise_verdict_queues_one_retry(state: BankState) -> None:
  _record_attempt(state, 'SOUTHWARD', 1, [GOOD_CLUE])
  state.record_verdict(
    batch=1,
    batch_size=3,
    attempt=1,
    word='SOUTHWARD',
    clue_text='Which way the north wind blows',
    style='american',
    verdict='revise',
    reason='trap does not function',
  )
  state.settle_word_attempt('SOUTHWARD', 1)

  assert 'SOUTHWARD' not in state.completed_words()
  entries = state.retry_entries()
  assert len(entries) == 1
  assert entries[0].word == 'SOUTHWARD'
  assert any('trap does not function' in r for r in entries[0].reasons)


def test_second_failure_rejects_finally(state: BankState) -> None:
  _record_attempt(state, 'SOUTHWARD', 1, [GOOD_CLUE])
  state.record_verdict(
    batch=1,
    batch_size=3,
    attempt=1,
    word='SOUTHWARD',
    clue_text='Which way the north wind blows',
    style='american',
    verdict='revise',
    reason='trap does not function',
  )
  state.settle_word_attempt('SOUTHWARD', 1)

  _record_attempt(state, 'SOUTHWARD', 2, [OTHER_CLUE])
  state.record_verdict(
    batch=2,
    batch_size=3,
    attempt=2,
    word='SOUTHWARD',
    clue_text='Down, to a cartographer?',
    style='american',
    verdict='revise',
    reason='still no trap',
  )
  state.settle_word_attempt('SOUTHWARD', 2)

  assert 'SOUTHWARD' in state.completed_words()
  assert state.retry_entries() == []
  assert any(
    r['kind'] == 'retry-exhausted-revise' for r in state.rejected_records
  )


def test_judge_reject_is_final_without_retry(state: BankState) -> None:
  _record_attempt(state, 'SOUTHWARD', 1, [GOOD_CLUE])
  state.record_verdict(
    batch=1,
    batch_size=3,
    attempt=1,
    word='SOUTHWARD',
    clue_text='Which way the north wind blows',
    style='american',
    verdict='reject',
    reason='unsalvageable',
  )
  state.settle_word_attempt('SOUTHWARD', 1)

  assert 'SOUTHWARD' in state.completed_words()
  assert state.retry_entries() == []
  assert any(r['kind'] == 'judge-reject' for r in state.rejected_records)


def test_mechanical_failure_queues_retry(state: BankState) -> None:
  _record_attempt(state, 'SOUTHWARD', 1, [GOOD_CLUE])
  state.record_mechanical_failure(
    batch=1,
    batch_size=3,
    attempt=1,
    word='SOUTHWARD',
    clue=GOOD_CLUE,
    reasons=['clue text contains the answer'],
  )
  state.settle_word_attempt('SOUTHWARD', 1)

  entries = state.retry_entries()
  assert len(entries) == 1
  assert any('contains the answer' in r for r in entries[0].reasons)


def test_skip_is_recorded_final_and_does_not_retry(state: BankState) -> None:
  _record_attempt(
    state,
    'SOUTHWARD',
    1,
    [GOOD_CLUE],
    skips=[{'style': 'cryptic', 'reason': 'no fair wordplay'}],
  )
  state.record_verdict(
    batch=1,
    batch_size=3,
    attempt=1,
    word='SOUTHWARD',
    clue_text='Which way the north wind blows',
    style='american',
    verdict='accept',
    reason=None,
  )
  state.settle_word_attempt('SOUTHWARD', 1)

  assert 'SOUTHWARD' in state.completed_words()
  assert any(r['kind'] == 'skip' for r in state.rejected_records)


def test_unverdicted_generation_is_pending_verification(
  state: BankState,
) -> None:
  _record_attempt(state, 'SOUTHWARD', 1, [GOOD_CLUE])

  assert 'SOUTHWARD' not in state.completed_words()
  assert state.retry_entries() == []
  pending = state.pending_verifications()
  assert len(pending) == 1
  assert pending[0].word == 'SOUTHWARD'
  assert pending[0].surviving_clues == [GOOD_CLUE]


def test_duplicate_accepted_text_is_rejected(state: BankState) -> None:
  for word, attempt in (('ALPHA', 1), ('BETA', 1)):
    _record_attempt(state, word, attempt, [GOOD_CLUE])
    state.record_verdict(
      batch=1,
      batch_size=3,
      attempt=attempt,
      word=word,
      clue_text='Which way the north wind blows',
      style='american',
      verdict='accept',
      reason=None,
    )
    state.settle_word_attempt(word, attempt)

  assert len(state.accepted_records) == 1
  assert any(r['kind'] == 'duplicate' for r in state.rejected_records)


def test_reload_from_disk_is_idempotent(tmp_path: Path) -> None:
  out_dir = tmp_path / 'out'
  state = BankState(out_dir)
  _record_attempt(state, 'SOUTHWARD', 1, [GOOD_CLUE, OTHER_CLUE])
  state.record_verdict(
    batch=1,
    batch_size=3,
    attempt=1,
    word='SOUTHWARD',
    clue_text='Which way the north wind blows',
    style='american',
    verdict='accept',
    reason=None,
  )
  state.record_verdict(
    batch=1,
    batch_size=3,
    attempt=1,
    word='SOUTHWARD',
    clue_text='Down, to a cartographer?',
    style='american',
    verdict='reject',
    reason='no',
  )
  state.settle_word_attempt('SOUTHWARD', 1)

  reloaded = BankState(out_dir)
  assert reloaded.completed_words() == {'SOUTHWARD'}
  assert len(reloaded.accepted_records) == 1
  assert len(reloaded.rejected_records) == 1

  # Re-settling after reload must not append duplicate records.
  reloaded.settle_word_attempt('SOUTHWARD', 1)
  accepted_lines = (out_dir / 'accepted.jsonl').read_text().splitlines()
  assert len(accepted_lines) == 1


def test_crash_before_settle_is_backfilled_on_reload(tmp_path: Path) -> None:
  out_dir = tmp_path / 'out'
  state = BankState(out_dir)
  _record_attempt(state, 'SOUTHWARD', 1, [GOOD_CLUE])
  state.record_verdict(
    batch=1,
    batch_size=3,
    attempt=1,
    word='SOUTHWARD',
    clue_text='Which way the north wind blows',
    style='american',
    verdict='accept',
    reason=None,
  )
  # Crash here: settle_word_attempt never ran, accepted.jsonl is empty.

  reloaded = BankState(out_dir)
  assert reloaded.completed_words() == {'SOUTHWARD'}
  assert len(reloaded.accepted_records) == 1


def test_no_output_word_retries_then_rejects(state: BankState) -> None:
  state.record_generation(
    batch=1, batch_size=3, attempt=1, word='SOUTHWARD', word_object=None
  )
  state.record_mechanical_failure(
    batch=1,
    batch_size=3,
    attempt=1,
    word='SOUTHWARD',
    clue=None,
    reasons=['generator produced no output for this word'],
  )
  state.settle_word_attempt('SOUTHWARD', 1)

  assert len(state.retry_entries()) == 1

  state.record_generation(
    batch=2, batch_size=3, attempt=2, word='SOUTHWARD', word_object=None
  )
  state.record_mechanical_failure(
    batch=2,
    batch_size=3,
    attempt=2,
    word='SOUTHWARD',
    clue=None,
    reasons=['generator produced no output for this word'],
  )
  state.settle_word_attempt('SOUTHWARD', 2)

  assert 'SOUTHWARD' in state.completed_words()
  assert any(
    r['kind'] == 'retry-exhausted-mechanical' for r in state.rejected_records
  )


def test_next_batch_id_advances_across_reload(tmp_path: Path) -> None:
  out_dir = tmp_path / 'out'
  state = BankState(out_dir)
  assert state.next_batch_id() == 1
  _record_attempt(state, 'SOUTHWARD', 1, [GOOD_CLUE])
  assert BankState(out_dir).next_batch_id() == 2
