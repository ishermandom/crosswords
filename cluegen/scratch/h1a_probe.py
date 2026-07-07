# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""H1a sanity check: satisfaction-seeded brainstorm, one word, eyeball drafts.

H1a (`setter.md`): a brainstorm seeded by satisfaction basis — at least two
angles per basis — produces more non-flat drafts per word than the
semantic-sense seeding in `pipeline_local._TURN_ANGLES`. This probe runs the
seeded variant once so the drafts can be eyeballed against the baseline drafts
already collected in `logs/setter_draft_inventory.jsonl`.

The drafts turn keeps the baseline's draft count (4 or 5) and its three hard
rules verbatim, so the only variable is the seeding. Difficulty is absent from
both turns by design: satisfaction replaced difficulty as the target.

First arm's result (2 samples, COURT): the model fills the basis rubric with the
same shallow senses and just labels them — bases are qualities to be, not moves
to make. The second arm seeds by the taxonomy's MECHANISMS list instead
(recipes, not qualities), whole list shown per `satisfaction.md`'s own usage
rule.

Usage: python3 h1a_probe.py [WORD] [basis|mechanism] (default: COURT basis)
"""

import datetime
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import pipeline_local

_MODEL = os.environ.get('H1A_MODEL', 'gemma4:26b-qat')

# The five bases of satisfaction, one-line definitions copied from
# `cluegen/local/satisfaction.md` (the whole list, never one favored mechanism —
# per that document's own usage rule).
_TURN_ANGLES_SATISFACTION = """\
Answer word: {word}

Brainstorm cluing angles for {word}, organized by the kind of satisfaction
each would deliver to the solver. Work through all five bases below; for
each basis, propose at least two genuinely distinct angles:

- The aha: the surface points somewhere else; the answer is obvious only
  in retrospect — confirming it lands as "of course."
- Elegance: phrasing so apt and economical that a straight clue pleases on
  its own — nothing wasted, nothing trivial.
- Fair resistance: hard to get cold but gettable — and confirmable — with
  crossing letters.
- Prize trivia: the solver recalls or learns something interesting but not
  obscure; the clue is a small gift of fact.
- Fun: humor or surprise in the surface itself — simply enjoyable to read.

For each angle: a short name, one sentence on how it applies to {word},
and which sense or convention of {word} it exploits. No clue drafts yet —
this turn is breadth, not phrasing. Plain unformatted text; your output
will be read by an LLM in the next turn."""

# The ten mechanisms, one-line definitions and examples copied from
# `cluegen/local/satisfaction.md`. The double-definition example is swapped
# (BARK for COURT) so the list never hands the test word a ready-made clue.
_TURN_ANGLES_MECHANISM = """\
Answer word: {word}

Brainstorm cluing angles for {word} by working through the mechanism list
below — the distinct ways a clue can work. For each mechanism that can
apply to {word}, propose one angle; skip a mechanism only when it genuinely
cannot apply. Be concrete: name the specific sense, frame, fact, scene, or
image the angle uses — a vague classification is useless to the next turn.
For prize fact, state the actual fact.

1. Sense pivot: lead with one sense of a polysemous word; the answer uses
   another. ("Bank deposit?" for SILT)
2. Frame anchor: the answer's meaning lives inside a named cultural,
   regional, or professional frame. ("Love, at Wimbledon" for ZERO)
3. Count or role metonymy: define the answer by what it counts or the role
   it plays. ("Innings in a standard ballgame" for NINE)
4. Definition by example: a specific instance stands in for the answer's
   class, usually flagged with a ?. ("Jackson one might break?" for TWENTY)
5. Double definition: two unrelated senses joined in one surface, each
   independently defining the answer. ("Tree covering or dog's warning" for
   BARK)
6. Conceptual reframe: an abstract property described concretely, as a
   small riddle. ("It separates the positives from the negatives" for ZERO)
7. Metaphor as definition: a figurative description that is literally apt
   on inspection. ("Prehistoric time capsule?" for AMBER)
