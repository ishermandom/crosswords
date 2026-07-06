# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Multi-turn confirm v2: calibrated semantics from the 2026-07-05 rulings.

Four changes over confirm_multiturn_v1, each anchored in a user calibration on
the expanded eval set (ledger: calibrations #6/#7):

1. Substitution asks WHAT THE DEFINITION POINTS AT instead of classifying a
   shift. v1's forced shift enum made the judge label every figurative framing a
   referent shift (26B: 21/21 accept kills; 31B: the personification family),
   and its ?-carve-out both over-licensed bare metonymy ("Six points?") and was
   the only thing saving consequence definitions ("Reason to spike the ball").
   v2: metaphor, hyperbole, role/consequence framing, and implicit-unit quantity
   equations of the RIGHT thing all point at the answer; only a definition that
   literally describes a DIFFERENT thing (the bow, not the violin) is a
   substitution failure — and a '?' never repairs that.
2. Truth gains the hyperbole rule: a figurative claim passes only if it encodes
   something true of the answer; comic exaggeration with no factual core fails
   unless a '?' marks the stretch.
3. Economy becomes a calibrated gate (was advisory-only). The line drawn by the
   user's rulings: inherent-property words are load-bearing hints because the
   answer is hidden ("slowly" in a rust clue earns its place); charming
   scene-setting is legal; redundant restatement and dead-weight tails are
   bloat.
4. Sense ownership splits into usability (English sense, or a signposted foreign
   word a typical English speaker knows — MERCI grade) and common knowledge
   (archaic/specialist senses feel random however believable).

Verdict rule: unusable sense -> bad; defines a different thing -> bad; grammar
mismatch, failing truth claim, validated bloat, or obscure sense -> fixable;
else bankable.

Installed via battery's `CONFIRM_STAGE` hook; battery-only, like v1.
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
Your check — reference: does the clue's definition pick out the answer
itself, or does it literally describe some other thing? Write the
sentence pair first; the judgment must be visible in it.

A definition still points at the answer when it works through metaphor
or personification, playful hyperbole, the answer's role or
consequence ("Excuse for a snow day" -> BLIZZARD), or a bare number
equated with a quantity whose unit is obvious ("Retirement age, often"
-> SIXTYFIVE). For a number answer, a plural counted noun is fine too
— a clue shaped like "Keys on a grand piano" points at the count
itself, not at the keys; that is not a grammar mismatch. None of
those are reference failures — flag "other_object" only when the
words, read fairly, describe a different specific thing, and name
that thing. For quantities, apply the value test: the equation is
fair only when the named quantity's own value IS the number. A bet,
prize, or event merely associated with the number — one whose own
value is something else — is a different thing.

Separately report a grammar mismatch: right referent, but the
definition cannot replace the answer in a sentence (part of speech,
tense, or number breaks).

Calibration examples:
- "One who delivers your letters" -> MAIL: "She sorted the mail." ->
  "She sorted the one who delivers your letters." — describes the
  CARRIER, a different thing: points_at "other_object", name "mail
  carrier".
- "Bristled stick for scrubbing molars" -> TOOTHPASTE: the words
  describe the brush, not the paste: points_at "other_object", name
  "toothbrush".
- "Winter's white blanket" -> SNOW: metaphor, but every word picks out
  the answer itself: points_at "answer".
- "Excuse for a snow day" -> BLIZZARD: defines by consequence; the
  thing your excuse names IS the answer: points_at "answer".
- "Runs fast" -> SPRINTER: the right thing, but a verb phrase cannot
  stand in for the noun: points_at "grammar_mismatch"."""
)

_SUBSTITUTION_PROMPT = (
  'Check reference for this one clue. Fill the fields in order: in '
  '"sentence_with_answer", write one natural sentence where the answer '
  'stands alone in the clued sense. In "sentence_with_clue", rewrite '
  "that exact sentence with the clue's definition in the answer's "
  'place. In "analysis", compare the two sentences and say whether the '
  'definition picks out the answer itself — through metaphor, role, or '
  'implicit units if need be — or literally describes a different '
  'thing. Then commit the last two fields ("other_object_name" is the '
  'empty string unless points_at is "other_object").\n\n'
)

_SUBSTITUTION_SCHEMA = {
  'type': 'object',
  'properties': {
    'sentence_with_answer': {'type': 'string'},
    'sentence_with_clue': {'type': 'string'},
    'analysis': {'type': 'string'},
    'points_at': {
      'type': 'string',
      'enum': ['answer', 'other_object', 'grammar_mismatch'],
    },
    'other_object_name': {'type': 'string'},
  },
  'required': [
    'sentence_with_answer',
    'sentence_with_clue',
    'analysis',
    'points_at',
    'other_object_name',
  ],
}

_TRUTH_SYSTEM = (
  _PANEL_PREAMBLE
  + """
Your check — literal truth: test every qualifier, comparative, and
factual claim in the clue against the fact, one by one. A modifier
that overclaims or falsely implies is a failing claim — however
charming the surface. You test truth, not uniqueness: a true clue
that also fits other answers is not flawed — cross-checking is the
solver's job.

Figurative language is judged by its factual core: a metaphor or
exaggeration passes when it encodes something true of the answer, and
fails when no fair reading of it is true. A '?' at the end of the
clue licenses a stretch that cannot be taken as fact; without the
mark, such a claim fails.

Calibration examples:
- "The fastest land animal" -> GAZELLE: failing — "fastest" is false;
  that title belongs to the cheetah.
- "A primary color" -> BLUE: no failing claims — true as stated; that
  red and yellow also fit is the solver's cross-checking work.
- "Pest that treats your blood as an open bar" -> MOSQUITO: no
  failing claims — the exaggeration encodes the true feeding habit.
- "Appliance that turns the kitchen into a battlefield" -> BLENDER:
  failing — "battlefield" has no true reading and no '?' marks the
  stretch; loudness alone does not underwrite it."""
)

_TRUTH_PROMPT = (
  'Check literal truth for this one clue. In "analysis", test each '
  'qualifier and factual claim one by one, judging figurative wording '
  'by its factual core. Then list every failing claim — quote the '
  'failing words from the clue and name the failure in a few words. '
  'An empty list means every claim holds.\n\n'
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
Your check — economy: does every meaning-carrying word earn its keep?
Run the deletion test on clauses and phrases, never on single words.
If deleting a phrase costs the clue its point — its joke, its
paradox, its poetry, or the surprising specific that makes a fact
worth banking — the phrase IS the point and earns its place. If the
deletion costs only a literal detail, the phrase is bloat, however
true or familiar the detail.

Two rules for modifiers. A modifier that REPEATS content already in
the clue is restatement — bloat at any length ("hot" before "heat";
"standing guard" after "sentinel"). A modifier adding sensory
texture or scene — a color, a season, a place on the counter — is
charm, never bloat: the answer is hidden, and texture is how it
emerges.

Calibration examples:
- "Feathered alarm clock with no snooze button" -> ROOSTER: no bloat
  — delete "with no snooze button" and the joke dies; the tail is the
  point.
- "Green fuzz slowly claiming the forgotten loaf" -> MOLD: no bloat —
  "slowly" and "forgotten" are texture; the scene is the charm.
- "Crackling tower of driftwood lighting the beach at midnight" ->
  BONFIRE: no bloat — the scene is poetry elevating a plain gloss.
- "Armored sentinel standing guard over the castle" -> KNIGHT:
  bloated — "standing guard" restates "sentinel".
- "Sticky glue that adheres" -> PASTE: bloated — "that adheres"
  repeats what "Sticky" and "glue" already say.
- "Four-legged seat pulled up to the bar and spun after last call" ->
  STOOL: bloated — the definition and its character are complete at
  "the bar"; the spin is a true, even amusing detail, but the point
  was already made.
- "Night watchman on patrol" -> GUARD: bloated — "on patrol" adds
  neither definition nor charm.
- "Frozen rain" -> SLEET: no bloat — dropping either word breaks the
  definition."""
)

