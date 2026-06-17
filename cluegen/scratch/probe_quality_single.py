# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Probe full quality evaluation (conventions + rubric) in a single turn.

Tests whether the model can handle the complete evaluation in one shot with
focused attention — the thinking trace serves as the reasoning scratchpad.
Compare latency and correctness against the multi-turn production pipeline.

Usage:
  python cluegen/scratch/probe_quality_single.py
  python cluegen/scratch/probe_quality_single.py --clue "Keeps time?" --answer CLOCK
  python cluegen/scratch/probe_quality_single.py --model gemma4:31b-mlx
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cluegen.scratch.lib import harness

_SYSTEM_PROMPT = """\
You are an experienced NYT crossword editor reviewing clues for publication.
Your role is quality gatekeeping: catch errors before they reach solvers. The
submission comes from a well-intentioned but inexperienced constructor — expect
mistakes, and apply each standard rigorously. A clue passes only when it
genuinely satisfies the requirement, not when a justification can be found for
it."""

_USER_PROMPT = """\
Respond with JSON only:
{
  "conventions": {
    "has_tense_agreement": boolean,
    "has_wordplay_indicator": boolean,
    "is_abbreviation_signaled": boolean,
    "uses_fill_format": boolean,
    "has_genuine_alternatives": boolean
  },
  "scales": {
    "angle_craft": number,
    "misdirection": number,
    "elasticity": number,
    "reference_accessibility": number,
    "surface_coherence": number,
    "fairness_of_deception": number,
    "cross_check_payoff": number
  }
}

Conventions:

has_tense_agreement: the clue's grammatical form must agree with the answer
(plural answer → plural clue surface; verb answer → matching tense).

has_wordplay_indicator: reason from the clue to the answer, not the other way
around. Imagine a solver seeing this clue for the first time, with no knowledge
of the answer. Ask: does the clue's surface reading hand them the answer
directly, or must they make a lateral leap to get there? A ? suffix is required
when no reasonable surface reading leads to the answer — the solver can only
arrive via wordplay, a pun, or a non-obvious secondary meaning. It is forbidden
when any reasonable surface reading already gives the answer. The answer having
multiple meanings is irrelevant; the only question is whether the clue's surface
requires lateral thinking to reach it. A ? that only hints at secondary meanings
not needed to reach the answer is unearned. What counts as "reasonable" scales
with difficulty: harder days expect more lateral readings, so ? appears less
often on Friday/Saturday.

Earned (? required):
- "Semi professional?" → TEAMSTER: The surface ("partly professional") gives no
  path to TEAMSTER. Only once you pivot — "semi" = semi-truck, TEAMSTER =
  professional truck driver — does the answer emerge. ? is required.
- "Perpetual homebody?" → SNAIL: The surface ("someone who never goes out")
  gives no path to SNAIL. The pivot: take "homebody" literally — a snail
  carries its home on its body. ? is required.

Unearned (? forbidden):
- "Keeps time?" → CLOCK: Keeping time is a clock's primary function. The
  surface delivers directly. ? is unearned even though CLOCK has other meanings;
  those meanings aren't needed to reach the answer.
- "Points the way?" → COMPASS: Pointing a direction is what a compass does.
  The surface leads straight to the answer. ? is unearned.
- "Draws blood?" → NEEDLE: Drawing blood is what a needle does in its most
  common use. The surface delivers directly. ? is unearned.

is_abbreviation_signaled: any abbreviation in the answer must be signaled in
the clue (e.g. "Abbr.", "briefly", or an abbreviated word in the clue). If the
answer is not an abbreviation, this passes automatically.

uses_fill_format: blanks must be rendered as ___. If the clue has no fill
blank, this passes automatically.

has_genuine_alternatives: the alternative answers a solver would consider must
be real words or phrases, not invented by the clue.

Rubric dimensions (score 1–5):

angle_craft: deliberateness of the chosen angle (1 = obvious default/trivial
antonym, 5 = unexpected and considered)

misdirection: strength of surface misdirection (1 = points directly at the
answer, 5 = strong deliberate feint)

elasticity: supports multiple coherent interpretations (1 = single obvious
meaning, 5 = rich reinterpretation space)

reference_accessibility: breadth of required knowledge (1 = niche/specialist,
5 = universal)

surface_coherence: polish of the surface reading (1 = tortured syntax,
5 = natural, idiomatic phrase)

fairness_of_deception: cleanliness of the connection once seen (1 = ambiguity
that doesn't resolve, 5 = elegant and unambiguous). Score 5 by default for
clues with no misdirection.

cross_check_payoff: degree of genuine ambiguity left for crosses to resolve
(1 = clue already determines the answer, 5 = several plausible fills collapse
to one)

Decision policy:
- Use the first interpretation that a reasonable solver would reach.
- When a convention is clearly satisfied or violated, record the decision and
  move on. Do not search for additional interpretations after deciding.
- Rubric scores are approximate judgments. When multiple adjacent scores are
  defensible, choose the one that best fits the clue overall.
- Do not revisit completed checks. Prefer a good judgment reached quickly.
"""

if __name__ == '__main__':
  harness.run(
    'quality-single',
    _SYSTEM_PROMPT,
    _USER_PROMPT,
    temperature=1.0,
  )
