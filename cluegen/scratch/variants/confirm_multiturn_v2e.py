# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Multi-turn confirm v2e: v2 with the economy check as a 3-wording panel.

Idea-12 rungs 1-4 showed that single-wording economy judgments carry ~2-3 rows
of per-wording jitter on borderline taste calls: each rewording fixed its
targets and rotated fresh false verdicts onto rows every other wording got right
(FOG died only under try 3, SOCKS/YAWN only under try 4, GARLIC/ ESCALATOR only
under try 2). A majority vote across the three viable wordings (tries 1, 3, 4)
scored every economy-sensitive probe row correctly except UMBRELLA (the accepted
taste miss) — the jitter integrates out.

So v2e runs the economy check three times, once per wording, and gates in code
only on a UNANIMOUS panel of (is_bloated AND quote-validated evidence). Dissent
leaves the clue unbloated; minority votes are logged as advisories.

Panel composition (frozen after exhaustive offline evaluation of all cached
compositions and thresholds on the full gentune survivors): the deletion-test
siblings t3 and t4 plus the trimming-editor framing, unanimity required — 19/20
accepts and 8/9 kills at the confirm stage, the Pareto front of every rule
tried; the strict members carry the kills and the editor's dissent protects
prize-fact specifics (KETCHUP "in the 1830s"). Known residuals: PILLOW (3 of 4
wordings vote its tail bloated) and UMBRELLA (accepted taste miss). Member texts
are byte-identical to their rungs, so their calls replay from cache, as do
substitution, truth, and sense (v2 at 9f2eb99).

Production cost: +2 economy calls per clue reaching confirm.
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
that thing. For a number answer, apply the value test to the thing
the clue names: an amount, duration, age, score, or prize whose value
IS the number points at the answer — a jackpot of a million IS a
million; an age of seventy IS seventy. A thing whose own value is
something else is a different thing, however strongly the number is
associated with it. For an event or deed answer, the reverse also
fails: an event is never its bare point value — a clue reading "Six
points" describes the score, not the scoring play that earns it; flag
"other_object" and name the value.

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

_ECONOMY_SYSTEM_T3 = (
  _PANEL_PREAMBLE
  + """
Your check — economy: does every meaning-carrying word earn its keep?
Judge a suspect phrase by deleting it and asking what the clue LOSES.
If the deletion costs the clue its point — its joke, its paradox, its
poetry, or the surprising specific that makes a fact worth banking —
the phrase IS the point and earns its place. If the deletion costs
only a literal detail, the phrase is bloat, however true or familiar
the detail. A single word naming an inherent property ("slowly" for
something that always acts slowly) is a hint that helps the hidden
answer emerge — never flag a lone modifier as a surplus fact.

Bloat's common shapes: words that restate what another word already
said; dead tails that neither define nor delight; and the trailing
fact appended after the clue's point has already been made.

Calibration examples:
- "Feathered alarm clock with no snooze button" -> ROOSTER: no bloat
  — delete "with no snooze button" and the joke dies; the tail is the
  point.
- "Green fuzz slowly claiming the forgotten loaf" -> MOLD: no bloat —
  "slowly" is an inherent-property hint, and the scene is the charm.
- "Crackling tower of driftwood lighting the beach at midnight" ->
  BONFIRE: no bloat — the scene is poetry elevating a plain gloss.
- "Armored sentinel standing guard over the castle" -> KNIGHT:
  bloated — "standing guard" restates "sentinel".
- "Four-legged seat pulled up to the bar and spun after last call" ->
  STOOL: bloated — the definition and its character are complete at
  "the bar"; the spin is a true, even amusing detail, but the point
  was already made.
- "Night watchman on patrol" -> GUARD: bloated — "on patrol" adds
  neither definition nor charm.
- "Frozen rain" -> SLEET: no bloat — dropping either word breaks the
  definition."""
)

_ECONOMY_PROMPT_T3 = (
  'Check economy for this one clue. In "analysis", run the deletion '
  'test on each suspect phrase: name what the clue loses without it — '
  'its point, or only a literal detail. In "bloat_evidence", quote '
  'every phrase whose deletion costs only a detail, using the '
  "clue's own words (empty list if none). Then commit "
  '"is_bloated".\n\n'
)

