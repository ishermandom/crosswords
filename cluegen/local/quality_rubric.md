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

- Ratified: `satisfaction` continuous (2026-07-04 round 3 — supersedes the
  round-2 three-bucket answer; excellent/good/meh survive as prose anchors, not
  buckets); `liveliness` continuous; `difficulty` kept (weekday is a poor
  per-clue proxy — good aggregate correlation, no per-clue guarantee); the
  defect-flavored `flaw` field dropped in favor of an optional free-text `note`;
  `paraphrase` out of this rubric (bank dedup process, not a clue tag).
- Under review: `strengths` membership; `basis` mode; `mechanism` mode;
  `difficulty` form under the all-scales convention (enum vs continuous).
- Pending: the "dropped" list.

Settled structure decisions (2026-07-04):

- Shared vocabulary — one rubric for judges (scale) and human labeling
  (calibration slice).
- This rubric targets the NYT bank; machine-generated clues keep their own
  defect-centric rubric in the judge prompts.
- Tag form decided per entry, leaning toward fewer labels; no global
  scales-vs-binaries rule.
- Scale convention (user, 2026-07-04): ALL graded axes share one aligned
  normalization, continuous 1.0-5.0 — any value is legal (3.5 as acceptable as
  2.0). The normalization itself is arbitrary (0-100 would do); what matters is
  that every scale aligns and leaves enough degrees of freedom that a model
  never has to flip a coin between adjacent buckets that both feel a bit wrong.
  Expressiveness beats inter-rater stability.
- Trap-proportionality derived, not labeled (was coupled to difficulty in v0;
  decoupled per user).

## Entries

### 1. `satisfaction` — the primary verdict — RATIFIED 2026-07-04 as continuous

Continuous 1.0-5.0: how much the clue earns its keep. Prose anchors from the
round-2 buckets: ~5.0 excellent (showcase), ~3.0 good (solid bank citizen), ~1.5
meh. Replaces v0's bankable/fixable/bad, which presumed defects — wrong shape
for a bank where nothing is truly bad (user, 2026-07-04). This is the tag the
user most wants from the data.

### 2. `liveliness` — flat-vs-lively — RATIFIED 2026-07-04 as continuous

Continuous 1.0-5.0: 1.0 = dictionary-flat gloss, 5.0 = fully alive. Explicitly
wanted as a graded axis (user, 2026-07-04). Distinct from `satisfaction` (a flat
clue can still be a good bank citizen on a Monday; a lively one can underwhelm)
and from `basis` (which names WHAT enlivens; this grades HOW MUCH). Soft
consistency expectation: scores near 1.0 sit naturally with `basis=none`.

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

### 5. `difficulty` — enum: `easy` / `medium` / `hard` — RATIFIED 2026-07-04

The difficulty the text actually achieves. Kept (user, 2026-07-04): weekday is a
poor per-clue proxy — the aggregate correlation is good, but no individual clue
is guaranteed to match its day — so an achieved-difficulty tag audits the proxy
the training data's conditioning token derives from, which bears directly on how
clean the fine-tune's conditioning signal is.

### 6. `note` — optional free text — RATIFIED 2026-07-04

Replaces the v0 `flaw` enum. Catches the rare bank oddity (dated convention, era
drift) without a structured field that would sit empty on nearly every clue. The
full defect vocabulary remains the machine-clue rubric's concern.

### 7. `strengths` — inverted defect axes (under review; members TBD)

The v0 defect enum re-read from the opposite end (user, 2026-07-04): not flags
for flaws, but graded strength scales on the continuous 1.0-5.0 convention.
Candidate members, inverted from v0/judge checks:

- `economy` — padded ... not a wasted word.
- `surface` — stilted ... something a person would actually say.
- `fairness` — trap collapses on re-read ... lands clean in retrospect (scored
  only when misdirection exists).
- `anchor` — needs a lookup to believe ... instantly checkable once seen.

Which members earn a place — and whether four is already too many — is the next
review question.

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
