# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Quality evaluation as one focused turn per convention and rubric item.

Turns are ordered so each evaluation can build on prior ones: mechanical
conventions first, then the foundational wordplay check, then rubric
dimensions that depend on it. Thinking mode is enabled selectively — the
three turns requiring genuine weighing use think=True; the rest use
think=False with a brief inline trace. All turns produce a verdict and a
reason in ten words or fewer.

Compare against probe_quality_single.py to assess whether per-turn focus
improves accuracy or reduces total latency.

Usage:
  python prototyping/probe_quality_multi.py
  python prototyping/probe_quality_multi.py --clue "Keeps time?" --answer CLOCK
  python prototyping/probe_quality_multi.py --model gemma4:31b-mlx
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib import harness

_SYSTEM_PROMPT = """\
You are an experienced NYT crossword editor reviewing clues for publication.
Your role is quality gatekeeping: catch errors before they reach solvers. The
submission comes from a well-intentioned but inexperienced constructor — expect
mistakes, and apply each standard rigorously. A clue passes only when it
genuinely satisfies the requirement, not when a justification can be found for
it.

Use the first interpretation a reasonable solver would reach. Do not revisit a
judgment once made.

After each evaluation, reply with your verdict and a brief reason (ten words
or fewer):
  <grade>: <reason>
Some evaluations are scored as binary PASS/FAIL, others on a 1-5 scale.
Examples:
  FAIL: plural clue but singular answer
  4.5: direct surface but angle is the obvious default"""

# --- Conventions (turns 1–5) ---

_TURN_TENSE_AGREEMENT = """\
Style convention checks — starting with tense agreement.

The clue's grammatical form must agree with the answer (plural answer →
plural clue surface; verb answer → matching tense).

Output: <grade>: <reason> -- where the grade is PASS or FAIL"""

_TURN_ABBREVIATION_SIGNALED = """\
Convention: abbreviation signaled

Any abbreviation in the answer must be signaled in the clue (e.g. "Abbr.",
"briefly", or an abbreviated word in the clue). If the answer is not an
abbreviation, this passes automatically.

Output: <grade>: <reason> -- where the grade is PASS or FAIL"""

_TURN_FILL_FORMAT = """\
Convention: fill format

Blanks must be rendered as ___. If the clue has no fill blank, this passes
automatically.

Output: <grade>: <reason> -- where the grade is PASS or FAIL"""

_TURN_GENUINE_ALTERNATIVES = """\
Convention: genuine alternatives

The alternative answers a solver would consider must be real words or
phrases, not invented by the clue.

Output: <grade>: <reason> -- where the grade is PASS or FAIL"""

_TURN_WORDPLAY_INDICATOR = """\
Convention: wordplay indicator

A ? suffix is required when no reasonable surface reading leads directly to
the answer — the solver must make a non-obvious pivot (wordplay, pun, or
secondary meaning not reachable from the surface). It is forbidden when any
reasonable surface reading already delivers the answer.

Calibration: assume a mid-week solver who expects occasional misdirection.
Mild indirection does not require ?. ? is required only when reaching the
answer demands a non-obvious pivot.

Earned (? required):
- "Semi professional?" → TEAMSTER: "partly professional" gives no path to
  TEAMSTER. Only via pivot — semi = semi-truck, TEAMSTER = truck driver.
- "Perpetual homebody?" → SNAIL: only via pivot — a snail carries its home.

Unearned (? forbidden):
- "Keeps time?" → CLOCK: keeping time is a clock's primary function.
- "Draws blood?" → NEEDLE: drawing blood is a needle's most common use.

Output: <grade>: <reason> -- where the grade is PASS or FAIL"""

# --- Rubric dimensions (turns 6–11) ---

_TURN_SURFACE_COHERENCE = """\
Rubric dimensions — starting with surface coherence.

Polish of the surface reading: does the clue read as natural, idiomatic
language?
  1 = tortured syntax or forced phrasing
  5 = natural, idiomatic phrase

Output: <score>: <reason>"""

_TURN_ANGLE_CRAFT = """\
Rubric: angle craft

How deliberate and considered is the angle chosen for this clue? Evaluate
the constructor's choice independent of whether it creates misdirection.
  1 = obvious default or trivial antonym
  5 = unexpected, considered angle that creates recognition even without
      wordplay

Output: <score>: <reason>"""

_TURN_MISDIRECTION = """\
Rubric: misdirection

Strength of the surface misdirection — how confidently does the clue's
surface lead elsewhere before the answer clicks?
  1 = points directly at the answer
  5 = strong deliberate feint that confidently misleads

Output: <score>: <reason>"""

_TURN_FAIRNESS_OF_DECEPTION = """\
Rubric: fairness of deception

Cleanliness of the connection once the trick is seen — does it resolve
elegantly and unambiguously? Score 5 by default if this clue has no
misdirection.
  1 = ambiguity that doesn't fully resolve
  5 = elegant and unambiguous once the pivot lands

Output: <score>: <reason>"""

_TURN_ELASTICITY = """\
Rubric: elasticity

How many coherent interpretations does the clue support before the answer
is known?
  1 = single obvious meaning, no reinterpretation space
  5 = rich space with several plausible readings

Output: <score>: <reason>"""

_TURN_REFERENCE_ACCESSIBILITY = """\
Rubric: reference accessibility

How broadly accessible is the knowledge required? Score the intrinsic
breadth of what the clue demands, independent of puzzle difficulty.
  1 = niche or specialist knowledge
  5 = universal

Output: <score>: <reason>"""

if __name__ == '__main__':
  args = harness.parse_args('quality-multi')
  turns: list[harness.SystemTurn | harness.UserTurn] = [
    harness.SystemTurn(_SYSTEM_PROMPT),
    # Conventions: mechanical checks first, foundational wordplay check last.
    harness.UserTurn(
      f'Clue: {args.clue}\nAnswer: {args.answer}\n\n{_TURN_TENSE_AGREEMENT}',
      use_thinking=False,
    ),
    harness.UserTurn(_TURN_ABBREVIATION_SIGNALED, use_thinking=False),
    harness.UserTurn(_TURN_FILL_FORMAT, use_thinking=False),
    harness.UserTurn(_TURN_GENUINE_ALTERNATIVES, use_thinking=False),
    harness.UserTurn(_TURN_WORDPLAY_INDICATOR, use_thinking=True),
    # Rubric: surface and angle first, then misdirection chain, then remainder.
    harness.UserTurn(_TURN_SURFACE_COHERENCE, use_thinking=False),
    harness.UserTurn(_TURN_ANGLE_CRAFT, use_thinking=False),
    harness.UserTurn(_TURN_MISDIRECTION, use_thinking=True),
    harness.UserTurn(_TURN_FAIRNESS_OF_DECEPTION, use_thinking=True),
    harness.UserTurn(_TURN_ELASTICITY, use_thinking=False),
    harness.UserTurn(_TURN_REFERENCE_ACCESSIBILITY, use_thinking=False),
  ]
  harness.run_messages('quality-multi', turns, args, temperature=1.0)
