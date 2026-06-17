# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Persistent pipeline state over append-only JSONL files in out/.

Every event (generation, mechanical failure, verdict, acceptance,
rejection) is one appended line, so a run interrupted at any point can be
resumed by re-deriving state from the files. The derivation rules:

- A word is COMPLETED when its second attempt is fully verdicted, or its
  first attempt is fully verdicted with no retryable failures.
- A word AWAITS RETRY when attempt 1 is fully verdicted, produced
  retryable failures (mechanical or "revise"), and attempt 2 has not run.
- A word is PENDING VERIFICATION when a generation was recorded but some
  surviving clue has no verdict yet (a crash between the two LLM calls);
  resuming re-runs only the verify step for those clues.

settle_word_attempt() converts verdicts into accepted/rejected records.
It is idempotent — re-settling after a reload appends nothing new — which
lets startup backfill records lost to a crash mid-settle.
"""

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import NotRequired, TypedDict

from cluegen.cloud.mechanical_checks import (
  clue_style_of,
  clue_text_of,
  maybe_clue_text,
  normalize_clue_text,
  stem_soft_flags,
)

# Verdicts the judge may return; "revise" is the only retryable one.
VERDICT_ACCEPT = 'accept'
VERDICT_REVISE = 'revise'
VERDICT_REJECT = 'reject'

CLUE_TEXT_EXCERPT_LENGTH = 60


class _BatchedRecord(TypedDict):
  """Batch bookkeeping fields shared by every record type."""

  batch: int
  batch_size: int


class GenerationRecord(_BatchedRecord):
  """One word's generation output, or (word=None) unparsed output."""

  attempt: int
  word: str | None
  object: dict[str, object] | None
  unparsed: NotRequired[list[str]]
  ts: str


class MechanicalFailureRecord(_BatchedRecord):
  """One clue (or whole-word) mechanical-check failure."""

  attempt: int
  word: str
  clue: dict[str, object] | None
  reasons: list[str]
  ts: str


class VerdictRecord(_BatchedRecord):
  """One judge verdict for one clue."""

  attempt: int
  word: str
  clue: str
  style: str | None
  verdict: str
  reason: str | None
  synthetic: bool
  ts: str


class AcceptedRecord(_BatchedRecord):
  """One clue admitted to the bank."""

  attempt: int
  word: str
  clue: dict[str, object]
  soft_flags: list[str]
  ts: str


class RejectedRecord(_BatchedRecord):
  """One finally rejected clue, per-style skip, or failed word."""

  attempt: int
  word: str
  kind: str
  style: str | None
  clue: dict[str, object] | None
  reasons: list[str]
  ts: str


@dataclass(frozen=True)
class RetryEntry:
  """A word due for its second (final) generation attempt."""

  word: str
  reasons: tuple[str, ...]


@dataclass(frozen=True)
class PendingVerification:
  """Surviving clues from a recorded generation that lack verdicts."""

  word: str
  attempt: int
  batch: int
  batch_size: int
  surviving_clues: list[Mapping[str, object]]


def _timestamp() -> str:
  """Current UTC time for record stamping."""
  return datetime.now(UTC).isoformat(timespec='seconds')


def _excerpt(clue: Mapping[str, object] | None) -> str:
  """A short identifying snippet of a clue's text for retry prompts."""
  text = maybe_clue_text(clue)
  if not text:
    return '(no clue text)'
  return text[:CLUE_TEXT_EXCERPT_LENGTH]


