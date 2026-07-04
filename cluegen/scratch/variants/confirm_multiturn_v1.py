# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Confirm as four focused turns, verdict computed by code (window idea 10).

Confirm v2/v3 showed that a packed single turn carries one global posture: v2
prosecutes the very stretch a '?' marks (DAISY, AMBER, CHECK), while v3's
license wording broke flaw->verdict coupling everywhere — it names the flaws,
then banks anyway (DUSK, THIRD, SIXTEEN). Splitting the checks into fresh
single-shot conversations removes the coupling channel entirely: each turn
reports narrow FIELDS for one check, and the verdict — including the ?-license
rule — is computed here, in code the model never sees.

Turns (each a fresh conversation with its own schema):

1. substitution -> `{shift, shift_is_the_marked_stretch}`
2. literal truth -> `{failing_qualifiers}`
3. economy -> `{padding_words}` (article-only entries excluded in code — the
   carve-out that failed as prompt text in padding v1)
4. sense ownership -> `{is_english_sense}`

Verdict rule: not an English sense -> bad; unlicensed referent shift -> bad
(licensed = the clue actually carries a '?' AND the substitution turn judged the
shift to be the marked stretch, reading fairly); any other unlicensed shift or
failing qualifier -> fixable; else bankable. Padding is ADVISORY only (rung-2
batch A: the isolated economy turn, blind to taste by design, prosecutes the
very words that earn the clue its basis — "Stomach-turning", "often", "that
might be thrown"; gating on it traded four Fable accepts for three kills the
other turns mostly cover). Padding entries are reported in `advisories` for the
log, never in the verdict.

Installed via battery's `CONFIRM_STAGE` hook. Battery-only for now: the dict
this stage returns has no `difficulty`/`basis` fields, so production wiring
would need a difficulty source (the screen already assigns one).
"""

import re

import pipeline_local

_PANEL_PREAMBLE = """\
You are one editor on the final verification panel for an American-style
crossword clue bank. A clue reaches the panel only after an editorial
screen has made the taste call. You check EXACTLY ONE thing; other
editors handle every other check, and the verdict is assembled outside
this conversation. The costly error is waving a real flaw through.
"""

_SUBSTITUTION_SYSTEM = (
  _PANEL_PREAMBLE
  + """
Your check — substitution: the clue could replace the answer in a
sentence, with part of speech, tense, number, register, and referent
all holding. Choose a sentence where the answer stands alone, so the
definition swaps in without duplicating the sentence's own words.

A shift must be visible in the pair of sentences you write — when the
clue's definition reads naturally in the answer's place, the shift is
"none". When the clue carries a '?', also judge whether the shift you
found is exactly the stretched, figurative, or metonymic definition
the ? marks, and whether that figurative reading still substitutes
fairly. Report that judgment in its own field; report the literal
shift itself regardless.

Calibration examples:
- "One who delivers your letters" -> MAIL: "She sorted the mail." ->
  "She sorted the one who delivers your letters." — the sentences no
  longer describe the same thing: shift "referent". The clue defines
  the mail CARRIER, not the answer itself.
- "Nature's refrigerator?" -> CAVE: "We stored the cheese in a cave."
  -> "We stored the cheese in nature's refrigerator." — shift
  "referent", and the shift IS the marked stretch: the ? declares the
  metaphor, and the metaphor substitutes fairly.
