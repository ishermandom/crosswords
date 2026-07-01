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

# Import lib relative to this file, not via the cluegen package: PYTHONPATH
# carries the main repo root, so the package-qualified import silently loads
# the main checkout's harness instead of this worktree's.
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib import harness

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

Draft to the TARGET difficulty — it is a requirement, not a ceiling. For
medium, prefer a less-first sense or mild misdirection over the primary
straight definition. For hard, the surface should confidently invite a
wrong reading. At every difficulty, a dictionary-flat clue is a failure:
easy means accessible, never inert.

Two hard rules when drafting:
- The clue must define the answer word ITSELF — never a person or thing
  merely associated with it. ("One who might be called to service" defines
  a draftee, so it cannot clue DRAFT.)
- If a sense exists only inside a longer phrase (an idiom fragment — the
  "easy target" sense lives in SITTING DUCK, not in DUCK), discard the
  angle unless the clue genuinely works for the answer word alone.

For each draft: the clue text as it would appear in print, then on the next
line its angle name and the trap it sets — the trap is the specific wrong
answer (a real word or phrase) or wrong reading the surface invites; name
it concretely. Apply the craft invariants as you draft — economy, natural
surface, honest question mark. Plain unformatted text."""

_TURN_EDIT = """\
Now act as your own toughest editor. For EACH draft, perform the
substitution test — do not merely assert it. Write one natural sentence
using {word} in the clued sense, then rewrite the sentence with the clue's
definition in place of {word}. The draft fails if the rewritten sentence
changes part of speech, tense, number, or referent — or reads unnaturally.

Then check each surviving draft:
- Literal accuracy: every content word of the clue must be true of the
  answer in the clued sense. (A planted flower is not a "visitor"; a clue
  calling it one fails, however pretty the surface.)
- Question-mark honesty: a straight definition of ANY sense of the answer —
  even a surprising secondary sense — takes no ?. The ? marks genuine
  wordplay or a stretched definition, never apologizes for loose phrasing.
- No answer leakage; and the trap survives a re-read.

End with a verdict line per draft: KEEP or CUT, with the one-phrase
reason. Plain unformatted text."""

_TURN_EXTRACT = """\
Among the KEEP drafts, select the one closest to the {difficulty} target —
when two are equally close, take the livelier, more specific one. Never
default to the safest. Return it as JSON with these fields:
- "clue": exact print text.
- "difficulty": your honest calibration, which may differ from the target.
  A straight definition — even of a surprising secondary sense — is medium
  at most.
- "trap": one sentence written from the solver's perspective, in this
  shape: what the surface makes them read first, the specific wrong answer
  they would try (a real word, in CAPS), and the realization that escapes
  the trap. Null if the clue is straight.
- "confidence": honest; "low" if no draft survived cleanly."""

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
  parser.add_argument(
    '--fast-angles',
    action='store_true',
    help='angle turn without thinking (speed experiment: the angle list is '
    'already externalized reasoning; internal thinking may be redundant)',
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
        harness.UserTurn(
          _TURN_ANGLES.format(**substitutions),
          use_thinking=not cli.fast_angles,
        ),
        # think=False: exploration lives in the angle turn; with thinking
        # on, gemma4 can exhaust the window reasoning before emitting any
        # drafts.
        harness.UserTurn(
          _TURN_DRAFTS.format(**substitutions), use_thinking=False
        ),
        # Editor turn: the written-out substitution sentences are the
        # externalized reasoning, so thinking stays off.
        harness.UserTurn(
          _TURN_EDIT.format(**substitutions), use_thinking=False
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