8. Vignette: a tiny scene the answer completes. ("Reaction to a jump
   scare" for GASP)
9. Relational pivot: the answer defined by its relation to another
   quantity or item, where the relation itself carries surprise.
   ("One-twelfth gross?" for DOZEN)
10. Prize fact: a straight clue carried by interesting, checkable trivia.
    ("Spinal Tap amp's top setting" for ELEVEN)

No clue drafts yet — this turn is breadth, not phrasing. Plain unformatted
text; your output will be read by an LLM in the next turn."""

# Third arm, prompted by the micro-probe finding (2026-07-06): a direct ask for
# raw material yields vivid concrete scenes that the angle rubrics suppress.
# Material first, then clues from the material.
_TURN_ANGLES_MATERIAL = """\
Answer word: {word}

List 10 pieces of vivid raw material about {word} a crossword clue could
be built from: interesting checkable facts, tiny concrete scenes, cultural
frames, and surprising senses. Cover several senses of {word}, and include
at least two genuinely checkable facts. No clue drafts yet. Each item: one
concrete sentence. Vague classifications are useless; a specific fact or
image is the goal. Plain unformatted text; your output will be read by an
LLM in the next turn."""

_TURN_DRAFTS_MATERIAL = """\
Pick the 4 or 5 pieces of material that promise the most solver
satisfaction — spread across different senses of {word}, not variants of
one. Draft exactly one clue per chosen piece, building the clue from that
material.

Three hard rules when drafting:
- The clue must define the answer word ITSELF — never a person or thing
  merely associated with it.
- If a sense exists only inside a longer phrase (an idiom fragment),
  discard the material unless the clue genuinely works for the answer word
  alone.
- No dictionary-flat surfaces. A draft that could pass as a thesaurus
  entry or dictionary gloss is dead on arrival — each surface must put a
  specific scene, image, or wordplay in the solver's head. (Both clue
  IRIS: "Messenger from the clouds?" lives; "Part of the eye" is flat
  despite being accurate.)

For each draft: the clue text as it would appear in print, then on the
next line the material it was built from, in a few words. Apply the craft
invariants as you draft. Plain unformatted text."""

# Fifth arm (H3-lite, after rung 1): on the adverb SELDOM every vivid-arm draft
# was a scene-sentence that cannot substitute for the answer. This draft turn
# forces the substitution frame — sentence first, clue cast to replace the word
# in it — while keeping the vivid arm's selection rules.
_TURN_DRAFTS_CAST = """\
Pick the 4 or 5 most VIVID pieces — the ones with a specific image, scene,
or fact. A generic sense description is an automatic skip, however safe it
feels.

For each chosen piece, work in three steps:
1. Write one natural sentence that uses {word} in the target sense.
2. Write a clue that could replace {word} in that sentence exactly —
   same part of speech, tense, and number — while keeping the piece's
   specific image or fact. If the image cannot survive the cast, pick a
   different piece.
3. Check: the clue must define {word} itself, never a person or thing
   merely associated with it, and must not read like a dictionary gloss.

