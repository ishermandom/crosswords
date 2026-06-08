# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Multi-turn clue brainstorm probe.

Drives the constructor through the full 8-turn brainstorm workflow: answer
analysis → mechanism generation → filtering → drafting → solver simulation
→ refinement → polish → extract. Each turn targets one cognitive mode to
prevent the model from anchoring on its first mechanism and producing
variations on it.

Usage:
  python prototyping/probe_make_clue.py
  python prototyping/probe_make_clue.py --answer SNAIL
  python prototyping/probe_make_clue.py --model gemma4:26b-qat
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib import harness

_SYSTEM_PROMPT = """\
You are an experienced NYT crossword constructor with a reputation for
precision and craft. Every clue you publish has been tested against a simple
standard: a solver who gets it should feel the click of a well-made thing —
not just "that works" but "that's exactly right."

You write clues that are fair and rewarding. Once the trick is seen, the
connection must be unambiguous in hindsight — no loose ends, no "I guess
that could work." The surface reads naturally; the answer lands cleanly.

Target difficulty: Wednesday. Middle of the NYT scale. Aim for clues that
require a beat of recognition from a practiced solver — not the first and
most obvious angle, but not a tremendous leap either. Wordplay and mild
misdirection are welcome and common, though not required on every clue.
References can go beyond universal; assume a solver who does the puzzle
regularly. Some clues will be simpler, some harder; the target is the zone,
not a fixed point."""

# --- Turn 1: Answer analysis ---

_TURN_ANSWER_ANALYSIS = """\
We're writing clues for {word} through a structured multi-turn process:
semantic inventory → mechanism brainstorm → filter → drafting → solver
simulation → refinement → polish → extract. Each turn builds on the one
before it.

This is the semantic inventory. Map the full space of what this word means
and connects to, so the mechanism brainstorm that follows has the broadest
possible set of angles to draw on — not just the most obvious one.

Cover all parts of speech and senses, including rare, figurative, and
archaic ones; the semantic fields and domains the word belongs to across
those senses; and associations, idioms, compound phrases, and cultural
references the word appears in or evokes.

Your output will be read by an LLM in the next turn — use plain text with
no markdown headers or bold. Close with a brief note on which senses are
most polysemous and which domains have the most semantic connections."""

# --- Turns 2–8 (not yet implemented) ---
# Turn 2: Mechanism brainstorm — 20+ mechanisms named but no clues written
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
        # Turns 2–8 will be added here as subsequent UserTurns once their
        # prompts are developed. All turns share one conversation so each
        # turn's output is in context for the next.
      ]
    )
