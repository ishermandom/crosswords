# CLUE_SPEC.md — Mixed-Style Clue Bank Generation Spec

This specification defines the standard for a crossword clue bank for
automatically generated acrostic-style puzzles. Each answer word gets SEVERAL
original clues: by default **2 American-style and 2 cryptic-style** (counts
adjustable via the batch prompt). Target solvers enjoy both styles mixed in one
puzzle.

Global rules:

- Clues for the same word must take genuinely different angles — different
  misdirection domains or mechanisms, never paraphrases of each other.
- Every clue must be self-contained (acrostic clues can't cross-reference other
  entries or "see 17-Across").
- If a word resists fair treatment in one style, skip that style honestly (see
  Output Schema). A skip is success; a forced bad clue is failure.

---

# PART A — American-style (NYT-style) clues

## A1. The contract

A single deceptive definition or description. No wordplay grammar — the craft is
misdirection within a natural surface.

## A2. Craft invariants (apply at EVERY difficulty)

- **Accuracy.** The clue could substitute for the answer in a sentence: matching
  part of speech, tense, number, and register. "Sprinted" cannot clue RUN.
- **Economy.** Every word earns its place; remove anything removable.
- **Natural surface.** Reads like something a person would actually say or write
  — even when the clue is perfectly straight.
- **Liveliness.** Prefer the vivid, specific angle over the dictionary-flat one:
  "Like a snowbird's November flight" beats "Toward the south" at identical
  difficulty. Easy ≠ dull — easy clues are crafted through freshness and fair
  signposting, not deception.
- Cleverness that needs a paragraph to justify is a craft failure.

## A2b. The difficulty dial

Difficulty = how much work the solver does to bridge clue → answer. Misdirection
is one tool at the hard end of this dial, not the essence of craft.

- **Directness** (easy): one dominant reading, clearly signposted.
- **Ambiguity breadth** (medium): a common word in a less-first sense; a broad
  definition with several plausible candidates; mild trivia angles.
- **Active misdirection** (hard): the surface confidently suggests a wrong
  reading via polysemy ("Round number?" → golf), part-of-speech flips,
  real-world convention ("Which way the north wind blows"), or register shifts
  ("One who might cry uncle?" — idiom turns literal vocative). The aha must be
  fair in retrospect — punish confidence, not knowledge. The deadliest traps
  make a _wrong answer fit_ until checked.
- **Question mark conventions:** signals wordplay, stretched definition, or
  definition-by-example. Use honestly; its absence promises straightness.
- **No trivia-lookup-only clues at hard difficulty.** Hard means twisted, not
  obscure.

## A3. Difficulty calibration (tag each clue)

- `easy` (Mon–Tue): direct, signposted. "Like a snowbird's November flight."
- `medium` (Wed): one mild twist or a misdirecting word.
- `hard` (Thu–Sat): full misdirection; surface confidently suggests a wrong
  answer.

Default mix per word: one `medium`, one `hard`.

## A4. Exemplars (spanning the dial)

The same word at three difficulties — SOUTHWARD — shows the dial in action:

1. _Like a snowbird's November flight_ (easy) — direct, but vivid and
   signposted; craft without deception.
2. _Down, to a cartographer?_ (medium) — "down" in a less-first sense (map
   orientation); the ? flags the stretch.
3. _Which way the north wind blows_ (hard) — NORTHWARD fits and has the same
   length; winds are named for their origin. Convention-based trap.

Additional medium:

4. **EIGHTEEN** — _Threshold for the franchise_ (medium) — "franchise" in its
   voting sense rather than the McDonald's-first reading; broad but fair.

Additional hard:

5. **NEPHEW** — _One who might cry uncle?_ (hard) — idiom "cry uncle"
   (surrender) flips to literal vocative.
6. **EIGHTEEN** — _Round number?_ (hard) — "round" flips adjective→noun (round
   of golf). Two words, total misdirection.

---

# PART B — Cryptic-style clues

## B1. The contract

Every clue must support exactly two readings:

1. **Surface reading** — a natural, coherent phrase that evokes a scene and
   points _away_ from the answer.
2. **Cryptic reading** — a grammatically exact parse:
   `[definition] + [wordplay]` or `[wordplay] + [definition]`, definition at one
   end.

Every word serves the cryptic reading (definition, fodder, indicator, or
permitted connector). Surface-only padding is a craft failure.

Difficulty target: mid-week broadsheet (Guardian/Times weekday) — deceptive,
strictly fair.

## B2. Permitted mechanisms

anagram · charade · container/insertion · hidden word · reversal · homophone ·
deletion · double definition · &lit (rare; only when airtight)

Combination clues are fine if each step has its own indicator and the chain
stays short (≤2 mechanisms).

## B3. Fairness rules (hard constraints)

- **Definition at one end.** Matches the answer's part of speech;
  dictionary-defensible.