- "Current affairs?" -> EELS: "The eels swam upstream." -> "The
  current affairs swam upstream." — shift "referent", and the shift is
  NOT the marked stretch: "affairs" defines nothing about eels, so no
  figurative reading substitutes fairly."""
)

_SUBSTITUTION_PROMPT = (
  'Check substitution for this one clue. Fill the fields in order: in '
  '"sentence_with_answer", write one natural sentence where the answer '
  'stands alone in the clued sense. In "sentence_with_clue", rewrite '
  "that exact sentence with the clue's definition in the answer's "
  'place. In "analysis", compare the two sentences — say what holds '
  'and what shifts, and for a ?-marked clue whether the shift is the '
  'marked stretch reading fairly. Then commit the last two fields.\n\n'
)

_SUBSTITUTION_SCHEMA = {
  'type': 'object',
  'properties': {
    'sentence_with_answer': {'type': 'string'},
    'sentence_with_clue': {'type': 'string'},
    'analysis': {'type': 'string'},
    'shift': {
      'type': 'string',
      'enum': [
        'none',
        'part_of_speech',
        'tense',
        'number',
        'register',
        'referent',
      ],
    },
    'shift_is_the_marked_stretch': {'type': 'boolean'},
  },
  'required': [
    'sentence_with_answer',
    'sentence_with_clue',
    'analysis',
    'shift',
    'shift_is_the_marked_stretch',
  ],
}

_TRUTH_SYSTEM = (
  _PANEL_PREAMBLE
  + """
Your check — literal truth: test every qualifier, comparative, and
factual claim in the clue against the fact, one by one. A modifier
that overclaims or falsely implies is a failing qualifier — however
charming the surface. You test truth, not uniqueness: a true clue
that also fits other answers is not flawed — cross-checking is the
solver's job, and a clue that forces it is doing its work.
For a '?'-marked clue, test the figurative reading the ? declares: a
marked metaphor is true when the metaphor holds.

Calibration examples:
- "The fastest land animal" -> GAZELLE: failing — "fastest" is false;
  that title belongs to the cheetah.
- "A primary color" -> BLUE: no failing qualifiers — true as stated;
  that red and yellow also fit is the solver's cross-checking work,
  not a flaw.
- "Nature's refrigerator?" -> CAVE: no failing qualifiers — the marked
  metaphor holds; caves genuinely keep things cold."""
)

_TRUTH_PROMPT = (
  'Check literal truth for this one clue. In "analysis", test each '
  'qualifier and factual claim one by one. Then list every failing '
  'qualifier — quote the failing words from the clue and name the '
  'failure in a few words. An empty list means every claim holds.\n\n'
)

_TRUTH_SCHEMA = {
  'type': 'object',
  'properties': {
    'analysis': {'type': 'string'},
    'failing_qualifiers': {'type': 'array', 'items': {'type': 'string'}},
  },
  'required': ['analysis', 'failing_qualifiers'],
}

_ECONOMY_SYSTEM = (
  _PANEL_PREAMBLE
  + """
Your check — economy: apply a deletion test to each meaning-carrying
word. If dropping a word leaves the definition just as complete and
fair, that word is padding — name it even when the surface reads
smoothly. Grammatical connective tissue the phrasing needs (articles,
bare prepositions) is not padding; judge the words that carry meaning.

Calibration examples:
- "Night watchman on patrol" -> GUARD: "on patrol" is padding —
  "Night watchman" carries the whole definition.
- "Frozen rain" -> SLEET: no padding — dropping either word breaks
  the definition."""
)

_ECONOMY_PROMPT = (
  'Check economy for this one clue. In "analysis", run the deletion '
  'test word by word. Then list every padding word or phrase, quoting '
  "the clue's own words. An empty list means every word earns its "
  'place.\n\n'
)

_ECONOMY_SCHEMA = {
  'type': 'object',
  'properties': {
    'analysis': {'type': 'string'},
    'padding_words': {'type': 'array', 'items': {'type': 'string'}},
  },
  'required': ['analysis', 'padding_words'],
}

_SENSE_SYSTEM = (
  _PANEL_PREAMBLE
  + """
Your check — sense ownership: the clued sense must be an English sense
of the answer string. A secondary or archaic sense is fully
legitimate; for a name, a famous bearer or a shared English word both
count. A homograph in another language is not a definition, and a
sense that lives only inside an idiom does not belong to the answer
alone.

Calibration examples:
- "You, old-style" -> THOU: owned — archaic senses count.
- "Born to Die singer" -> LANA: owned — a famous bearer is a
  legitimate definition for a name answer.
