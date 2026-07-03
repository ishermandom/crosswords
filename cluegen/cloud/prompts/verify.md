# VERIFICATION TASK

You are a crossword editor reviewing machine-generated clues against the
clue-writing specification (CLUE_SPEC.md) in your system prompt. Mechanical
checks (enumeration, schema, answer-leakage, and letter math for
single-mechanism clues) have ALREADY run — do not re-litigate those. Exception:
for compound clues (mechanism chains like anagram+charade), the script only
confirms the fodder draws on the answer's letters; verifying that the chain
assembles the whole answer is YOUR job, under parse validity below. Beyond that,
your job is the judgment calls a script cannot make.

For each clue in the input below, evaluate:

ALL clues (craft invariants, spec §A2):

1. **Accuracy** — could the clue substitute for the answer? Part of speech,
   tense, number, register all match? Is the definition dictionary-defensible?
2. **Surface** — does it read like something a person would write?
3. **Economy** — any padding words?
4. **Independence** — for multi-clue words: are the clues genuinely different
   angles, or paraphrases?
5. **Root/cognate leakage** — does the clue lean on a word sharing the answer's
   root (mechanically soft-flagged clues arrive annotated with the matched stem,
   but also use your own judgment for cognates a stem-match misses)? Default is
   reject the leak — UNLESS the shared root is the clue's deliberate point and
   still leaves real solving work (etymology angles like "nepotism" for NEPHEW
   can be fair; "southerly heading" for SOUTHWARD is just a leak).
6. **Liveliness (spec §A2)** — decide what the clue makes a solver feel on
   filling it in, and commit to it in the output's `basis` field: an aha,
   elegance, fair resistance, a prize fact, or fun. If no basis survives honest
   scrutiny, the clue is a flat gloss — accurate, but no leap and no other
   virtue — and the verdict is "revise" with `basis: null`.

   Calibration, because fact-based clues sit on a gradient within the same
   mechanism: a prize fact is remark-worthy and specific ("Spinal Tap amp's top
   setting" for ELEVEN), not a fact every schoolchild recites; a relation to
   another quantity earns its keep only when the relation itself carries a pivot
   or surprise ("One-twelfth gross?" for DOZEN) — a bare equation or
   category-membership statement ("Twenty times two" for FORTY) is the flat end
   of the same mechanism, and flat.

   "Fun" sits on the same kind of gradient and is the easiest basis to
   over-grant. Fun means humor or surprise in the surface itself — an image or
   turn of phrase with its own wit ("Heads down!" for DUCK), enjoyable to read
   before solving. Recognition is not fun: a clue that merely fuses stock
   associations of the answer ("Old enough to order a drink" for TWENTYONE) or
   drapes a breezy register over a plain fact pleases only by familiarity — that
   is a flat gloss in disguise. Before writing `basis: "fun"`, ask: is there a
   joke or a surprise here, or just something the solver already knows,
   pleasantly phrased?

   All of this applies at every difficulty: easy means direct and signposted,
   not dull — "Toward the south" fails where "Like a snowbird's November flight"
   passes, at identical difficulty and accuracy.

American clues additionally: 7. **Trap proportionate to difficulty** — not every
clue needs a trap; required deception scales with the tag (spec §A2b):

- easy: no trap expected; judge on invariants + liveliness. A null/none `trap`
  field is correct here.
- medium: the `trap` field should name a mild ambiguity (a less-first sense, a
  broad definition); verify it exists.
- hard: the `trap` field must name an active misdirection, and it must actually
  function — a plausible solver should be drawn toward a wrong reading, and the
  clue must survive a re-read once solved (fair in retrospect). A hard tag with
  no functioning trap → "revise".

8. **Difficulty tag sanity** — does the tag match the dial (§A2b)? Hard must be
   twisted, not merely obscure.

Cryptic clues additionally: 9. **Parse validity** — does the stated parse
actually work, word by word? For compound clues, do the chain's pieces assemble
exactly the answer's letters, in order? Definition at one end? Indicators
standard and unambiguous in function? No padding outside
definition/fodder/indicator/connector? 10. **Synonym fairness** — are the
wordplay substitutions (e.g. "shower" = RAIN) dictionary-fair, not stretches?

Verdicts:

- "accept" — meets the bar as-is.
- "revise" — fixable flaw; give a one-sentence, actionable reason (e.g.
  "definition is mid-clue", "trap claimed but no plausible wrong answer
  exists").
- "reject" — unsalvageable for this word/style; one-sentence reason.

Be strict. A mediocre clue bank is worse than a smaller good one. Accepting a
flawed clue is the costly error. A "revise" verdict merely triggers one cheap
retry; a "reject" is final for that clue — reserve it for genuinely
unsalvageable word/style combinations.

Output rules (strict — machine-parsed):

- One JSON object per CLUE, one per line (JSONL), in input order: {"word": ...,
  "clue": ..., "style": ..., "verdict": "accept|revise|reject", "basis": null |
  "aha|elegance|resistance|prize-fact|fun", "reason": null | "..."}
- No prose, no markdown fences, no commentary.

CLUES TO REVIEW: {{CLUES_JSONL}}
