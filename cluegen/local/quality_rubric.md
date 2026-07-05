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
earn little. It is deliberately NOT the rubric for machine-generated clues (that
defect-centric vocabulary lives in the judge prompts), and the existing judges
do not adopt it — it defines a separate tagging path.

Sources mined (2026-07-04): `satisfaction.md` (bases, mechanisms, failure modes,
anatomy), the local screen + confirm judge prompts (`pipeline_local.py`), and
the cloud path (`prompts/verify.md`, `local/quality.py` conventions and scales,
`CLUE_SPEC.md` invariants).

## Ratification pointer

Moves as entries are reviewed; a decision is recorded the turn it lands.

- Ratified (rounds 1-7, 2026-07-04): the two-tier architecture below; all four
  holistic scales (`satisfaction`, `difficulty`, `craft`, `liveliness`);
  breakdown scales — `basis` x5, `mechanism` x10, `economy`, `surface`,
  `fairness`, `anchor`, `cross_check`, `obscurity`, `misdirection`, and round
  7's `currency`; required `rationale`; `flaw`, `paraphrase`, convention
  binaries, and day profiles out; `elasticity` and `freshness` ruled out
  (close-calls addendum). 27 scales + rationale per clue. Nothing under review.
- Open follow-up, not blocking: calibration-slice sizing under the 27-scale
  labeling cost (~2-3 min/clue with rationale, so ~75-150 clues, stratified).

Settled structure decisions (2026-07-04):

- Two-tier architecture (user, round 6): HOLISTIC scales are summary statistics;
  BREAKDOWN scales are justifications — they help the model think the holistic
  answer through, and make disagreements diagnosable. Breakdowns feed holistics
  without determining them.
- Shared vocabulary — one rubric for judges (scale) and human labeling
  (calibration slice).
- Scale convention: ALL graded axes share one aligned normalization, continuous
  1.0-5.0 — any value is legal (3.5 as acceptable as 2.0). The normalization is
  arbitrary; what matters is alignment and enough degrees of freedom that a
  model never flips a coin between adjacent buckets.
- The former `strengths` grouping dissolved into the breakdown tier (round 6) —
  scale names unchanged; breakdowns are not all virtues (`obscurity`,
  `misdirection` are neutral axes).
- Tag form decided per entry; no global scales-vs-binaries rule.
- Trap-proportionality derived, not labeled.

## Holistic scales (summary statistics)

### `satisfaction`

How much the clue earns its keep. Prose anchors: ~5.0 excellent (showcase), ~3.0
good (solid bank citizen), ~1.5 meh. The tag the user most wants from the data.

### `difficulty`

The difficulty the text actually achieves: 1.0 = Monday-direct, 3.0 = midweek
twist, 5.0 = Saturday-grade. Audits the weekday proxy the training data's
conditioning token derives from (weekday correlates in aggregate, guarantees
nothing per clue). Fed by `obscurity` and `misdirection` — two different roads
to hard.

### `craft`

