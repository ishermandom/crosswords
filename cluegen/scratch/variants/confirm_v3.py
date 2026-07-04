# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Confirm v3: a '?' licenses the stretch it marks; substitute cleanly.

Diagnosis (window ledger, baseline batch A): confirm v2 prosecutes marked
metaphor/metonymy as substitution failure — it kills Fable accepts DAISY
"Petal-puller's target?" (cultural metonymy the ? declares), AMBER "Prehistoric
time capsule?" ("a time capsule is an intentional vessel" — while acknowledging
the ? marks the metaphor), and CHECK "Threaten the king" (it substituted the
definition into a sentence already containing "the king", produced "threaten the
king the black king", and called the wreckage a referent shift). Nothing in v2
says the ? licenses the stretch, and nothing constrains the substitution
procedure.

v3 adds both: the marked-stretch license (with an invented CAVE example — the
EELS example stays as the counterweight: a marked stretch must still be true in
its figurative reading) and a clean-substitution instruction.
"""

import pipeline_local

_OLD_SUBSTITUTION = (
  '- Substitution: the clue could replace the answer in a sentence — part\n'
  '  of speech, tense, number, register, and referent all hold.'
)
_NEW_SUBSTITUTION = (
  '- Substitution: the clue could replace the answer in a sentence — part\n'
  '  of speech, tense, number, register, and referent all hold. Choose a\n'
  '  sentence where the answer stands alone, so the definition swaps in\n'
  "  without duplicating the sentence's own words. A '?' on the clue\n"
  '  marks a stretched, figurative, or metonymic definition as\n'
  '  intentional: test whether the figurative reading substitutes\n'
  '  fairly — a marked stretch is not a referent shift.'
)

_OLD_QUESTION_MARK = (
  '- Question-mark honesty: a ? belongs only with genuine wordplay or a\n'
  '  stretched definition; a straight definition takes none.'
)
_NEW_QUESTION_MARK = (
  '- Question-mark honesty: a ? belongs only with genuine wordplay or a\n'
  '  stretched definition; a straight definition takes none. The license\n'
  '  runs the other way too: an earned ? covers the stretch it marks —\n'
  '  do not fail substitution or literal truth for the very stretch the\n'
  '  ? declares.'
)

_OLD_THOU_EXAMPLE = (
  '- "You, old-style" -> THOU: bankable. A secondary or archaic sense is\n'
  '  fully legitimate.'
)
_NEW_THOU_EXAMPLE = (
  '- "You, old-style" -> THOU: bankable. A secondary or archaic sense is\n'
  '  fully legitimate.\n'
  '- "Nature\'s refrigerator?" -> CAVE: bankable. The ? marks the\n'
  '  metaphor, and the metaphor is true — caves genuinely keep things\n'
  '  cold. A marked stretch that reads fairly is not a flaw.'
)

for old, new in [
  (_OLD_SUBSTITUTION, _NEW_SUBSTITUTION),
  (_OLD_QUESTION_MARK, _NEW_QUESTION_MARK),
  (_OLD_THOU_EXAMPLE, _NEW_THOU_EXAMPLE),
]:
  assert old in pipeline_local._CONFIRM_SYSTEM, f'confirm_v3 anchor: {old!r}'
  pipeline_local._CONFIRM_SYSTEM = pipeline_local._CONFIRM_SYSTEM.replace(
    old, new
  )

_OLD_STEP_ONE = (
  'write one '
  'natural sentence using the answer in the clued sense, substitute '
  "the clue's definition, and say whether part of speech, tense, "
  'number, or referent shifts'
)
_NEW_STEP_ONE = (
  'write one '
  'natural sentence where the answer stands alone in the clued sense '
  '(for a ?-marked clue, its intended figurative sense), substitute '
  "the clue's definition, and say whether part of speech, tense, "
  'number, or referent shifts beyond any stretch the ? marks'
)
assert _OLD_STEP_ONE in pipeline_local._CONFIRM_PROMPT
pipeline_local._CONFIRM_PROMPT = pipeline_local._CONFIRM_PROMPT.replace(
  _OLD_STEP_ONE, _NEW_STEP_ONE
)
