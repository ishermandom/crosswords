<!-- Copyright 2026 Ilya Sherman (ishermandom@) -->
<!-- SPDX-License-Identifier: MIT -->

# Setter design — expansive generation

_Scope: the design for the clue-generation (setter) side of the local pipeline —
its goal, operating rules, standing principles, and the hypotheses under test.
This document states the platonic ideal; how to achieve it is implementation
work, tracked in the window ledger and `tasks.md`. Campaign-level goals live in
`ceiling.md`._

## Goal

Maximize the setter's throughput of producing solver-satisfying clues. The
setter must be able to generate at least one satisfying clue for each target
answer word, including for each of the hardest words in the input set. More is
better.

## Autonomous operation

Claude iterates on this design autonomously, under these rules:

- **Check-ins**: only for genuine blockers, budget included. Otherwise keep
  making progress and post brief ongoing reports; the user chimes in when
  available. Surface taste and direction uncertainties in the reports rather
  than waiting on answers.
- **Task switching**: when the current task carries too much risk relative to
  expected reward without user input, switching tasks is a legitimate next step
  — but only after evaluating that another step is actually higher value, never
  reflexively.
- **Fable budget**:
  $10 per window, refreshed when a new autonomous stretch
  begins. The standing quota gates apply within it (self-launch under $2
  estimated; $5 hard cap between check-ins).
