<!-- Copyright 2026 Ilya Sherman (ishermandom@) -->
<!-- SPDX-License-Identifier: MIT -->

# NYT clue-bank tag rubric (working draft)

One shared tag vocabulary for grading clues in the NYT bank — the training
corpus and the source of golden calibration data. Judges emit every tag at
scale, across thousands of clues; the user hand-labels a small stratified slice
with the same tags to calibrate and audit the judges. This replaces the earlier
plan of hand-labeling a golden set large enough to stand on its own — that plan
assumed a small set would suffice and does not scale.

Scope (user, 2026-07-04): this rubric grades KNOWN-GOOD human clues, so it is
satisfaction-centric — NYT clues are essentially never "bad", and defect tags
earn little. It is deliberately NOT the rubric for machine-generated clues,
which routinely carry flaws both significant and minor; that defect-centric
vocabulary lives in the judge prompts (screen/confirm, cloud verify) and stays
there.

Sources mined (2026-07-04): `satisfaction.md` (bases, mechanisms, failure modes,
anatomy), the local screen + confirm judge prompts (`pipeline_local.py`), and
the cloud path (`prompts/verify.md`, `local/quality.py` conventions and scales,
`CLUE_SPEC.md` invariants).

## Ratification pointer

Moves as entries are reviewed; a decision is recorded the turn it lands.

- Ratified: `paraphrase` is out of this rubric (bank dedup process, not a clue
  tag); IF a flaw field survives, its mode is dominant-required +
  others-allowed.
- Under review: `satisfaction` (bucket count), `liveliness` (granularity;
  relation to `basis`), fate of the `flaw` field, `difficulty` (keep as
  weekday-proxy audit vs out).
- Pending: `basis`, `mechanism`; the "dropped" list.

Settled structure decisions (2026-07-04):

- Shared vocabulary — one rubric for judges (scale) and human labeling
  (calibration slice).
- This rubric targets the NYT bank; machine-generated clues keep their own
  defect-centric rubric in the judge prompts.
- Tag form decided per entry, leaning toward fewer labels; no global
  scales-vs-binaries rule.
- Trap-proportionality derived, not labeled (was coupled to difficulty in v0;
  decoupled per user).

## Entries

### 1. `satisfaction` — the primary verdict (bucket count under review)

How much the clue earns its keep: `excellent` / `good` / `meh`, possibly more
buckets. Replaces v0's bankable/fixable/bad, which presumed defects — wrong
shape for a bank where nothing is truly bad (user, 2026-07-04). This is the tag
the user most wants from the data.

### 2. `liveliness` — flat-vs-lively scale (granularity under review)

Explicitly wanted as a graded axis (user, 2026-07-04): from dictionary-flat
gloss to fully alive. Distinct from `satisfaction` (a flat clue can still be a
good bank citizen on a Monday; a lively one can underwhelm) and from `basis`
(which names WHAT enlivens; this grades HOW MUCH). Relation to `basis=none` and
point count to be settled.

### 3. `basis` — enum: `aha` / `elegance` / `resistance` / `prize-fact` / `fun` / `none`

Names what the clue makes a solver feel — the enum both judge schemas already
emit. The anti-inflation gradients live in rubric prose: recognition is not fun;
a fact earns its keep by surprise or specificity; a relation to another quantity
needs a pivot; a vivid straight definition is elegance, not `none`.

### 4. `mechanism` — enum, dominant mechanism

The satisfaction.md ten plus `plain-definition`: sense pivot, frame anchor,
count/role metonymy, definition-by-example, double definition, conceptual
reframe, metaphor-as-definition, vignette, relational pivot, prize fact.

No judge currently emits this. It exists for the diversity audit (monoculture
detection) and angle-distinct depth, both of which only work at bank scale —
exactly what judge-emitted tags make affordable.

### 5. `difficulty` — enum: `easy` / `medium` / `hard`

The difficulty the text actually achieves. For bank clues the weekday already
supplies a difficulty proxy — the training data's conditioning token derives
from it — so the live question is whether an achieved- difficulty tag earns its
keep as an AUDIT of that proxy (how noisy is weekday as a difficulty label?),
which bears directly on how clean the fine-tune's conditioning signal is.

### 6. `flaw` — likely dropped for this rubric (decision pending)

v0 carried a 12-member defect enum merged from the judge paths. For NYT bank
data the user expects flaws to be rare enough that the field may not earn its
place; if kept at all, it shrinks to the rare bank-specific defects (e.g.
era-drifted conventions), with mode dominant-required + others-allowed. The full
defect vocabulary remains the machine-clue rubric's concern.

## Dropped, deliberately

- `paraphrase` / angle-distinctness — the bank's dedup process, not a
  clue-quality tag (ratified 2026-07-04).
- The 1-5 scales (angle craft, misdirection, elasticity, reference
  accessibility, surface coherence, fairness of deception, cross-check payoff)
  and their day profiles — the local path abandoned scales for enums + named
  flaws; the one graded axis this rubric wants back is `liveliness`, on its own
  terms.
- Separate convention binaries (tense agreement, wordplay indicator,
  abbreviation signaled, fill format, genuine alternatives) — correctness checks
  for machine clues, not grading axes for human ones.
- Cross-check payoff as a tag — under-determination is a virtue, not a dimension
  to police (satisfaction.md, user calibration 2026-07-04).
- Required free-text rationale — judges emit analysis anyway; optional for human
  labels.
