# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Screen fun-gradient variant v1: evoked moment vs listed properties.

Diagnosis (window ledger idea 8): the 2026-07-02 fun gradient kills
stock-association clues, but the screen extends it to surfaces whose vividness
lives in one precise cultural moment (GASP "Reaction to a jump scare" — Fable:
accept, fun; screen: 8/8 fixable, basis none, explicitly reasoning "recognition
of a common experience"). Fable-generated calibration pairs
(`fun_calibration_verdicts.jsonl`, $0.32) pin the line: an evoked, specific
lived moment earns fun with no pivot; props, ingredients, and generic frames
don't. This variant states that line and adds the crispest generated pair
(SNOOZE) as a graded example.
"""

import pipeline_local

_OLD_GRADIENT_CLOSE = (
  'Flatness is the absence of any pivot,\n'
  '  surprise, or specificity — never the presence of common knowledge.'
)
_NEW_GRADIENT_CLOSE = (
  'Flatness is the absence of any pivot,\n'
  '  surprise, or specificity — never the presence of common knowledge.\n'
  '  The fun line runs between an evoked moment and listed properties: a\n'
  '  surface that stages a specific lived scene or pins a precise\n'
  '  cultural moment earns fun with no pivot; naming the answer\'s\n'
  '  props, ingredients, or usual location does not.'
)

_OLD_DUCK_EXAMPLE = (
  '- "Heads down!" -> DUCK: bankable (easy; basis: fun). No pivot and no\n'
  '  trap — the surface\'s own wit earns the bank. Fun or elegance in the\n'
  '  image or register is a full basis, without misdirection.'
)
_NEW_DUCK_EXAMPLE = (
  '- "Heads down!" -> DUCK: bankable (easy; basis: fun). No pivot and no\n'
  '  trap — the surface\'s own wit earns the bank. Fun or elegance in the\n'
  '  image or register is a full basis, without misdirection.\n'
  '- "Button smacked at 6:00, 6:09, and 6:18" -> SNOOZE: bankable (easy;\n'
  '  basis: fun). The escalating timestamps stage a lived mini-scene —\n'
  '  the specificity of the moment is the fun.\n'
  '- "Alarm clock button" -> SNOOZE: fixable. The same territory as a\n'
  '  generic object frame — props and location, no evoked moment.'
)

for old, new in [
  (_OLD_GRADIENT_CLOSE, _NEW_GRADIENT_CLOSE),
  (_OLD_DUCK_EXAMPLE, _NEW_DUCK_EXAMPLE),
]:
  assert old in pipeline_local._JUDGE_SYSTEM, f'fun_v1: anchor missing: {old!r}'
  pipeline_local._JUDGE_SYSTEM = pipeline_local._JUDGE_SYSTEM.replace(old, new)
