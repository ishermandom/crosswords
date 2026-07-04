# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Confirm-stage padding variant v1: economy as a per-word deletion test.

Diagnosis (window ledger idea 7): the confirm's "name any padding" step judges
padding as a gestalt — a smooth surface reads as "None" — while Fable's economy
standard is a deletion test (ZED: "'That' is padding — 'Last character,
overseas' is tighter"). This variant makes the deletion test explicit, with a
plain-article carve-out so Fable-accepted surfaces like NINE "A full lineup on a
baseball field?" survive.
"""

import pipeline_local

_OLD_ECONOMY = '- Economy: name padding even when the surface reads smoothly.'
_NEW_ECONOMY = (
  '- Economy: test each word by deletion — if the clue keeps its\n'
  '  accuracy, its pivot, and its grammar without the word, the word\n'
  '  is padding, however smooth the surface. Demonstratives ("that",\n'
  '  "this"), intensifiers, and throat-clearing openers are the usual\n'
  '  offenders; a plain article is fine.'
)

_OLD_GUARD_EXAMPLE = (
  '- "Night watchman on patrol" -> GUARD: fixable. "on patrol" is padding\n'
  '  — "Night watchman" carries the whole definition.'
)
_NEW_GUARD_EXAMPLE = (
  '- "Night watchman on patrol" -> GUARD: fixable. "on patrol" is padding\n'
  '  — "Night watchman" carries the whole definition.\n'
  '- "This tallest peak" -> EVEREST: fixable. "This" points at nothing —\n'
  '  "Tallest peak" loses no accuracy, pivot, or grammar.'
)

_OLD_STEP_FOUR = '(4) name any padding.'
_NEW_STEP_FOUR = (
  '(4) economy: delete each word in turn and say which words the clue '
  'survives without — each survivor is padding unless it is a plain '
  'article.'
)

for attribute, old, new in [
  ('_CONFIRM_SYSTEM', _OLD_ECONOMY, _NEW_ECONOMY),
  ('_CONFIRM_SYSTEM', _OLD_GUARD_EXAMPLE, _NEW_GUARD_EXAMPLE),
  ('_CONFIRM_PROMPT', _OLD_STEP_FOUR, _NEW_STEP_FOUR),
]:
  text = getattr(pipeline_local, attribute)
  assert old in text, f'padding_v1: anchor not found in {attribute}: {old!r}'
  setattr(pipeline_local, attribute, text.replace(old, new))