_ECONOMY_SYSTEM_T4 = (
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

_ECONOMY_PROMPT_T4 = (
  'Check economy for this one clue. In "analysis", run the deletion '
  'test on each suspect phrase: name what the clue loses without it — '
  'its point, or only a literal detail. In "bloat_evidence", quote '
  'every phrase whose deletion costs only a detail, using the '
  "clue's own words (empty list if none). Then commit "
  '"is_bloated".\n\n'
)

_ECONOMY_SYSTEM_ED = (
  _PANEL_PREAMBLE
  + """
Your check — economy, as the trimming editor: the clue is going to
print and column inches are precious. Mark exactly the words a
veteran editor would cut, knowing the cut must cost the solver
nothing: neither definition, nor fairness, nor the clue's charm.

An editor never cuts the point — the joke, the paradox, the poetry,
or the specific that gives a fact its teeth (a date, a place, a
number that makes the claim checkable). An editor does cut
redundancy, dead connective tails, and details no solver needs.

Calibration examples:
- "Wheeled cart pushed along supermarket aisles while shopping" ->
  TROLLEY: cut "while shopping" — the aisles already said it.
- "Sour green citrus with acidic juice" -> LIME: cut "with acidic
  juice" — "Sour" said it.
- "Grandfather's pocket ticker, wound each night" -> WATCH: nothing
  to cut — the nightly winding is period charm that places the
  object.
- "Patient beaver damming the creek by moonlight" -> BEAVER: nothing
  to cut — patience and moonlight are the picture, and the picture is
  the point."""
)

_ECONOMY_PROMPT_ED = (
  'Trim this one clue. In "analysis", go through it as the editor: '
  'name what each candidate cut would cost the solver. In '
  '"bloat_evidence", quote exactly the words you would cut, using '
  "the clue's own words (empty list if you would print it as is). "
  'Then commit "is_bloated" (true only if you would actually cut '
  'something).\n\n'
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


def _verdict_from_turns(clue, substitution, truth, sense):
  """Code-side verdict before the economy panel folds in.

  Returns `(verdict, flaws, advisories)`; identical to v2's rule minus the
  economy handling, which `_economy_panel_verdict` applies afterwards.
  """
  if not sense['is_usable_sense']:
    return 'bad', ['sense: not a usable sense of the answer'], []
  if substitution['points_at'] == 'other_object':
    name = substitution['other_object_name'] or 'an unnamed other thing'
    return 'bad', [f'substitution: defines a different thing ({name})'], []
  flaws = []
  if substitution['points_at'] == 'grammar_mismatch':
    flaws.append('substitution: grammar mismatch')
  # Truth entries get the same quote validation as economy evidence (rung 1
  # killed an accept on the bare-article flag `['The']`).
  flaws.extend(
    f'truth: {qualifier}'
    for qualifier in _validated_quotes(clue, truth['failing_qualifiers'])
  )
  if not sense['is_commonly_known']:
    flaws.append('sense: too obscure for a typical solver')
  return ('fixable', flaws, []) if flaws else ('bankable', [], [])


def _economy_panel_verdict(clue, panel, verdict, flaws, advisories):
  """Fold the 3-wording economy panel into the verdict by majority.

  A wording votes to gate when it commits `is_bloated` AND at least one evidence
  entry survives quote validation. Two votes gate (flaws carry the union of the
  gating wordings' validated evidence); a lone vote is logged as an advisory.
  """
  gate_votes = 0
  evidence_union = []
  for economy in panel:
    validated = _validated_quotes(clue, economy['bloat_evidence'])
    if economy['is_bloated'] and validated:
      gate_votes += 1
      evidence_union.extend(
        entry for entry in validated if entry not in evidence_union
      )
  if gate_votes == len(panel):
    flaws = flaws + [f'economy: {entry}' for entry in evidence_union]
    return 'fixable' if verdict == 'bankable' else verdict, flaws, advisories
  if gate_votes:
    advisories = advisories + [
      f'economy (minority): {entry}' for entry in evidence_union
    ]
  return verdict, flaws, advisories


_ECONOMY_PANEL = (
  (_ECONOMY_SYSTEM_T3, _ECONOMY_PROMPT_T3),
  (_ECONOMY_SYSTEM_T4, _ECONOMY_PROMPT_T4),
  (_ECONOMY_SYSTEM_ED, _ECONOMY_PROMPT_ED),
)


def _multi_turn_confirm(judge_turn, word, clue):
  """Run substitution/truth/sense plus the economy panel; assemble verdict.

  All turns always run (uniform cache, full per-turn diagnostics) — no
  short-circuit on an early kill.
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
  panel = [
    judge_turn('confirm.economy', system, prompt, _ECONOMY_SCHEMA)
    for system, prompt in _ECONOMY_PANEL
  ]
  sense = judge_turn(
    'confirm.sense', _SENSE_SYSTEM, _SENSE_PROMPT, _SENSE_SCHEMA
  )
  verdict, flaws, advisories = _verdict_from_turns(
    clue, substitution, truth, sense
  )
  if verdict != 'bad':
    verdict, flaws, advisories = _economy_panel_verdict(
      clue, panel, verdict, flaws, advisories
    )
  return {
    'verdict': verdict,
    'flaws': flaws,
    'advisories': advisories,
    'turns': {
      'substitution': substitution,
      'truth': truth,
      'economy_t3': panel[0],
      'economy_t4': panel[1],
      'economy_ed': panel[2],
      'sense': sense,
    },
  }


assert not hasattr(pipeline_local, 'CONFIRM_STAGE'), 'hook already installed'
pipeline_local.CONFIRM_STAGE = _multi_turn_confirm