Output for each: the sentence, then the clue text as it would appear in
print, then the material in a few words. Plain unformatted text."""

# Seventh arm (pick-step repair): the vividness-only pick discards
# satisfaction-rich material — for TWELVE it chose eggs/inches/months over
# jurors/apostles/clock-face, losing the count-metonymy aha clues the old funnel
# banked. Selection here spreads across kinds of satisfaction (principle 4), not
# just image sharpness.
_TURN_DRAFTS_DIVERSE = """\
Pick the 4 or 5 pieces that together promise the most VARIED solver
satisfaction — at most one per kind: the sharpest image or scene, the best
misdirection potential (a surface a solver will read the wrong way first),
the most interesting checkable fact, the most surprising sense of {word}.
Spread the picks across different senses. A generic sense description ("an
official venue for legal proceedings") is an automatic skip, however safe
it feels. Draft exactly one clue per chosen piece.

The printed clue must keep the piece's specific image, fact, or
misdirection — if it does not survive into the clue text, the draft is a
failure. The other hard rules:
- The clue must define the answer word ITSELF — never a person or thing
  merely associated with it.
- The clue must be able to substitute for {word} in a sentence — matching
  part of speech, tense, and number.
- No dictionary-flat surfaces.

For each draft: the clue text as it would appear in print, then on the
next line the material it was built from, in a few words. Plain
unformatted text."""

# Eighth arm (material-width repair): TWELVE and FRANK fail upstream of the pick
# — "vivid raw material" biases toward imagery, missing count-metonymy
# satisfaction and whole senses (FRANK's frankfurter never appears). A sense
# inventory first, then material spread across it.
_TURN_MATERIAL_SENSES = """\
Answer word: {word}

First, list every sense of {word} you know — parts of speech, slang,
abbreviations and shortened forms, names, and uses inside professional or
cultural frames. One line each.

Then list 10 pieces of vivid raw material spread across those senses:
interesting checkable facts, tiny concrete scenes, roles the word plays
(what it counts, who it names, where it appears), and surprising senses.
No clue drafts. Each item: one concrete sentence naming which sense it
uses. Vague classifications are useless; a specific fact, image, or role
is the goal."""

# Ninth arm (conversion repair, fresh ladder): sense-inventory width reaches the
# draft turn but non-imagery material converts to mush ("Relating to a
# bratwurst") — the model lacks the crossword conventions for shortenings and
# count metonymy. A compact conventions block, examples from non-test words,
# spread across kinds per `satisfaction.md`'s no-single-mechanism rule.
_TURN_DRAFTS_CONVENTIONS = """\
Pick the 4 or 5 pieces that together promise the most VARIED solver
satisfaction — at most one per kind: the sharpest image or scene, the best
misdirection potential, the most interesting checkable fact, the most
surprising sense of {word}. Spread the picks across different senses. A
generic sense description is an automatic skip, however safe it feels.
Draft exactly one clue per chosen piece.

Crossword conventions — use whichever the material calls for:
- A shortened, slang, or informal form is fair when the clue signals it:
  "Kitchen cooler, briefly" clues FRIDGE; "for short" and "informally"
  work the same way.
- A number or quantity word can be defined by a set it famously counts:
  "Innings in a standard ballgame" clues NINE.
- A name can be clued through a famous bearer's well-known frame, as long
  as the clue defines the name itself.

The printed clue must keep the piece's specific image, fact, or
misdirection. The other hard rules:
- The clue must define the answer word ITSELF — never a person or thing
  merely associated with it.
- The clue must be able to substitute for {word} in a sentence — matching
  part of speech, tense, and number.
- No dictionary-flat surfaces.

For each draft: the clue text as it would appear in print, then on the
next line the material it was built from, in a few words. Plain
unformatted text."""

# Sixth arm (true H3): the single-turn cast traded vividness for legality (SCORE
# drafts went flat) while SELDOM's stayed adverbially illegal. Split the tension
# across turns: draft vividly first (unchanged vivid turns), then a dedicated
# re-cast turn that repairs grammar with the image held fixed.
_TURN_RECAST = """\
Now test each draft for substitution legality. For each draft, one at a
time:

1. Write one natural sentence that uses {word} in the draft's sense.
2. Try replacing {word} in that sentence with the draft's clue text. If
   the sentence stays natural — same part of speech, tense, and number —
   the draft passes unchanged.
3. If it fails, RE-CAST the clue: keep its specific image or fact, change
   only its grammatical form so it could replace {word} exactly. For an
   adverb answer, the whole clue must work as an adverb; for a verb, as
   that verb form. If the image cannot survive any legal cast, drop the
   draft.

Finish with the final list: each clue as it would print, one per line,
nothing else after the list."""

# Fourth arm (try 6 of the wording budget). Diagnosis from the material arm: the
# pick step chooses the flattest material and the draft step restates material
# as definition. This arm pins turn 1 to the exact micro-probe wording that
# produced vivid scenes, selects by vividness explicitly, and requires the
# printed clue to keep the material's specific image.
_TURN_MATERIAL_VIVID = """\
Answer word: {word}

List 8 pieces of vivid raw material about {word} a crossword clue could be
built from — interesting checkable facts, tiny concrete scenes, cultural
frames, and surprising senses. No clue drafts. Each item: one concrete
sentence. Vague classifications are useless; a specific fact or image is
the goal."""

_TURN_DRAFTS_VIVID = """\
Pick the 4 or 5 most VIVID pieces — the ones with a specific image, scene,
or fact. A generic sense description ("an official venue for legal
proceedings") is an automatic skip, however safe it feels. Draft exactly
one clue per chosen piece.

The printed clue must keep the material's specific image or fact — if the
image does not survive into the clue text, the draft is a failure. The
other hard rules:
- The clue must define the answer word ITSELF — never a person or thing
  merely associated with it.
- The clue must be able to substitute for {word} in a sentence — matching
  part of speech, tense, and number.
- No dictionary-flat surfaces.

For each draft: the clue text as it would appear in print, then on the
next line the material it was built from, in a few words. Plain
unformatted text."""

_TURN_DRAFTS_SATISFACTION = """\
Pick the 4 or 5 angles that promise the most solver satisfaction — spread
across different bases, not variants of one. Draft exactly one clue per
chosen angle.

Three hard rules when drafting:
- The clue must define the answer word ITSELF — never a person or thing
  merely associated with it.
- If a sense exists only inside a longer phrase (an idiom fragment),
  discard the angle unless the clue genuinely works for the answer word
  alone.
- No dictionary-flat surfaces. A draft that could pass as a thesaurus
  entry or dictionary gloss is dead on arrival — each surface must put a
  specific scene, image, or wordplay in the solver's head. (Both clue
  IRIS: "Messenger from the clouds?" lives; "Part of the eye" is flat
  despite being accurate.)

For each draft: the clue text as it would appear in print, then on the
next line its angle name and the satisfaction basis it aims at. Apply the
craft invariants as you draft. Plain unformatted text."""


def main() -> None:
  """Run the two seeded turns on one word; tee the transcript to a log."""
  word = sys.argv[1].upper() if len(sys.argv) > 1 else 'COURT'
  arm = sys.argv[2] if len(sys.argv) > 2 else 'basis'
  turns = {
    'basis': [_TURN_ANGLES_SATISFACTION, _TURN_DRAFTS_SATISFACTION],
    'mechanism': [_TURN_ANGLES_MECHANISM, _TURN_DRAFTS_SATISFACTION],
    'material': [_TURN_ANGLES_MATERIAL, _TURN_DRAFTS_MATERIAL],
    'vivid': [_TURN_MATERIAL_VIVID, _TURN_DRAFTS_VIVID],
    'cast': [_TURN_MATERIAL_VIVID, _TURN_DRAFTS_CAST],
    'develop': [_TURN_MATERIAL_VIVID, _TURN_DRAFTS_VIVID, _TURN_RECAST],
    'diverse': [_TURN_MATERIAL_VIVID, _TURN_DRAFTS_DIVERSE, _TURN_RECAST],
    'senses': [_TURN_MATERIAL_SENSES, _TURN_DRAFTS_DIVERSE, _TURN_RECAST],
    'conventions': [
      _TURN_MATERIAL_SENSES,
      _TURN_DRAFTS_CONVENTIONS,
      _TURN_RECAST,
    ],
  }[arm]
  timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
  log_path = (
    pathlib.Path(__file__).parent
    / 'logs'
    / f'h1a_probe_{word}_{arm}_{timestamp}.log'
  )

  messages = [{'role': 'system', 'content': pipeline_local._SETTER_SYSTEM}]
  transcript = []
  for template in turns:
    messages.append({'role': 'user', 'content': template.format(word=word)})
    reply = pipeline_local._chat(_MODEL, messages)
    messages.append({'role': 'assistant', 'content': reply})
    header = f'--- {template.splitlines()[0][:40]}'
    transcript.append(f'{header}\n{reply}\n')
    print(f'{header}\n{reply}\n', flush=True)

  log_path.write_text(
    f'model: {_MODEL}\nword: {word}\narm: {arm}\n\n' + '\n'.join(transcript)
  )
  print(f'transcript: {log_path}')


if __name__ == '__main__':
  main()
