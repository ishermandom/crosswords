# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Pure-code validation of generated clues, run between the two LLM calls.

These checks catch everything a script can verify without judgment: schema
shape, cryptic letter math, answer leakage, and bank-wide uniqueness.
Failures here skip the LLM verify step entirely, so they cost no tokens.
"""

import re
from collections.abc import Mapping, Set
from dataclasses import dataclass, field
from enum import StrEnum


class Style(StrEnum):
  """The two clue styles the bank accepts."""

  AMERICAN = 'american'
  CRYPTIC = 'cryptic'


class Difficulty(StrEnum):
  """Solver-effort tags defined by the spec's difficulty dial."""

  EASY = 'easy'
  MEDIUM = 'medium'
  HARD = 'hard'


class Confidence(StrEnum):
  """Generator's self-reported confidence in a clue."""

  HIGH = 'high'
  MEDIUM = 'medium'
  LOW = 'low'


# Suffixes stripped from the answer to find stems for soft-flag leakage
# detection ("south" inside a SOUTHWARD clue). Longest-first so that e.g.
# "wards" wins over "s".
STEM_SUFFIXES: tuple[str, ...] = (
  'wards',
  'ward',
  'ness',
  'ment',
  'tion',
  'sion',
  'able',
  'ible',
  'less',
  'ful',
  'ish',
  'ous',
  'ity',
  'ing',
  'est',
  'ed',
  'es',
  'er',
  'ly',
  'al',
  's',
  'y',
)

# Stems shorter than this produce too many false positives to flag.
MINIMUM_STEM_LENGTH = 4


def letters_only(text: str) -> str:
  """Lowercase the text and drop everything but letters."""
  return ''.join(c for c in text.lower() if c.isalpha())


def normalize_clue_text(text: str) -> str:
  """Canonical form for uniqueness comparison: casefold, tidy whitespace."""
  return ' '.join(text.split()).casefold()


def maybe_clue_text(clue: Mapping[str, object] | None) -> str | None:
  """The clue's text, when present and a string."""
  if clue is None:
    return None
  text = clue.get('clue')
  return text if isinstance(text, str) else None


def clue_text_of(clue: Mapping[str, object]) -> str:
  """The clue's text; raises on clues that never passed schema checks."""
  text = maybe_clue_text(clue)
  if text is None:
    raise ValueError(f'clue object has no text: {clue!r}')
  return text


def clue_style_of(clue: Mapping[str, object] | None) -> str | None:
  """The clue's style tag, when present and a string."""
  if clue is None:
    return None
  style = clue.get('style')
  return style if isinstance(style, str) else None


def expected_enumeration(answer: str) -> str:
  """The enumeration a cryptic clue for this answer must carry.

  Spaces separate counts with commas, hyphens with hyphens:
  "ESCAPE ROOM" -> "(6,4)", "MERRY-GO-ROUND" -> "(5-2-5)".
  """
  word_parts = [
    '-'.join(str(len(piece)) for piece in word.split('-'))
    for word in answer.split()
  ]
  return f'({",".join(word_parts)})'


def clue_enumeration(clue_text: str) -> str | None:
  """The trailing enumeration in a clue's text, or None if absent."""
  match = re.search(r'\(([0-9,\- ]+)\)\s*$', clue_text)
  if match is None:
    return None
  return f'({match.group(1).replace(" ", "")})'


def answer_leak_variants(answer: str) -> tuple[str, ...]:
  """The answer and its trivial inflections, for hard-fail leak detection."""
  base = answer.lower()
  variants = [base, base + 's', base + 'es', base + 'ed', base + 'ing']
  if base.endswith('e'):
    variants.append(base[:-1] + 'ing')
  return tuple(variants)


def has_answer_leak(answer: str, clue_text: str) -> bool:
  """Whether the clue text contains the answer or a trivial inflection.

  Matches whole words only, so ONE inside "money" is not a leak.
  """
  lowered = clue_text.lower()
  return any(
    re.search(rf'\b{re.escape(variant)}\b', lowered)
    for variant in answer_leak_variants(answer)
  )


def stem_soft_flags(answer: str, clue_text: str) -> list[str]:
  """Soft-flag annotations for answer stems appearing in the clue.

  A stem is the answer with one common suffix stripped, kept only when
  >= MINIMUM_STEM_LENGTH letters. Stems match as substrings — "south"
  inside "southerly" counts — because the point is to alert the judge,
  not to auto-reject.
  """
  base = answer.lower()
  lowered_clue = clue_text.lower()
  flags = []
  seen_stems = set()
  for suffix in STEM_SUFFIXES:
    if not base.endswith(suffix):
      continue
    stem = base[: -len(suffix)]
    if len(stem) < MINIMUM_STEM_LENGTH or stem in seen_stems:
      continue
    seen_stems.add(stem)
    if stem in lowered_clue:
      flags.append(f"clue contains stem '{stem}' of the answer")
  return flags


@dataclass
class CheckedClue:
  """One clue's mechanical-check outcome."""

  clue: Mapping[str, object]
  failures: list[str]
  soft_flags: list[str]

  @property
  def survives(self) -> bool:
    """Whether the clue passes on to the LLM verify step."""
    return not self.failures


