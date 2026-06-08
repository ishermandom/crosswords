# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Quality evaluation as one focused turn per convention and rubric item.

A solve-first pre-pass (think=True) works through the intended solve path and
establishes shared context — alternative answers and clue readings — so
subsequent turns can score rather than discover. Misdirection is scored before
the wordplay indicator so the indicator can reference the established feint
strength. Thinking mode is selective: the pre-pass and misdirection use
think=True; all other turns use think=False.

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

_SYSTEM_PROMPT_INTRO = """\
You are an experienced NYT crossword editor. A well-intentioned but
inexperienced puzzle constructor has submitted a clue for you to review."""

_SYSTEM_PROMPT_EVALUATION = """\
Your role is quality gatekeeping: catch errors before they reach solvers.
Expect mistakes from this constructor, and apply each standard rigorously —
a clue passes only when it genuinely satisfies the requirement, not when a
justification can be found for it.

Use the first interpretation a reasonable solver would reach. Do not revisit
a judgment once made.

After each evaluation, reply with your verdict and a brief reason (ten words
or fewer):
  <grade>: <reason>
Some evaluations are scored as binary PASS/FAIL, others on a 1-5 scale.
Examples:
  FAIL: plural clue but singular answer
  4.5: direct surface but angle is the obvious default"""

# --- Solve-first pre-pass ---

_TURN_SOLVE_FIRST = """\
Work through how a solver reaches this answer. Keep your reasoning brief —
identify the mechanism in a few steps, then commit. Output exactly three
labeled lines — no markdown, no headers, no bullets:

Solve path: [surface reading] → [what makes the answer click; name any pivot
  mechanism, or note "straight definition" and describe the angle chosen]
Alternative answers: [comma-separated real words or phrases a solver would
  try before landing on the correct answer]
Clue readings: [semicolon-separated interpretations of the clue surface a
  solver might hold before the answer is known]

Example 1 (straight definition) — "Long stretch of time" → EON:
Solve path: surface describes an extended duration → straight definition:
  an eon is a very long period; angle uses "stretch" as a synonym
Alternative answers: ERA, AGE, EPOCH
Clue readings: a very long period; a stretch of geological time

Example 2 (pivot) — "Perpetual homebody?" → SNAIL:
Solve path: surface suggests someone who never leaves home → pivot: a snail
  carries its home everywhere, so it is always "home"; double meaning
Alternative answers: HERMIT, RECLUSE, SHUT-IN
Clue readings: a person who stays home constantly; a creature in its shell"""

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
  solve_first_user = (
    f'Clue: {args.clue}\nAnswer: {args.answer}\n\n{_TURN_SOLVE_FIRST}'
  )

  # Two conversations rather than one long one. The 31b-mlx model hits a
  # generation cliff mid-run when KV cache accumulation pushes compressed
  # memory past a threshold (observed: 8–10 GB compressed, dropping to
  # 0.2 tok/s after the cliff). Splitting discards the cache between
  # conversations, keeping each short enough to stay below the wall.
  # The solve-first output is seeded into conversation 2 as a minimal prior
  # exchange — the full solve-first prompt stays out of conversation 2's
  # context, so the split also reduces prefill tokens for evaluation turns.
  with harness.Session('quality-multi', args, temperature=1.0) as session:
    # Conversation 1: solver mode only — minimal persona, no evaluation
    # framing. Keeping this conversation separate prevents the gatekeeping
    # role and output-format instructions from bleeding into the solve-first
    # analysis and pushing the model toward premature evaluation.
    # think=True: discovering the solve path is genuine interpretive work.
    solve_response = session.run_conversation(
      [
        harness.SystemTurn(_SYSTEM_PROMPT_INTRO),
        harness.UserTurn(solve_first_user, use_thinking=True),
      ]
    )

    # Conversation 2: evaluation mode. The solve-first output is seeded as a
    # prior exchange so the model has full context without re-running the call.
    session.run_conversation(
      [
        harness.SystemTurn(_SYSTEM_PROMPT_EVALUATION),
        harness.SeedTurn(
          f'Clue: {args.clue}\nAnswer: {args.answer}\n\n'
          f'A solver analysis was run on this clue. Use the following as'
          f' established context for your evaluation:',
          solve_response or '',
        ),
        # think=False: tense, abbreviation, fill format, and genuine alternatives
        # are mechanical pattern checks — no interpretive weighing required.
        harness.UserTurn(_TURN_TENSE_AGREEMENT, use_thinking=False),
        harness.UserTurn(_TURN_ABBREVIATION_SIGNALED, use_thinking=False),
        harness.UserTurn(_TURN_FILL_FORMAT, use_thinking=False),
        harness.UserTurn(_TURN_GENUINE_ALTERNATIVES, use_thinking=False),
        # Misdirection precedes the wordplay indicator: scoring the feint
        # strength (1–5) is the substantive judgment; the indicator then just
        # asks whether that feint warrants a ?. think=True here; think=False
        # for the indicator because it reads off the misdirection score.
        harness.UserTurn(_TURN_MISDIRECTION, use_thinking=True),
        harness.UserTurn(_TURN_WORDPLAY_INDICATOR, use_thinking=False),
        # think=False for the remaining rubric dimensions: surface coherence and
        # angle craft are stylistic reads with no deep dependency; fairness of
        # deception and elasticity both have the solve path and misdirection
        # score in context, so they score without re-deriving the mechanism.
        harness.UserTurn(_TURN_SURFACE_COHERENCE, use_thinking=False),
        harness.UserTurn(_TURN_ANGLE_CRAFT, use_thinking=False),
        harness.UserTurn(_TURN_FAIRNESS_OF_DECEPTION, use_thinking=False),
        harness.UserTurn(_TURN_ELASTICITY, use_thinking=False),
        harness.UserTurn(_TURN_REFERENCE_ACCESSIBILITY, use_thinking=False),
      ]
    )