Deliberateness and execution of the chosen angle, rated holistically (returned
in round 6; the cloud path's `angle_craft`, which round 5 had absorbed). 1.0 =
the obvious default angle taken lazily; 5.0 = a considered angle, executed
tightly.

### `liveliness`

Flat ... fully alive: 1.0 = dictionary-flat gloss, 5.0 = vivid. The summary over
the basis profile (an all-low basis profile sits naturally near 1.0); distinct
from `satisfaction` — a flat clue can still be a good Monday bank citizen, and a
lively one can underwhelm.

## Breakdown scales (justifications)

### `basis` — five scales

How strongly the clue delivers each: `aha`, `elegance`, `resistance`,
`prize_fact`, `fun`. No enum, no `none` — the dominant basis is implicit and a
flat gloss is an all-low profile. Anti-inflation gradients: recognition is not
fun; a fact earns its keep by surprise or specificity; a relation to another
quantity needs a pivot; a vivid straight definition scores on `elegance`, not
nowhere.

### `mechanism` — ten scales

How much each mechanism does the clue's work: sense pivot, frame anchor,
count/role metonymy, definition-by-example, double definition, conceptual
reframe, metaphor-as-definition, vignette, relational pivot, prize fact.
Composition is two elevated scales; `plain-definition` is an all-low profile.
Most clues sit at 1.0 on most mechanisms — the sparse profile is fast to emit.
Exists for the diversity audit and angle-distinct depth.

### `economy`

Padded ... not a wasted word.

### `surface`

Stilted ... something a person would actually say.

### `fairness`

Trap collapses on re-read ... lands clean in retrospect. Scored only when
misdirection exists (neutral default otherwise). Also where `obscurity` bites
past its cliff: an anchor too obscure to check is unfair however clean the
mechanics (the trivia-wall failure).

### `anchor`

Needs a lookup to believe ... instantly checkable once seen. Checkability in
retrospect — orthogonal to how many solvers knew the fact going in (that's
`obscurity`): "Spinal Tap amp's top setting" is niche knowledge yet instantly
checkable.

### `cross_check`

Clue alone pins the answer ... several plausible fills, collapsed only by
crossing answers. A quantified virtue ("When shadows stretch" fitting DUSK and
DAWN is doing extra work). Not `difficulty` in disguise: a hard clue can pin a
unique answer, a flat "Compass point" under-determines.

### `obscurity` — added round 6

Universal knowledge ... specialist trivia (1.0 = every solver walks in knowing
it, 5.0 = a lookup for almost everyone). Graded separately even though it feeds
`difficulty`, because it is a frequent pattern in its own right — and it feeds
`fairness` too: past some cliff, obscure clues stop being fair (user,
2026-07-04).

### `misdirection` — added round 6

No feint ... surface confidently sells a wrong reading (1.0 = points straight at
the answer, 5.0 = full trap). Graded separately (user, 2026-07-04): it feeds
`satisfaction` as well as `difficulty`, and not all difficult clues rely on it —
obscurity-hard clues sit low here.

### `currency` — added round 7

Dated referent ... current one (1.0 = bakes in an assumption the world has moved
past, e.g. a 1994 "Palm handheld"; 5.0 = reads as written today). Distinct from
`obscurity`: a dated referent was universal in its day. Graded per clue rather
than proxied by the puzzle's year (user, 2026-07-04): most old clues are still
current — few actually bake in dated assumptions — so year alone is a poor
proxy. Matters for training data drawn preferentially from recent eras.

## `rationale` — required free text

One or two sentences justifying the scores — the audit trail for whether a
decision is valid or bogus. Bank oddities (era-drifted conventions) fold in
here.

## Where the cloud path's seven 1-5 scales went (accounting, round 6)

- Remapped one-to-one: `surface_coherence` → `surface`; `fairness_of_deception`
  → `fairness`; `cross_check_payoff` → `cross_check`; `misdirection` →
  `misdirection` (round 5 absorbed it into `difficulty`; round 6 restored it as
  its own breakdown); `angle_craft` → `craft` (round 5 absorbed it; round 6
  restored it as a holistic).
- Split in two: `reference_accessibility` → `obscurity` (audience breadth,
  inverted) + `anchor` (checkability in retrospect).
- Ruled out after review: `elasticity` — see the close-calls addendum.
- Retired outright: the day profiles (per-weekday acceptance ranges + quality
  floors) — gating logic for admitting new clues, not grading tags for clues
  already in the bank.

## Addendum: close calls (considered and ruled out, 2026-07-04)

Candidate scales that nearly made the rubric; kept here so the reasoning
survives the next "are there others lurking?" pass.

- `elasticity` — how many coherent readings the surface sustains (1 = "Longest
  river in France", single reading; ~3 = "Curb an impulse" for CHECK, noun/verb
  hover with several senses live; 5 = "Round number?" or "Current affairs?",
  rich reinterpretation space). Ruled out: an ingredient in several dimensions
  (`difficulty`, `misdirection`, `satisfaction`) but hard to measure on its own
  — raters disagree on what counts as a coherent alternative reading — and
  probably not worth the effort. Distinct from `cross_check` (readings of the
  text vs answers that fit), which stays.
- `freshness` — chestnut ... novel angle ("Bank deposit?" for SILT was brilliant
  once; a 2023 reuse is a different object). Ruled out: not important for
  training a fine-tuned model (the hope), and raw repetition frequency is
  mechanically computable from the bank when the diversity audit needs it —
  perceived staleness adds little over that count.

## Addendum: convention binaries (dropped; ratified 2026-07-04)

Correctness gates from `quality.py`, true by construction on bank data — the NYT
bank is the source of these conventions — so as bank tags they carry ~zero
information. They remain gates for machine-generated clues in the existing
pipeline. Era-drifted exceptions land in `rationale`.

- `has_tense_agreement` — clue's grammatical form matches the answer.
- `has_wordplay_indicator` — ? present iff misdirection/wordplay.
- `is_abbreviation_signaled` — abbreviated answer flagged in the clue.
- `uses_fill_format` — fill-in-the-blank rendered as ___.
- `has_genuine_alternatives` — claimed alternatives are real candidates.

## Dropped, deliberately

- `paraphrase` / angle-distinctness — a property of a clue PAIR, not one clue;
  the bank's dedup process owns it (ratified 2026-07-04). Residual coverage:
  near-identical mechanism profiles on the same answer flag paraphrase
  candidates.
- The day profiles and convention binaries — see the accounting and addendum
  sections above (ratified 2026-07-04).