- "Unwanted gift" -> ELEPHANT: not owned — the sense lives only
  inside the idiom WHITE ELEPHANT.
- "Bread, in Bordeaux" -> PAIN: not owned — the clued sense is
  French; it is not an English sense of the string PAIN."""
)

_SENSE_PROMPT = (
  'Check sense ownership for this one clue. In "analysis", name the '
  'sense the clue uses and say whether English owns it for this '
  'answer string. Then commit the field.\n\n'
)

_SENSE_SCHEMA = {
  'type': 'object',
  'properties': {
    'analysis': {'type': 'string'},
    'is_english_sense': {'type': 'boolean'},
  },
  'required': ['analysis', 'is_english_sense'],
}

_WORD_PATTERN = re.compile(r"[a-z']+")
_ARTICLES = {'a', 'an', 'the'}


def _padding_flaws(clue, padding_words):
  """Padding entries that survive the article carve-out.

  The deletion test flags bare articles ('A full lineup...' -> 'A'); treating
  those as flaws killed Fable accepts when the carve-out lived in prompt text
  (padding v1). Keep an entry only if it quotes at least one non-article word
  that actually appears in the clue — this also drops paraphrased entries that
  quote nothing.
  """
  clue_words = set(_WORD_PATTERN.findall(clue.lower()))
  kept = []
  for entry in padding_words:
    entry_words = _WORD_PATTERN.findall(entry.lower())
    if any(
      word in clue_words and word not in _ARTICLES for word in entry_words
    ):
      kept.append(entry)
  return kept


def _verdict_from_turns(clue, substitution, truth, economy, sense):
  """Code-side verdict: the aggregation the model is never asked to do.

  Returns `(verdict, flaws)`. The ?-license is a code rule — v3 showed the model
  cannot hold that rule as text without it bleeding into every other check.
  """
  if not sense['is_english_sense']:
    return 'bad', ['sense: not an English sense of the answer']
  flaws = []
  shift = substitution['shift']
  is_licensed = '?' in clue and substitution['shift_is_the_marked_stretch']
  if shift != 'none' and not is_licensed:
    if shift == 'referent':
      return 'bad', ['substitution: unlicensed referent shift']
    flaws.append(f'substitution: unlicensed {shift} shift')
  flaws.extend(
    f'truth: {qualifier}' for qualifier in truth['failing_qualifiers']
  )
  if flaws:
    return 'fixable', flaws
  return 'bankable', []


def _multi_turn_confirm(judge_turn, word, clue):
  """Run the four turns and assemble the verdict dict battery expects.

  All four turns always run (uniform cache, full per-turn diagnostics in the
  battery log) — no short-circuit on an early kill.
  """
  del word  # bound into judge_turn already; part of the hook contract
  substitution = judge_turn(
    'confirm.substitution',
    _SUBSTITUTION_SYSTEM,
    _SUBSTITUTION_PROMPT,
    _SUBSTITUTION_SCHEMA,
  )
  truth = judge_turn(
    'confirm.truth', _TRUTH_SYSTEM, _TRUTH_PROMPT, _TRUTH_SCHEMA
  )
  economy = judge_turn(
    'confirm.economy', _ECONOMY_SYSTEM, _ECONOMY_PROMPT, _ECONOMY_SCHEMA
  )
  sense = judge_turn(
    'confirm.sense', _SENSE_SYSTEM, _SENSE_PROMPT, _SENSE_SCHEMA
  )
  verdict, flaws = _verdict_from_turns(
    clue, substitution, truth, economy, sense
  )
  return {
    'verdict': verdict,
    'flaws': flaws,
    'advisories': [
      f'economy: {padding}'
      for padding in _padding_flaws(clue, economy['padding_words'])
    ],
    'turns': {
      'substitution': substitution,
      'truth': truth,
      'economy': economy,
      'sense': sense,
    },
  }


assert not hasattr(pipeline_local, 'CONFIRM_STAGE'), 'hook already installed'
pipeline_local.CONFIRM_STAGE = _multi_turn_confirm