_ECONOMY_PROMPT = (
  'Check economy for this one clue. In "analysis", run the deletion '
  'test on each suspect phrase: name what the clue loses without it — '
  'its point, or only a literal detail. In "bloat_evidence", quote '
  'every phrase whose deletion costs only a detail, using the '
  "clue's own words (empty list if none). Then commit "
  '"is_bloated".\n\n'
)

_ECONOMY_SCHEMA = {
  'type': 'object',
  'properties': {
    'analysis': {'type': 'string'},
    'bloat_evidence': {'type': 'array', 'items': {'type': 'string'}},
    'is_bloated': {'type': 'boolean'},
  },
  'required': ['analysis', 'bloat_evidence', 'is_bloated'],
}

_SENSE_SYSTEM = (
  _PANEL_PREAMBLE
  + """
Your check — sense ownership, two judgments.

First, usability: the clued sense must be an English sense of the
answer string, OR a foreign word that the clue signposts (a place or
language tag) AND that a typical English speaker recognizes. A rare
foreign homograph is not usable however clearly it is flagged. A
sense that lives only inside an idiom is not usable either.

Second, common knowledge: is the sense one most solvers actually
know? An archaic or specialist sense can be genuinely English yet so
obscure the clue feels random.

Calibration examples:
- "You, old-style" -> THOU: usable and commonly known — a famous
  archaism.
- "Born to Die singer" -> LANA: usable and commonly known — a famous
  bearer defines a name answer.
- "Thanks, in Paris" -> MERCI: usable — signposted, and recognized by
  a typical English speaker.
- "Eleven, in Madrid" -> ONCE: not usable — a Spanish homograph most
  English speakers don't know as "eleven"; the signpost doesn't help.
- "Unwanted gift" -> ELEPHANT: not usable — the sense lives only
  inside the idiom WHITE ELEPHANT.
- "Sky, in old verse" -> WELKIN: usable but NOT commonly known — real
  English, yet most solvers would find it random."""
)

