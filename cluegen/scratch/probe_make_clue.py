# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Multi-turn clue brainstorm probe.

Drives the constructor through the full 8-turn brainstorm workflow: answer
analysis → mechanism generation → filtering → drafting → solver simulation
→ refinement → polish → extract. Each turn targets one cognitive mode to
prevent the model from anchoring on its first mechanism and producing
variations on it.

Usage:
  python cluegen/scratch/probe_make_clue.py
  python cluegen/scratch/probe_make_clue.py --answer SNAIL
  python cluegen/scratch/probe_make_clue.py --model gemma4:26b-qat
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cluegen.scratch.lib import harness

_SYSTEM_PROMPT = """\
You are an experienced NYT crossword constructor with a reputation for
precision and craft. You write clues that are fair and rewarding. Every
clue you publish has been tested against a simple standard: a solver who
gets it should feel the click of a well-made thing — not just "that works"
but "that's exactly right." The surface reads naturally; the answer lands
cleanly.

For each clue, you follow a structured multi-turn process:
semantic inventory → mechanism brainstorm → filter → drafting → solver
simulation → refinement → polish → extract. Each turn builds on the one
before it.

Target difficulty: Wednesday. Middle of the NYT scale. Aim for clues that
require a beat of recognition from a practiced solver — not the first and
most obvious angle, but not a tremendous leap either. Wordplay and mild
misdirection are welcome and common, though not required on every clue.
References can go beyond universal; assume a solver who does the puzzle
regularly. Some clues will be simpler, some harder; the target is the zone,
not a fixed point."""

# --- Turn 1: Answer analysis ---

_TURN_ANSWER_ANALYSIS = """\
Target answer: {word}

This is the semantic inventory. Map the full space of what this word means
and connects to, so the mechanism brainstorm that follows has a broad set of
angles to draw on.

Cover all parts of speech and senses, including rare, figurative, and
archaic ones; the semantic fields and domains the word belongs to across
those senses; and associations, idioms, compound phrases, and cultural
references the word appears in or evokes.

Your output will be read by an LLM in the next turn — use plain,
unformatted text. Close with a brief note on which senses are most
polysemous and which domains have the most semantic connections."""
# TODO: Once turn 2 is stable, evaluate whether the closing note adds value —
# the inventory itself may be sufficient input for the mechanism brainstorm.

# --- Turn 2: Angle brainstorm ---

_TURN_ANGLE_BRAINSTORM = """\
This is the angle brainstorm. Draw on the semantic inventory from the
previous turn and generate a breadth of distinct cluing angles for {word}
— typically 20 or more.

A cluing angle is an approach that could yield a clue: a combination of
what semantic territory the clue's surface inhabits and what structural
device connects it to the answer. Two dimensions of variation to think
across:

Surface domain — what context does the clue appear to be about? A clue's
surface can live in sports, finance, fashion, idiom, historical usage, or
any other territory while the answer draws on a potentially different sense.

Structural device — what kind of wordplay or definitional approach makes
the connection? Two broad subcategories to draw from:

Definitional: direct definition, fill-in-the-blank, indirect definition
via a related phrase, synonym, near-synonym, and so on.

Wordplay: double meaning exploiting two senses simultaneously, part-of-
speech switch disguising the answer's grammatical role, garden-path
misdirection where the surface leads the solver toward a different sense,
pun, and so on.

Include several angles from each subcategory — not just variations on
direct definition. Go beyond both lists freely.

For each angle, give it a name and one or two sentences on how it applies
to {word}. No clue drafts — this turn is about breadth, not specific
phrasing. No evaluation of which angles are strongest; that comes next.
Your output will be read by an LLM — use plain, unformatted text."""

# --- Turns 3–8 (not yet implemented) ---
# Turn 3: Mechanism filter — shortlist 5–7 + 1–2 rough high-ceiling ideas
# Turn 4: Clue drafting — 3–5 drafts per mechanism, labeled by type
# Turn 5: Solver simulation + credibility check (Bullshit Rating)
# Turn 6: Refinement + diversity audit
# Turn 7: Polish — "?" convention, substitution test, abbreviation signals
# Turn 8: Extract — schema-enforced {"clues": [...]}

if __name__ == '__main__':
  args = harness.parse_args('make-clue')
  word = args.answer

  with harness.Session('make-clue', args, temperature=1.0) as session:
    session.run_conversation(
      [
        harness.SystemTurn(_SYSTEM_PROMPT),
        # think=False: the thinking trace mirrored the final output without
        # adding depth — semantic enumeration doesn't benefit from it.
        harness.UserTurn(
          _TURN_ANSWER_ANALYSIS.format(word=word),
          use_thinking=False,
        ),
        # think=True: generating 20+ non-overlapping angles requires active
        # search across surface domains and structural devices.
        harness.UserTurn(
          _TURN_ANGLE_BRAINSTORM.format(word=word),
          use_thinking=True,
        ),
        # Turns 3–8 will be added here as subsequent UserTurns once their
        # prompts are developed. All turns share one conversation so each
        # turn's output is in context for the next.
      ]
    )
