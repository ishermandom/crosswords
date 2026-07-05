<!-- Copyright 2026 Ilya Sherman (ishermandom@) -->
<!-- SPDX-License-Identifier: MIT -->

# Clue quality rubric (working draft)

One shared tag vocabulary for clue quality. The judges emit every tag at scale,
across thousands of clues; the user hand-labels a small stratified slice with
the same tags to calibrate and audit the judges. This replaces the earlier plan
of hand-labeling a golden set large enough to stand on its own — that plan
assumed a small set would suffice and does not scale.

Sources mined (2026-07-04): `satisfaction.md` (bases, mechanisms, failure modes,
anatomy), the local screen + confirm judge prompts (`pipeline_local.py`), and
the cloud path (`prompts/verify.md`, `local/quality.py` conventions and scales,
`CLUE_SPEC.md` invariants).

## Ratification pointer

Moves as entries are reviewed; a decision is recorded the turn it lands.

- Ratified: (none yet)
- Under review: `verdict`, `flaw`
- Pending: `basis`, `mechanism`, `difficulty`; the "dropped" list

Settled structure decisions (2026-07-04):

- Shared vocabulary — one rubric for judges (scale) and human labeling
  (calibration slice).
- Verdict + dimensions — the verdict is the decision; dimension tags explain it.
- Tag form decided per entry, leaning toward fewer labels; no global
  scales-vs-binaries rule.
- Trap-proportionality is decoupled from difficulty: derived from `difficulty` x
  `flaw=trap-fails`, not labeled as its own field.

## Entries

### 1. `verdict` — enum: `bankable` / `fixable` / `bad`

The decision. Discipline kept from the local judges: `fixable` and `bad` require
a named flaw (entry 2); if no concrete flaw can be named, the verdict is
`bankable` — vague unease is not a flaw. `fixable` means one correctable text
flaw; `bad` means fundamentally flawed for this answer.

Source: local screen/confirm verdicts; cloud accept/revise/reject.

### 2. `flaw` — enum, single-select, dominant flaw; only when not bankable

Proposed members, merged from all three sources:

- `flat-gloss` — accurate but no basis; a thesaurus entry.
- `false-content` — a qualifier or claim fails literal truth, including claimed
  alternatives that are not real.
- `associated-referent` — defines something near the answer, not the answer.
- `idiom-fragment` — the clued sense exists only inside a longer phrase.
- `trivia-wall` — anchor too obscure to check in retrospect.
- `question-mark` — ? dishonesty in either direction (unearned or missing).
- `padding` — economy failure; a word that does no work.
- `unnatural-surface` — no person would say or write it.
- `leak` — root/cognate leakage (etymology-angle exception applies).
- `trap-fails` — claimed misdirection does not function or does not survive a
  re-read.
- `convention` — mechanical style violations: abbreviation not signaled,
  fill-in-the-blank not rendered as ___.
- `paraphrase` — duplicates another banked clue's angle for the same word (the
  one member needing more context than the single clue).

Rationale for one enum instead of ~12 binaries: bankable clues would carry
all-true binaries — the information lives in the failures, and single-select
matches the "fixable = one concrete flaw" discipline.

### 3. `basis` — enum: `aha` / `elegance` / `resistance` / `prize-fact` / `fun` / `none`

The liveliness commitment, identical to the enum both judge schemas already
emit. `none` caps the verdict at `fixable`. The anti-inflation gradients live in
rubric prose, not extra fields: recognition is not fun; a fact earns its keep by
surprise or specificity; a relation to another quantity needs a pivot; a vivid
straight definition is elegance, not `none`.

Source: satisfaction.md bases; local judge basis field; cloud verify basis
field.

### 4. `mechanism` — enum, dominant mechanism

The satisfaction.md ten plus `plain-definition`: sense pivot, frame anchor,
count/role metonymy, definition-by-example, double definition, conceptual
reframe, metaphor-as-definition, vignette, relational pivot, prize fact.

The one field no judge currently emits. It exists for the diversity audit
(monoculture detection) and angle-distinct depth, both of which only work at
bank scale — exactly what judge-emitted tags make affordable.

Source: satisfaction.md mechanisms; its 2026-07-02 snapshot hand-applied this
exact tagging.

### 5. `difficulty` — enum: `easy` / `medium` / `hard`

The difficulty the text actually achieves, not the generation target. Easy =
direct, signposted; medium = less-first sense, mild ambiguity; hard = active
misdirection. Hard-tag audits derive from `difficulty=hard` x `flaw=trap-fails`;
hard means twisted, not obscure.

Source: both judge paths assign it; training data and the fine-tune ladder
condition on it.

## Dropped, deliberately (pending ratification)

- The 1-5 scales (angle craft, misdirection, elasticity, reference
  accessibility, surface coherence, fairness of deception, cross-check payoff)
  and their day profiles — the local path abandoned scales for enums + named
  flaws and did not miss them; slow and inter-rater unstable for hand labeling.
- Separate convention binaries (tense agreement, wordplay indicator,
  abbreviation signaled, fill format, genuine alternatives) — folded into `flaw`
  members (`convention`, `question-mark`, `false-content`); substitution
  failures land under `false-content` or `associated-referent`.
- Cross-check payoff as a tag — under-determination is a virtue, not a dimension
  to police (satisfaction.md, user calibration 2026-07-04).
- Required free-text rationale — judges emit analysis anyway; optional for human
  labels.