- **Self-served during setter work** (relaxations of standing gates, scoped to
  this design's work): local generation and judging batches launch without
  advance notice — footprint goes in the report, and lease rules still apply;
  setter prompt wording is the experiment surface and iterates freely, with
  changes documented in the ledger (judge prompts stay frozen without a design
  round); sealed eval material may be spent when an adoption decision needs it,
  with the unsealing reported.
- **Still gated**: fine-tune/training steps of any size require explicit
  go-ahead.

## Fixed constraints

- Runs entirely locally on the Gemma-4 stack via Ollama; no external API calls
  or per-use cost (`spec.md`).
- Setter changes are evaluated against the project's current best calibrated
  judge, not against fresh human labeling. The battery harness
  (`cluegen/scratch/battery.py`) is the operational definition of "current
  best": judge iteration updates the harness, never this document.
- Judge throughput bounds expansiveness: the most effective buildable judge is
  expected to cost minutes per candidate, so candidates sent per word are
  capped.

## Standing principles

1. **Let the setter set and the judge judge.** Both optimize solver satisfaction
   — the setter by writing the best clues it can, the judge by evaluating those
   clues against its criteria. Some overlap is natural, and part of setting is a
   light form of judging; but the setter must not rebuild the judge inside
   itself — evaluating quality requires deep nuance, and building it twice risks
   divergence for no gain. Exactly where the boundary sits is open space to
   explore.

2. **Satisfaction is the target.** The goal is to maximize solver satisfaction,
   not just to clear a minimum quality bar. "Satisfying" is operationalized by
   the taxonomy in `satisfaction.md`, which the judge's liveliness turn scores
   as its basis enum (prize fact, fun, elegance, aha). Not all satisfying-enough
   clues are created equal — some are more compelling than others.
   `satisfaction.md` gives ways to meet the minimum bar; the setter's goal is to
   maximize satisfaction, not just meet the bar. Satisfaction is not any single
   ingredient (user calibration, 2026-07-07): vividness in particular is one
   component, not the target — a vivid but inaccurate clue is not satisfying,
   and accuracy comes first. The aim is satisfying clues across the variety of
   clue types, never a bias toward one kind.

3. **Guide the brainstorm, don't gate it.** Unguided candidate generation tends
   to yield poor clues, so the engineering effort goes into the prompt sequence
   that steers the setter's thinking — both individual prompts and the ordering
   of steps that shapes what the model considers. Strong hunch, under test
   (H1b): guide toward expansive brainstorming whenever cost-feasible, possibly
   as repeated rounds of expand, keep the best, develop further.

4. **Rank by satisfaction; spend the send set on diversity.** Selection inside
   the setter — which ideas to develop, which candidates to send — orders by
   expected solver satisfaction, never by safety, and the sent set is spread
   across distinct ideas rather than variants of one. How much outright dropping
   (versus ranking low) is healthy inside the setter is part of the open
   boundary in principle 1.

5. **Decide by cheap experiment.** Every open design choice gets the smallest
   run that yields a signal, sanity-checked by Claude directly; and where scale
   demands it, scored by the judge as a free eval harness. The ladder: start
   with a ~5-minute sanity check unless no signal is possible at that scale;
   progress to a ~30-minute probe when the sanity check looks promising; before
   launching anything larger, adversarially evaluate whether a cheaper
   experiment could yield the necessary signal faster. When a question is
   answerable from already-collected data, answer it there — don't re-run
   expensive computations.

6. **Design for cache reuse.** Structure experiments so expensive computations
   are content-addressed and reusable: changing one prompt re-runs only that
   prompt's calls; changing a scoring rule re-runs nothing.

7. **Throughput is the end goal, not a per-experiment constraint.** Steady-state
   operation maximizes satisfying clues per wall-clock minute, but an experiment
   may freely trade throughput for insight — halving speed to double
   satisfaction is a good intermediate result.

8. **The judge sees what the solver sees.** The judge scores the printed clue
   only — never the setter's stated intent, claimed basis, or difficulty
   estimate. Setter metadata exists for ranking, diagnostics, and capture, not
   for sympathetic reading.

9. **Manage the idea portfolio.** After each experiment cluster, re-rank the
   open threads by expected value before starting the next — fresh perspective
   by schedule, not by mood. A thread showing diminishing returns is parked, not
   polished. Parked is not dead: a failed early experiment is weak evidence
   against a goal, so parked threads carry a revisit trigger.

10. **Capture good clues opportunistically.** Keep a running list of good clues
    discovered so far, so promising outputs from experiment runs aren't lost to
    the ether. The list is not a golden set and not a finalized clue bank; the
    existing `clue_bank.jsonl` is a starting point only.

## Setter output

The output format is expected to iterate; aim for what is actually useful.
Required properties rather than a fixed schema:

- the clue exactly as it would print, self-contained;
- a note explaining why the setter believes a solver would find the clue
  satisfying, naming the satisfaction basis it claims;
- whatever bookkeeping the capture list needs — the current bank fields are a
  starting point, not a contract (`confidence` in particular measures nothing as
  historically prompted).

Per principle 8, none of this metadata is visible to the judge.

## Roles

- **Setter** (generation): brainstorms, drafts, selects and orders what to send,
  packages candidates with their metadata. Optimizes for recall of satisfying
  clues.
- **Judge** (evaluation): the calibrated protocol behind the battery
  indirection; the quality bar candidates must clear, and the measurement
  instrument for every setter experiment.
- Ranking's owner is open: the setter itself, a repurposed reflection turn
  inside the setter conversation, or a fresh-context call (possibly a cheaper
  model).

## Hypotheses

Untested; each gets a smallest-sufficient experiment per principle 5. Results
and mechanics live in the window ledger and `tasks.md`, not here.

- **H1a — satisfaction-seeded width**: a brainstorm seeded by satisfaction type
  (one angle per basis) produces more non-flat drafts per word than
  semantic-sense seeding.
- **H1b — iterated expansion**: repeated rounds of expand, select the best, and
  develop further beat a single-pass wide brainstorm at equal compute.
- **H2 — ranking owner**: at least one candidate ranker (setter self-rank with a
  satisfaction rubric, a repurposed reflection turn, or a fresh-context cheaper
  model) orders drafts consistently with judge verdicts. (The historical
  `confidence` field is not a usable signal: its prompt never stated what it
  measures, and all-CUT fallbacks were stamped low, entangling it with
  self-editor survival.)
- **H3 — two-step casting**: for hard words (verbs, short function words),
  generating the vivid angle first and casting it into the answer's part of
  speech as a separate step raises the vivid-and-legal rate over one-shot
  drafting.
- **H4 — early stop**: production judging can stop after M bankables per word
  with negligible loss; derivable offline from full-judge experiment data, no
  dedicated runs.

## Open questions

- The setter-judge boundary: how much light judging belongs inside setting, and
  how much outright dropping beyond the send cap is healthy (principles 1 and
  4).
- The send cap's value and semantics (per word, or per word-satisfaction mix) —
  set from measured draft distributions, not a priori.
- Fine-grained satisfaction ordering: the judge's accept/revise boundary is
  calibrated, but its ability to _order_ two bankable clues is not. Validate
  with a small user taste round when a ranker is adopted, not before.
- The setter output format: which fields earn their place (see Setter output).

## Non-goals

- Judge design and tuning — out of scope for setter improvements, in scope for
  the overall project; this document tracks the judge only through the battery
  indirection.
- Production pipeline wiring — deferred to the first consumer of the redesigned
  funnel.
- Cloud-pipeline parity; the cloud setter remains the inspiration bar
  (`ceiling.md`).
