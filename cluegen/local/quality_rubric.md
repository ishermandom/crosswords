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

- Ratified (rounds 1-4, 2026-07-04): every entry — `satisfaction`, `liveliness`,
  and `difficulty` continuous; `basis` as five per-member scales and `mechanism`
  as ten (dominant implicit; `none` / `plain-definition` are all-low profiles);
  all four `strengths` (economy, surface, fairness, anchor); optional free-text
  `note`; `flaw` and `paraphrase` out. 22 scales + note per clue.
- Under review: the "dropped" list (below) — never explicitly ratified.
- Out of scope (user, 2026-07-04): the existing judges (screen/confirm, cloud
  verify) do NOT adopt this rubric — it defines a separate tagging path over the
  bank; their schemas stay as they are.
- Open follow-up, not blocking: calibration-slice sizing under the 22-scale
  labeling cost (~1-2 min/clue for a human, so a slice of ~100-200 clues,
  stratified).

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

### 3. `basis` scales — RATIFIED 2026-07-04 as five per-member scales

Each basis rated 1.0-5.0 for how strongly the clue delivers it: `aha`,
`elegance`, `resistance`, `prize_fact`, `fun`. No enum and no `none` value — the
dominant basis is implicit (the highest scale), and a flat gloss is simply an
all-low profile (consistent with `liveliness` near 1.0). Composite clues (a
funny aha) stop being a forced choice. The anti-inflation gradients live in
rubric prose: recognition is not fun; a fact earns its keep by surprise or
specificity; a relation to another quantity needs a pivot; a vivid straight
definition scores on `elegance`, not nowhere.

Migration note: the judge schemas' single `basis` enum derives from these scales
(argmax, with a floor below which the answer is "none") — schema change needed
when judges adopt the rubric.

### 4. `mechanism` scales — RATIFIED 2026-07-04 as ten per-member scales

Each satisfaction.md mechanism rated 1.0-5.0 for how much it does the clue's
work: sense pivot, frame anchor, count/role metonymy, definition-by-example,
double definition, conceptual reframe, metaphor-as-definition, vignette,
relational pivot, prize fact. Composition ("a sense pivot inside a frame") is
two elevated scales — the thing the dominant-only enum could not express.
`plain-definition` is not a member: an all-low profile IS a plain definition
(same implicit-aggregate logic as `basis`). In practice most clues sit at 1.0 on
most mechanisms; the sparse profile is fast to emit.

No judge currently emits this. It exists for the diversity audit (monoculture
detection) and angle-distinct depth, both of which only work at bank scale —
exactly what judge-emitted tags make affordable.

### 5. `difficulty` — RATIFIED 2026-07-04 as continuous

Continuous 1.0-5.0, the difficulty the text actually achieves: 1.0 =
Monday-direct, 3.0 = midweek twist (less-first sense, mild ambiguity), 5.0 =
Saturday-grade active misdirection. Kept because weekday is a poor per-clue
proxy — good aggregate correlation, no per-clue guarantee — so this audits the
proxy the training data's conditioning token derives from. Bucket comparisons
for conditioning audits derive by thresholds chosen at analysis time (and
declared there).

### 6. `note` — optional free text — RATIFIED 2026-07-04

Replaces the v0 `flaw` enum. Catches the rare bank oddity (dated convention, era
drift) without a structured field that would sit empty on nearly every clue. The
full defect vocabulary remains the machine-clue rubric's concern.

### 7. `strengths` — RATIFIED 2026-07-04, all four members

The v0 defect enum re-read from the opposite end (user, 2026-07-04): graded
strength scales, continuous 1.0-5.0:

- `economy` — padded ... not a wasted word.
- `surface` — stilted ... something a person would actually say.
- `fairness` — trap collapses on re-read ... lands clean in retrospect (scored
  only when misdirection exists; no misdirection = leave at the neutral default,
  matching quality.py's defaults-to-5 precedent).
- `anchor` — needs a lookup to believe ... instantly checkable once seen.

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
