<!-- Copyright 2026 Ilya Sherman (ishermandom@) -->
<!-- SPDX-License-Identifier: MIT -->

# Setter design — expansive generation

_Scope: the design for the clue-generation (setter) side of the local pipeline —
its goal, the principles that shape it, and the hypotheses under test. The
judge's design and calibration live in the window ledger and the battery harness
(`cluegen/scratch/`); campaign-level goals live in `ceiling.md`._

## Goal

Maximize the number of judge-bankable, solver-satisfying clues the setter
produces per answer word — including at least a couple of interesting candidates
for the hardest words — by guiding its brainstorming, not by filtering its
output.

## Fixed constraints

- Runs entirely locally on the Gemma-4 stack via Ollama; no external API calls
  or per-use cost (`spec.md`).
- The judge is the adopted single-flow multi-turn protocol
  (`cluegen/scratch/variants/confirm_multiturn_v3.py`), calibrated against the
  user's verdicts; setter changes are evaluated against it, not against fresh
  human labeling.
- Judge throughput bounds expansiveness: the full protocol costs minutes per
  candidate at the 31B, so candidates sent per word are capped.
- The bank schema (`clue_bank.jsonl`) requires structured metadata per banked
  clue: `clue`, `difficulty`, `trap`, `confidence`.

## Standing principles

1. **Setter recalls, judge decides.** The setter surfaces the best candidates it
   can generate — multiple per word, up to a fixed cap — and never pre-filters.
   Its self-editor holds no kill authority; the judge is the only gate.
   Rationale: the setter's own KEEP/CUT pass was the funnel's choke point and
   systematically favored flat-but-safe clues over vivid ones (evidence: window
   ledger, "Setter funnel evidence").

2. **Satisfaction is the target.** Not difficulty (a proxy that misfired: early
   output was unsatisfying by being far too easy, but difficulty is only one
   component), and not substitution safety (the judge owns correctness).
   "Satisfying" is operationalized by the taxonomy in `satisfaction.md`, which
   the judge's liveliness turn scores as its basis enum (prize fact, fun,
   elegance, aha).

3. **Guide the brainstorm, don't gate it.** Unguided candidate generation yields
   exclusively poor clues, so the engineering effort goes into the prompt
   sequence that steers the setter's thinking — both individual prompts and the
   ordering of steps that shapes what the model considers.

4. **Rank, never veto.** Candidates are sorted roughly best-to-worst so the cap
   and the judge's time are spent well, but nothing is killed by rank. The
   ranking dimension is expected solver satisfaction, explicitly not
   correctness.

5. **Decide by cheap experiment.** Every open design choice gets the smallest
   run that yields a signal, scored by the judge as a free eval harness;
   anything answerable from already-collected data (e.g. early-stop policies) is
   simulated offline instead of re-run.

## Roles

- **Setter** (generation): brainstorms angles, drafts candidates, packages the
  sent set with its metadata. Optimizes for recall of interesting clues.
- **Ranker** (ordering): sorts the setter's candidates by expected solver
  satisfaction. Owner undecided — see hypotheses; candidates are the setter
  itself, a repurposed reflection turn, or a separate fresh-context call.
- **Judge** (verdicts): the calibrated multi-turn protocol; sole kill authority,
  and the measurement instrument for every setter experiment.

## Hypotheses

Untested as of this document's creation; each gets a smallest-sufficient
experiment, judged by the adopted protocol. Results and mechanics live in the
window ledger and `tasks.md`, not here.

- **H1 — guided width**: a wider brainstorm seeded by satisfaction type (one
  angle per basis: prize fact, aha, elegance, fun) produces more non-flat drafts
  per word than today's semantic-sense seeding.
- **H2 — ranking owner**: at least one of {setter self-rank with a satisfaction
  rubric, repurposed same-conversation reflection turn, fresh-context 26B
  ranker} orders drafts consistently with judge verdicts. (The existing
  `confidence` field is not a usable signal: its prompt never states what it
  measures, and all-CUT fallbacks are stamped low, entangling it with
  self-editor survival.)
- **H3 — two-step casting**: for hard words (verbs, short function words),
  generating the vivid angle first and casting it into the answer's part of
  speech as a separate step raises the vivid-and-legal rate over one-shot
  drafting.
- **H4 — early stop**: production judging can stop after M bankables per word
  with negligible loss; derivable offline from full-judge experiment data, no
  dedicated runs.

## Open questions

- Who ranks (H2), and whether the reflection turn survives at all once its kill
  authority is gone — as a metadata packager, a ranker, or nothing.
- The cap's value and semantics (per word, or per word-satisfaction mix) — to be
  set from measured draft distributions, not chosen a priori.
- Fine-grained satisfaction validation: the judge's accept/revise boundary is
  calibrated, but its ability to _order_ two bankable clues is not. Validate
  with a small user taste round when a ranker is adopted, not before.

## Non-goals

- Judge design and tuning (settled this window; see the ledger).
- Production pipeline wiring — deferred to the first consumer of the redesigned
  funnel.
- Cloud-pipeline parity; the cloud setter remains the inspiration bar
  (`ceiling.md`).