@dataclass
class WordCheckResult:
  """Mechanical-check outcome for one word's generated output object."""

  word: str
  checked_clues: list[CheckedClue] = field(default_factory=list)
  word_failures: list[str] = field(default_factory=list)
  skips: list[Mapping[str, object]] = field(default_factory=list)

  @property
  def survivors(self) -> list[CheckedClue]:
    """The clues that passed every check."""
    return [c for c in self.checked_clues if c.survives]


def _check_required_tags(
  clue: Mapping[str, object], failures: list[str]
) -> None:
  """Validate the enum-valued fields every clue must carry."""
  for tag_field, enum_type in (
    ('style', Style),
    ('difficulty', Difficulty),
    ('confidence', Confidence),
  ):
    value = clue.get(tag_field)
    if value not in set(enum_type):
      failures.append(
        f'{tag_field} must be one of {sorted(enum_type)}, got {value!r}'
      )


def _check_american_fields(
  clue: Mapping[str, object], failures: list[str]
) -> None:
  """American clues need a trap proportionate to their difficulty."""
  trap = clue.get('trap')
  if clue.get('difficulty') in (Difficulty.MEDIUM, Difficulty.HARD):
    if not isinstance(trap, str) or not trap.strip():
      failures.append('medium/hard American clue must name its trap/ambiguity')


def _check_cryptic_fields(
  answer: str,
  clue: Mapping[str, object],
  clue_text: str,
  failures: list[str],
) -> None:
  """Cryptic clues need parse fields, exact letter math, and enumeration."""
  for required in ('definition', 'mechanism', 'parse'):
    value = clue.get(required)
    if not isinstance(value, str) or not value.strip():
      failures.append(f'cryptic clue missing required field {required}')

  found = clue_enumeration(clue_text)
  expected = expected_enumeration(answer)
  if found != expected:
    failures.append(
      f'enumeration {found or "missing"} does not match expected {expected}'
    )

  mechanism = str(clue.get('mechanism') or '').lower()
  fodder = clue.get('anagram_fodder')
  hidden = clue.get('hidden_string')

  if 'anagram' in mechanism and not fodder:
    failures.append('anagram mechanism requires anagram_fodder')
  if 'hidden' in mechanism and not hidden:
    failures.append('hidden mechanism requires hidden_string')

  if isinstance(fodder, str):
    if sorted(letters_only(fodder)) != sorted(letters_only(answer)):
      failures.append(
        f'anagram fodder {fodder!r} is not an exact letter'
        f' multiset of the answer'
      )
    if fodder.strip().lower() not in clue_text.lower():
      failures.append(
        f'anagram fodder {fodder!r} does not appear verbatim in the clue text'
      )
  elif fodder is not None:
    failures.append(f'anagram_fodder must be a string, got {fodder!r}')

  if isinstance(hidden, str):
    if letters_only(answer) not in letters_only(hidden):
      failures.append(
        f'hidden_string {hidden!r} does not contain the answer'
        f' as a contiguous substring'
      )
    if hidden.strip().lower() not in clue_text.lower():
      failures.append(
        f'hidden_string {hidden!r} does not appear verbatim in the clue text'
      )
  elif hidden is not None:
    failures.append(f'hidden_string must be a string, got {hidden!r}')


def check_clue(
  answer: str, clue: object, accepted_texts: Set[str]
) -> CheckedClue:
  """Run every mechanical check on one clue.

  Collects ALL failures rather than stopping at the first, so retry
  prompts can name everything that went wrong. accepted_texts is the
  bank-wide set of normalized accepted clue texts, for uniqueness.
  """
  if not isinstance(clue, Mapping):
    return CheckedClue({'raw': clue}, ['clue entry is not a JSON object'], [])

  failures: list[str] = []
  _check_required_tags(clue, failures)

  clue_text = clue.get('clue')
  if not isinstance(clue_text, str) or not clue_text.strip():
    failures.append('clue text is missing or empty')
    return CheckedClue(clue, failures, [])

  if has_answer_leak(answer, clue_text):
    failures.append('clue text contains the answer or an inflection')
  if normalize_clue_text(clue_text) in accepted_texts:
    failures.append('duplicate of a clue already in the accepted bank')

  if clue.get('style') == Style.AMERICAN:
    _check_american_fields(clue, failures)
  elif clue.get('style') == Style.CRYPTIC:
    _check_cryptic_fields(answer, clue, clue_text, failures)

  return CheckedClue(clue, failures, stem_soft_flags(answer, clue_text))


def check_word_output(
  answer: str, word_object: object, accepted_texts: Set[str]
) -> WordCheckResult:
  """Validate one word's whole generated object: clues plus skips."""
  result = WordCheckResult(word=answer)
  if not isinstance(word_object, Mapping):
    result.word_failures.append('output for word is not a JSON object')
    return result

  clues = word_object.get('clues')
  if not isinstance(clues, list):
    result.word_failures.append("'clues' is missing or not a list")
  else:
    for clue in clues:
      result.checked_clues.append(check_clue(answer, clue, accepted_texts))

  skips = word_object.get('skips', [])
  if isinstance(skips, list):
    result.skips = [s for s in skips if isinstance(s, Mapping)]
  else:
    result.word_failures.append("'skips' is not a list")
  return result