_SENSE_PROMPT = (
  'Check sense ownership for this one clue. In "analysis", name the '
  'sense the clue uses, say whether it is usable (an English sense, or '
  'a signposted and widely recognized foreign word), and whether most '
  'solvers know it. Then commit both fields.\n\n'
)

_SENSE_SCHEMA = {
  'type': 'object',
  'properties': {
    'analysis': {'type': 'string'},
    'is_usable_sense': {'type': 'boolean'},
    'is_commonly_known': {'type': 'boolean'},
  },
  'required': ['analysis', 'is_usable_sense', 'is_commonly_known'],
}

_WORD_PATTERN = re.compile(r"[a-z']+")
_ARTICLES = {'a', 'an', 'the'}


def _validated_quotes(clue, entries):
  """Entries that quote real, non-article clue words.

  Same mechanic as v1's `_padding_flaws`: an entry counts only if it quotes at
  least one non-article word actually present in the clue, which drops both
  bare-article flags and paraphrases that quote nothing.
  """
  clue_words = set(_WORD_PATTERN.findall(clue.lower()))
  kept = []
  for entry in entries:
    entry_words = _WORD_PATTERN.findall(entry.lower())
    if any(
      word in clue_words and word not in _ARTICLES for word in entry_words
    ):
      kept.append(entry)
  return kept


def _verdict_from_turns(clue, substitution, truth, economy, sense):
  """Code-side verdict: the aggregation the model is never asked to do.

  Returns `(verdict, flaws, advisories)`. There is no ?-license rule left in
  code: wordplay clues point at the answer through their true second reading
  (substitution), and a '?' licenses a truth stretch inside the truth turn's own
  rule — a wrong-object definition is unrepairable either way.
  """
  if not sense['is_usable_sense']:
    return 'bad', ['sense: not a usable sense of the answer'], []
  if substitution['points_at'] == 'other_object':
    name = substitution['other_object_name'] or 'an unnamed other thing'
    return 'bad', [f'substitution: defines a different thing ({name})'], []
  flaws = []
  advisories = []
  if substitution['points_at'] == 'grammar_mismatch':
    flaws.append('substitution: grammar mismatch')
  # Truth entries get the same quote validation as economy evidence: rung 1
  # killed an accept on the bare-article flag `['The']`.
  flaws.extend(
    f'truth: {qualifier}'
    for qualifier in _validated_quotes(clue, truth['failing_qualifiers'])
  )
  if not sense['is_commonly_known']:
    flaws.append('sense: too obscure for a typical solver')
  return ('fixable', flaws, advisories) if flaws else ('bankable', [], [])


def _economy_verdict(clue, economy, verdict, flaws, advisories):
  """Fold the economy gate into the verdict.

  Gates only when the turn commits `is_bloated` AND at least one evidence entry
  survives quoting validation; evidence without the commit (or vice versa)
  demotes to advisory, so a hedging turn never kills alone.
  """
  validated = _validated_quotes(clue, economy['bloat_evidence'])
  if economy['is_bloated'] and validated:
    flaws = flaws + [f'economy: {entry}' for entry in validated]
    return 'fixable' if verdict == 'bankable' else verdict, flaws, advisories
  if validated or economy['is_bloated']:
    advisories = advisories + [
      f'economy (advisory): {entry}' for entry in (validated or ['(no quote)'])
    ]
  return verdict, flaws, advisories


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
  verdict, flaws, advisories = _verdict_from_turns(
    clue, substitution, truth, economy, sense
  )
  if verdict != 'bad':
    verdict, flaws, advisories = _economy_verdict(
      clue, economy, verdict, flaws, advisories
    )
  return {
    'verdict': verdict,
    'flaws': flaws,
    'advisories': advisories,
    'turns': {
      'substitution': substitution,
      'truth': truth,
      'economy': economy,
      'sense': sense,
    },
  }


assert not hasattr(pipeline_local, 'CONFIRM_STAGE'), 'hook already installed'
pipeline_local.CONFIRM_STAGE = _multi_turn_confirm
