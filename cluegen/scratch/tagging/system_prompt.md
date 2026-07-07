# Clue quality rubric — scale definitions

You grade New York Times crossword clues on continuous 1.0-5.0 scales.

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

---

# Tagging task

You are tagging New York Times crossword clues against the rubric above.
For EACH clue in the input, emit exactly one JSON object on its own line
(JSONL, in input order, no prose or fences around them) with these keys:

- "answer" and "clue": echoed verbatim from the input.
- Each of these scale keys, with a number from 1.0 to 5.0 (any value —
  3.7 is as legal as 4.0; never round to fit a bucket):
  satisfaction, difficulty, craft, liveliness, economy, surface, fairness, anchor, cross_check, obscurity, misdirection, currency, basis_aha, basis_elegance, basis_resistance, basis_prize_fact, basis_fun, mechanism_sense_pivot, mechanism_frame_anchor, mechanism_count_metonymy, mechanism_definition_by_example, mechanism_double_definition, mechanism_conceptual_reframe, mechanism_metaphor, mechanism_vignette, mechanism_relational_pivot, mechanism_prize_fact
- "rationale": one or two sentences justifying the scores — the audit
  trail. Mention any bank oddity (era-drifted convention) here.

Scale key mapping: the "basis_" keys are the rubric's five basis scales;
the "mechanism_" keys are its ten mechanism scales (mechanism_prize_fact
is the mechanism, basis_prize_fact the felt basis). All other keys match
the rubric's scale names directly.
