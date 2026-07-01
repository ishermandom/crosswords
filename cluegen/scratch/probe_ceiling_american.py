# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Ceiling-campaign probe: one American-style clue per run.

Generates a single American-style clue for an answer word at a target
difficulty, judged against the cloud bank's CLUE_SPEC Part A standard (the
spec text is condensed into the system prompt below — scratch probes copy
prompt text rather than importing it).

Two modes:
  default   — 3-turn scaffold: angle brainstorm → drafts → self-edit + JSON
  --single  — one turn straight to JSON; the unscaffolded floor

Usage:
  python cluegen/scratch/probe_ceiling_american.py --answer TWELVE
  python cluegen/scratch/probe_ceiling_american.py --answer FORTY --single
  python cluegen/scratch/probe_ceiling_american.py --model gemma4:31b-qat
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cluegen.scratch.lib import harness

_SYSTEM_PROMPT = """\
You are an expert setter writing American-style (NYT-style) crossword clues
for an acrostic puzzle's clue bank. You will develop ONE original clue for a
given answer word at a given difficulty.

The contract: a single deceptive definition or description. No cryptic
wordplay grammar — the craft is misdirection within a natural surface.

Craft invariants, applying at every difficulty:
- Accuracy: the clue could substitute for the answer in a sentence —
  matching part of speech, tense, number, and register. "Sprinted" cannot
  clue RUN.
- Economy: every word earns its place; remove anything removable.
- Natural surface: reads like something a person would actually say or
  write.
- Liveliness: prefer the vivid, specific angle over the dictionary-flat
  one: "Like a snowbird's November flight" beats "Toward the south" at
  identical difficulty. Easy does not mean dull.
- Cleverness that needs a paragraph to justify is a craft failure.
- Self-contained: acrostic clues cannot cross-reference other entries.
- The clue must not contain the answer word or a trivial inflection of it.

The difficulty dial — difficulty is how much work the solver does to bridge
clue and answer:
- easy: direct, one dominant reading, clearly signposted — but still
  crafted: vivid, specific, never inert.
- medium: ambiguity breadth — a common word in a less-first sense; a broad
  definition with several plausible candidates; mild trivia angles.
- hard: active misdirection — the surface confidently suggests a wrong
  reading via polysemy, part-of-speech flips, real-world convention, or
  register shifts. The aha must be fair in retrospect — punish confidence,
  not knowledge. The deadliest traps make a wrong answer fit until checked.
  Hard means twisted, not obscure: no trivia-lookup-only clues.

Question mark: signals wordplay, a stretched definition, or definition-by-
example. Use it honestly; its absence promises straightness.

Exemplars spanning the dial, for SOUTHWARD: "Like a snowbird's November
flight" (easy); "Down, to a cartographer?" (medium); "Which way the north
wind blows" (hard — NORTHWARD fits and has the same length; winds are named
for their origin). Also: NEPHEW, "One who might cry uncle?" (hard — the
idiom flips to a literal vocative).

Failure modes to reject in your own work: padding words; surfaces no human
would write; misdirection by obscurity instead of ambiguity; a question
mark used as an apology; a trap that does not survive a re-read."""

_TURN_ANGLES = """\
Answer word: {word}
Target difficulty: {difficulty}

First, brainstorm cluing angles — at least 10, genuinely distinct. An angle
combines a surface domain (what the clue appears to be about) and the sense
or convention of the answer it exploits. For each angle: a short name, one
sentence on how it applies to {word}, and the wrong reading a solver would
chase (the trap), if the angle sets one.

No clue drafts yet — this turn is breadth, not phrasing. Plain unformatted
text; your output will be read by an LLM in the next turn."""

_TURN_DRAFTS = """\
Pick the 4 or 5 strongest angles for a {difficulty} clue — favor genuine
traps and lively surfaces over safe, predictable definitions. Draft exactly
one clue per chosen angle.

For each draft: the clue text as it would appear in print, then on the next
line its angle name and the trap it sets. Apply the craft invariants as you
draft — substitution test, economy, natural surface, honest question mark.
Plain unformatted text."""

_TURN_EXTRACT = """\
Now act as your own toughest editor. Re-read each draft cold, as a solver
would. Check: substitution test (clue and answer interchangeable in a
sentence), tense and number agreement, question-mark honesty, no answer
leakage, and whether the trap survives a re-read.

Select the single best clue for a {difficulty} target and return it as
JSON: "clue" (exact print text), "difficulty" (your honest calibration,
which may differ from the target), "trap" (one sentence naming the
misdirection; null if the clue is straight), "confidence" (honest)."""

_TURN_SINGLE = """\
Answer word: {word}
Target difficulty: {difficulty}

Write ONE original American-style clue for this answer at this difficulty,
then return it as JSON: "clue" (exact print text), "difficulty" (your
honest calibration), "trap" (one sentence naming the misdirection; null if
the clue is straight), "confidence" (honest)."""

_CLUE_SCHEMA = {
  'type': 'object',
  'properties': {
    'clue': {'type': 'string'},
    'difficulty': {'type': 'string', 'enum': ['easy', 'medium', 'hard']},
    'trap': {'type': ['string', 'null']},
    'confidence': {'type': 'string', 'enum': ['high', 'medium', 'low']},
  },
  'required': ['clue', 'difficulty', 'trap', 'confidence'],
}

if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    description='Generate one American-style clue (ceiling campaign).'
  )
  parser.add_argument('--answer', default='TWELVE')
  parser.add_argument(
    '--difficulty', choices=['easy', 'medium', 'hard'], default='hard'
  )
  parser.add_argument('--model', default='gemma4:26b-qat')
  parser.add_argument(
    '--single', action='store_true', help='single-turn baseline mode'
  )
  cli = parser.parse_args()
  word = cli.answer.upper()

  probe_args = harness.ProbeArgs(clue='', answer=word, model=cli.model)
  substitutions = {'word': word, 'difficulty': cli.difficulty}

  with harness.Session(
    'ceiling-american', probe_args, temperature=1.0
  ) as session:
    if cli.single:
      turns: list[harness.SystemTurn | harness.UserTurn] = [
        harness.SystemTurn(_SYSTEM_PROMPT),
        harness.UserTurn(
          _TURN_SINGLE.format(**substitutions), json_schema=_CLUE_SCHEMA
        ),
      ]
    else:
      turns = [
        harness.SystemTurn(_SYSTEM_PROMPT),
        # think=True: angle search benefits from active exploration.
        harness.UserTurn(_TURN_ANGLES.format(**substitutions)),
        # think=False: exploration lives in the angle turn; with thinking
        # on, gemma4 can exhaust the window reasoning before emitting any
        # drafts.
        harness.UserTurn(
          _TURN_DRAFTS.format(**substitutions), use_thinking=False
        ),
        # think=False: the reasoning happened in the prior turns; this turn
        # is selection + transcription under the schema.
        harness.UserTurn(
          _TURN_EXTRACT.format(**substitutions),
          json_schema=_CLUE_SCHEMA,
          use_thinking=False,
        ),
      ]
    session.run_conversation(turns)