class BankState:
  """In-memory view of the bank, backed by append-only JSONL files."""

  def __init__(self, out_dir: Path) -> None:
    """Load (or initialize) state from the given output directory."""
    self.out_dir = out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    self.generation_records: list[GenerationRecord] = []
    self.mechanical_failure_records: list[MechanicalFailureRecord] = []
    self.verdict_records: list[VerdictRecord] = []
    self.accepted_records: list[AcceptedRecord] = []
    self.rejected_records: list[RejectedRecord] = []

    # Indexes over the record lists, keyed by (word, attempt).
    self._generations: dict[tuple[str, int], GenerationRecord] = {}
    self._mechanical_failures: dict[
      tuple[str, int], list[MechanicalFailureRecord]
    ] = {}
    self._verdicts: dict[tuple[str, int], dict[str, VerdictRecord]] = {}
    self._accepted_texts: set[str] = set()
    self._accepted_keys: set[tuple[str, str]] = set()
    self._rejected_keys: set[tuple[str | None, ...]] = set()
    self._max_batch = 0

    self._load()

  # --- File plumbing ---

  def _path(self, name: str) -> Path:
    """Path of one of the JSONL state files."""
    return self.out_dir / name

  def _append(self, name: str, record: Mapping[str, object]) -> None:
    """Append one record to a state file."""
    with open(self._path(name), 'a') as handle:
      handle.write(json.dumps(record) + '\n')

  def _lines(self, name: str) -> Iterator[str]:
    """Yield non-blank lines from a state file, if it exists."""
    path = self._path(name)
    if not path.exists():
      return
    with open(path) as handle:
      for line in handle:
        if line.strip():
          yield line

  def _load(self) -> None:
    """Rebuild all indexes from disk, then backfill missing settles."""
    for line in self._lines('raw_generations.jsonl'):
      self._index_generation(json.loads(line))
    for line in self._lines('mech_failures.jsonl'):
      self._index_mechanical_failure(json.loads(line))
    for line in self._lines('verdicts.jsonl'):
      self._index_verdict(json.loads(line))
    for line in self._lines('accepted.jsonl'):
      self._index_accepted(json.loads(line))
    for line in self._lines('rejected.jsonl'):
      self._index_rejected(json.loads(line))

    # A crash between recording verdicts and settling leaves fully
    # verdicted attempts with missing accepted/rejected records;
    # settling is idempotent, so unconditionally re-settle.
    for word, attempt in list(self._generations):
      if self.is_fully_verdicted(word, attempt):
        self.settle_word_attempt(word, attempt)

  # --- Indexing (shared between load and record_*) ---

  def _note_batch(self, record: _BatchedRecord) -> None:
    """Track the highest batch id seen, for next_batch_id()."""
    self._max_batch = max(self._max_batch, record['batch'])

  def _index_generation(self, record: GenerationRecord) -> None:
    self.generation_records.append(record)
    self._note_batch(record)
    word = record['word']
    if word is not None:
      self._generations[(word, record['attempt'])] = record

  def _index_mechanical_failure(self, record: MechanicalFailureRecord) -> None:
    self.mechanical_failure_records.append(record)
    self._note_batch(record)
    key = (record['word'], record['attempt'])
    self._mechanical_failures.setdefault(key, []).append(record)

  def _index_verdict(self, record: VerdictRecord) -> None:
    self.verdict_records.append(record)
    self._note_batch(record)
    key = (record['word'], record['attempt'])
    normalized = normalize_clue_text(record['clue'])
    self._verdicts.setdefault(key, {})[normalized] = record

  def _index_accepted(self, record: AcceptedRecord) -> None:
    self.accepted_records.append(record)
    self._note_batch(record)
    normalized = normalize_clue_text(clue_text_of(record['clue']))
    self._accepted_texts.add(normalized)
    self._accepted_keys.add((record['word'], normalized))

  def _index_rejected(self, record: RejectedRecord) -> None:
    self.rejected_records.append(record)
    self._note_batch(record)
    self._rejected_keys.add(self._rejected_key(record))

  @staticmethod
  def _rejected_key(record: RejectedRecord) -> tuple[str | None, ...]:
    """Identity of a rejection, for idempotent appends.

    Skips dedupe per (word, style) regardless of reason, so a repeat
    skip on the retry attempt does not append a second record.
    """
    if record['kind'] == 'skip':
      identity = ''
    else:
      text = maybe_clue_text(record['clue'])
      identity = (
        normalize_clue_text(text) if text else ' | '.join(record['reasons'])
      )
    return (record['word'], record['kind'], record['style'], identity)

  # --- Recording ---

  def record_generation(
    self,
    *,
    batch: int,
    batch_size: int,
    attempt: int,
    word: str | None,
    word_object: Mapping[str, object] | None,
  ) -> None:
    """Record one word's generation output (None if the generator
    produced nothing for it)."""
    record: GenerationRecord = {
      'batch': batch,
      'batch_size': batch_size,
      'attempt': attempt,
      'word': word,
      'object': dict(word_object) if word_object is not None else None,
      'ts': _timestamp(),
    }
    self._append('raw_generations.jsonl', record)
    self._index_generation(record)

  def record_unparsed_output(self, *, batch: int, lines: Sequence[str]) -> None:
    """Record generator output lines that did not parse as word JSON."""
    record: GenerationRecord = {
      'batch': batch,
      'batch_size': 0,
      'attempt': 0,
      'word': None,
      'object': None,
      'unparsed': list(lines),
      'ts': _timestamp(),
    }
    self._append('raw_generations.jsonl', record)
    self._index_generation(record)

  def record_mechanical_failure(
    self,
    *,
    batch: int,
    batch_size: int,
    attempt: int,
    word: str,
    clue: Mapping[str, object] | None,
    reasons: Sequence[str],
  ) -> None:
    """Record one clue (or whole-word) mechanical-check failure."""
    record: MechanicalFailureRecord = {
      'batch': batch,
      'batch_size': batch_size,
      'attempt': attempt,
      'word': word,
      'clue': dict(clue) if clue is not None else None,
      'reasons': list(reasons),
      'ts': _timestamp(),
    }
    self._append('mech_failures.jsonl', record)
    self._index_mechanical_failure(record)

  def record_verdict(
    self,
    *,
    batch: int,
    batch_size: int,
    attempt: int,
    word: str,
    clue_text: str,
    style: str | None,
    verdict: str,
    reason: str | None,
    synthetic: bool = False,
  ) -> None:
    """Record one judge verdict (synthetic=True for verdicts the
    pipeline fabricates when the judge returned none for a clue)."""
    record: VerdictRecord = {
      'batch': batch,
      'batch_size': batch_size,
      'attempt': attempt,
      'word': word,
      'clue': clue_text,
      'style': style,
      'verdict': verdict,
      'reason': reason,
      'synthetic': synthetic,
      'ts': _timestamp(),
    }
    self._append('verdicts.jsonl', record)
    self._index_verdict(record)

  def _record_accepted(
    self,
    *,
    word: str,
    attempt: int,
    batch: int,
    batch_size: int,
    clue: Mapping[str, object],
  ) -> None:
    """Append an accepted clue, with recomputed soft-flag annotations."""
    record: AcceptedRecord = {
      'word': word,
      'attempt': attempt,
      'batch': batch,
      'batch_size': batch_size,
      'clue': dict(clue),
      'soft_flags': stem_soft_flags(word, clue_text_of(clue)),
      'ts': _timestamp(),
    }
    self._append('accepted.jsonl', record)
    self._index_accepted(record)

  def _record_rejected(
    self,
    *,
    word: str,
    attempt: int,
    batch: int,
    batch_size: int,
    kind: str,
    style: str | None,
    clue: Mapping[str, object] | None,
    reasons: Sequence[str],
  ) -> None:
    """Append a final rejection, if an identical one is not on file."""
    record: RejectedRecord = {
      'word': word,
      'attempt': attempt,
      'batch': batch,
      'batch_size': batch_size,
      'kind': kind,
      'style': style,
      'clue': dict(clue) if clue is not None else None,
      'reasons': list(reasons),
      'ts': _timestamp(),
    }
    if self._rejected_key(record) in self._rejected_keys:
      return
    self._append('rejected.jsonl', record)
    self._index_rejected(record)

  # --- Derived views ---

  @property
  def accepted_texts(self) -> set[str]:
    """Normalized texts of every accepted clue, for uniqueness checks."""
    return self._accepted_texts

  def next_batch_id(self) -> int:
    """The id the next batch should use (monotonic across runs)."""
    return self._max_batch + 1

  def touched_words(self) -> set[str]:
    """Words that have at least one generation attempt recorded."""
    return {word for word, _ in self._generations}

  def survivors(self, word: str, attempt: int) -> list[Mapping[str, object]]:
    """Clues from this attempt's output that passed mechanical checks.

    Derived as the recorded object's clues minus recorded mechanical
    failures (matched by normalized clue text); clues without usable
    text always mechanically fail, so they are excluded directly.
    """
    record = self._generations.get((word, attempt))
    if record is None:
      return []
    word_object = record['object']
    if not isinstance(word_object, Mapping):
      return []
    clues = word_object.get('clues')
    if not isinstance(clues, list):
      return []

    failed_texts: set[str] = set()
    for failure in self._mechanical_failures.get((word, attempt), []):
      failed_text = maybe_clue_text(failure['clue'])
      if failed_text is not None:
        failed_texts.add(normalize_clue_text(failed_text))

    surviving: list[Mapping[str, object]] = []
    for clue in clues:
      if not isinstance(clue, Mapping):
        continue
      text = maybe_clue_text(clue)
      if text is None or normalize_clue_text(text) in failed_texts:
        continue
      surviving.append(clue)
    return surviving

  def is_fully_verdicted(self, word: str, attempt: int) -> bool:
    """Whether every mechanically surviving clue has a verdict."""
    verdicts = self._verdicts.get((word, attempt), {})
    return all(
      normalize_clue_text(clue_text_of(clue)) in verdicts
      for clue in self.survivors(word, attempt)
    )

  def _retryable_reasons(self, word: str, attempt: int) -> list[str]:
    """Failure descriptions that qualify the word for a retry."""
    reasons: list[str] = []
    for failure in self._mechanical_failures.get((word, attempt), []):
      failure_clue = failure['clue']
      style = clue_style_of(failure_clue) or 'word'
      for reason in failure['reasons']:
        reasons.append(f'[{style}] "{_excerpt(failure_clue)}" — {reason}')
    for verdict in self._verdicts.get((word, attempt), {}).values():
      if verdict['verdict'] == VERDICT_REVISE:
        reasons.append(
          f'[{verdict["style"] or "?"}]'
          f' "{verdict["clue"][:CLUE_TEXT_EXCERPT_LENGTH]}"'
          f' — judge: {verdict["reason"] or "revise"}'
        )
    return reasons

  def completed_words(self) -> set[str]:
    """Words needing no further work (skip on resume)."""
    completed: set[str] = set()
    for word in self.touched_words():
      if (word, 2) in self._generations:
        if self.is_fully_verdicted(word, 2):
          completed.add(word)
      elif (
        (word, 1) in self._generations
        and self.is_fully_verdicted(word, 1)
        and not self._retryable_reasons(word, 1)
      ):
        completed.add(word)
    return completed

  def retry_entries(self) -> list[RetryEntry]:
    """Words whose first attempt failed retryably, awaiting attempt 2."""
    entries: list[RetryEntry] = []
    for word, attempt in self._generations:
      if attempt != 1 or (word, 2) in self._generations:
        continue
      if not self.is_fully_verdicted(word, 1):
        continue
      reasons = self._retryable_reasons(word, 1)
      if reasons:
        entries.append(RetryEntry(word, tuple(reasons)))
    return entries

  def pending_verifications(self) -> list[PendingVerification]:
    """Generation attempts interrupted before their verify call."""
    pending: list[PendingVerification] = []
    for (word, attempt), record in self._generations.items():
      if self.is_fully_verdicted(word, attempt):
        continue
      pending.append(
        PendingVerification(
          word=word,
          attempt=attempt,
          batch=record['batch'],
          batch_size=record['batch_size'],
          surviving_clues=self.survivors(word, attempt),
        )
      )
    return pending

  # --- Settlement ---

  def settle_word_attempt(self, word: str, attempt: int) -> None:
    """Convert this attempt's verdicts into accepted/rejected records.

    Idempotent: existing records are recognized and never duplicated.
    Retryable failures on attempt 1 are left unsettled — they become
    retry_entries() — and turn into final rejections on attempt 2.
    """
    record = self._generations.get((word, attempt))
    if record is None:
      raise ValueError(
        f'cannot settle {word} attempt {attempt}: no generation recorded'
      )
    batch, batch_size = record['batch'], record['batch_size']

    word_object = record['object']
    if isinstance(word_object, Mapping):
      skips = word_object.get('skips')
      for skip in skips if isinstance(skips, list) else []:
        if isinstance(skip, Mapping):
          self._record_rejected(
            word=word,
            attempt=attempt,
            batch=batch,
            batch_size=batch_size,
            kind='skip',
            style=clue_style_of(skip),
            clue=None,
            reasons=[str(skip.get('reason'))],
          )

    verdicts = self._verdicts.get((word, attempt), {})
    for clue in self.survivors(word, attempt):
      normalized = normalize_clue_text(clue_text_of(clue))
      verdict = verdicts.get(normalized)
      if verdict is None:
        continue  # Pending verification; settled later.
      if verdict['verdict'] == VERDICT_ACCEPT:
        self._settle_acceptance(
          word, attempt, batch, batch_size, clue, normalized
        )
      elif verdict['verdict'] == VERDICT_REJECT:
        self._record_rejected(
          word=word,
          attempt=attempt,
          batch=batch,
          batch_size=batch_size,
          kind='judge-reject',
          style=clue_style_of(clue),
          clue=clue,
          reasons=[verdict['reason'] or 'rejected by judge'],
        )
      elif verdict['verdict'] == VERDICT_REVISE and attempt >= 2:
        self._record_rejected(
          word=word,
          attempt=attempt,
          batch=batch,
          batch_size=batch_size,
          kind='retry-exhausted-revise',
          style=clue_style_of(clue),
          clue=clue,
          reasons=[verdict['reason'] or 'revise'],
        )

    if attempt >= 2:
      for failure in self._mechanical_failures.get((word, attempt), []):
        self._record_rejected(
          word=word,
          attempt=attempt,
          batch=batch,
          batch_size=batch_size,
          kind='retry-exhausted-mechanical',
          style=clue_style_of(failure['clue']),
          clue=failure['clue'],
          reasons=failure['reasons'],
        )

  def _settle_acceptance(
    self,
    word: str,
    attempt: int,
    batch: int,
    batch_size: int,
    clue: Mapping[str, object],
    normalized: str,
  ) -> None:
    """Accept a clue, unless its text already exists in the bank."""
    if (word, normalized) in self._accepted_keys:
      return
    if normalized in self._accepted_texts:
      self._record_rejected(
        word=word,
        attempt=attempt,
        batch=batch,
        batch_size=batch_size,
        kind='duplicate',
        style=clue_style_of(clue),
        clue=clue,
        reasons=['accepted clue text already in bank'],
      )
      return
    self._record_accepted(
      word=word, attempt=attempt, batch=batch, batch_size=batch_size, clue=clue
    )