- **No indirect anagrams.** Fodder appears verbatim in the clue.
- **Standard indicators only.** Anagram: broken, spilled, wild, ruined, cooked,
  confused, out... Hidden: some, partly, in part, held by... Reversal: back,
  returned, reversed, sent back, in retreat, reflected... **Acrostic note:**
  entries have no grid direction, so orientation-dependent reversal indicators
  are invalid — never "going up"/"rising"/"climbing" (vertical) or "westward"
  (across-grid). Homophone: we hear, reportedly, they say... Container: in,
  holding, swallowing, caught in...
- **Letter math must be exact.** Anagram fodder = exact multiset of answer
  letters. Hidden answers = contiguous substring ignoring spaces/punctuation.
  Enumeration matches the answer's word lengths.
- **Abbreviations must be standard** (N = north, R = right/river, ET = alien, ST
  = street/saint...). No stretches.
- **No obscure-on-obscure.** Uncommon answer → transparent wordplay; uncommon
  mechanism → common answer.
- **Capitalization tricks are fair downward only**: lowercasing a proper noun to
  hide it is fair; fake-capitalizing a common word is not.

## B4. Craft rubric

- Strongest move: deception and solution living in the _same domain_ (see ESCAPE
  ROOM exemplar).
- Shorter is better. Surface coherence outranks parse cleverness.
- Question mark signals definition-by-example or a stretched-but-fair reading.
- Prefer fodder whose surface meaning differs sharply from its cryptic function.

## B5. Exemplars (with full parses)

1. **ESCAPE ROOM** — _Where teams get trapped — key, then space (6,4)_ Charade.
   Def: "Where teams get trapped". key = ESCAPE (Esc key); space = ROOM. Surface
   reads as frozen-Microsoft-Teams troubleshooting.
2. **SOUTHWARD** — _Spilled Tudor wash going down, on most maps (9)_ Anagram.
   Def: "going down, on most maps". Fodder TUDOR WASH (exact multiset of
   SOUTHWARD), indicator "spilled".
3. **TRAINEE** — _Shower stuck in tee, for a beginner (7)_ Container. Def:
   "beginner". RAIN ("shower") inside TEE → T(RAIN)EE.
4. **STRESSED** — _Desserts sent back — one's under pressure (8)_ Reversal. Def:
   "under pressure". DESSERTS reversed, indicator "sent back".
5. **EDIT** — _Cut some becalmed items (4)_ Hidden. Def: "cut". Inside
   "becalm**ED IT**ems", indicator "some".
6. **WAIL** — _Cry like a giant of the sea, they say (4)_ Homophone. Def: "cry".
   Sounds like WHALE, indicator "they say".

(Exemplars are teaching aids; chestnuts like STRESSED/DESSERTS are not
submission-worthy — produce original constructions.)

---

# PART C — Output schema

One JSON object per **word**, one per line (JSONL). No prose outside the JSON.

```json
{
  "word": "SOUTHWARD",
  "enumeration": "(9)",
  "clues": [
    {
      "style": "american",
      "difficulty": "hard",
      "clue": "Which way the north wind blows",
      "trap": "NORTHWARD fits; wind-naming convention is the escape",
      "confidence": "high"
    },
    {
      "style": "cryptic",
      "difficulty": "medium",
      "clue": "Spilled Tudor wash going down, on most maps (9)",
      "definition": "going down, on most maps",
      "mechanism": "anagram",
      "anagram_fodder": "Tudor wash",
      "hidden_string": null,
      "parse": "anagram of TUDOR WASH, indicator 'spilled'; def at end",
      "confidence": "high"
    }
  ],
  "skips": [
    { "style": "cryptic", "reason": "only forced/unfair wordplay available" }
  ]
}
```

Field rules:

- `style`: `"american"` or `"cryptic"` — required on every clue. This tag is
  load-bearing: the puzzle assembler filters on it.
- Cryptic clues MUST include `definition`, `mechanism`, `parse`, and — to enable
  mechanical verification — `anagram_fodder` (anagram clues only: exact fodder
  string as it appears in the clue) and `hidden_string` (hidden clues only:
  exact clue substring containing the answer). Null otherwise. Cryptic clue text
  includes enumeration; American clue text does not.
- American clues include `trap`, calibrated to difficulty: for `hard`, one
  sentence naming the active misdirection (judge verifies it functions); for
  `medium`, the mild ambiguity exploited (the less-first sense, the broad
  definition); for `easy`, null — easy clues are judged on invariants and
  liveliness, not deception.
- `confidence`: "high" | "medium" | "low" — honest; "low" routes to judge pass.
- `skips`: array (possibly empty) of per-style skips with reasons.

# PART D — Failure modes: reject and retry if you catch yourself doing these

Both styles:

- Padding words; surfaces no human would write; cleverness needing a paragraph
  to justify; multiple clues for one word that are paraphrases of each other.

American:

- Misdirection by obscurity instead of ambiguity; question mark used as apology;
  trap that doesn't survive a re-read.

Cryptic:

- Definition buried mid-clue or wrong part of speech; indirect anagram; fodder
  letter-count mismatch; wrong enumeration; indicator doing double duty;
  invented indicators; chestnut recycling.
