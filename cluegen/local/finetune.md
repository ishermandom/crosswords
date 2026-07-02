<!-- Copyright 2026 Ilya Sherman (ishermandom@) -->
<!-- SPDX-License-Identifier: MIT -->

# Fine-tuning probe — spec

## Goal

Get a directional answer to one question: does a locally fine-tuned small model
beat the prompted-26B v9 pipeline as a clue setter, measured in
confirmed-bankable clues per GPU-minute? The probe is deliberately small — its
output is a go/no-go signal for investing further, not a production model.

## Why now

Evidence from the 2026-07-02 eval round (details: `ceiling-log.md`):

- The 31B confirm gate is stable (11/12 borderline clues drew identical verdicts
  across 5 re-judges), so yield is limited by clue craft, not judge noise.
- The gate's named complaints — padding, flatness, unearned question marks,
  part-of-speech mismatches — are style properties, exactly what supervised
  fine-tuning moves best. Prompting rents this behavior per-token through a
  4-turn scaffold; a tuned model would own it as its default distribution.
- The prompt-iteration round delivered ~2× end-to-end while killing three of
  five variants; remaining prompt levers look like 1.2–1.5× each. Fine-tuning is
  the higher-variance, higher-ceiling play, with stacked upside: craft prior
  (unknown, the bet), scaffold collapse (~3× fewer tokens per attempt), smaller
  model (~2× faster inference).

## Decisions

- **Method: QLoRA via mlx-lm.** Adapters over frozen 4-bit weights are the only
  local-feasible option (full fine-tuning needs 10×+ the memory). MLX is the
  mature Apple Silicon stack with Gemma support and a one-command train → fuse →
  serve flow. Reference point: Mistral-7B, 5k examples, ~90 min on an M2 Max at
  ~7GB peak; the fanless M4 Air runs slower sustained, so training is an
  overnight job under `caffeinate`.
- **Setter-only tuning.** The 26B screen and 31B confirm stay prompted and
  unchanged: an external quality bar a worse setter cannot silently degrade — it
  just banks less. (Judge tuning lacks labels at scale anyway; our
  Fable-verified verdicts number in the dozens.)
- **Data: curated subset of the xd corpus** (xd.saul.pw — 6M+ American-style
  answer/clue pairs, free download; scraped archive, licensing gray for
  redistribution, standard for personal research use). The cryptics dataset
  (cryptics.georgeho.org, ODbL) is out of scope — wrong style for this track.
- **Curation is the core risk control.** Fine-tuning pulls toward the corpus
  median, and the corpus median is dictionary-flat Monday fill. Curate for the
  lively subset: question-mark clues, length bands, dedup, and publication/era
  filters as metadata allows; condition on difficulty if signal exists. Judges
  remain the backstop.
- **Eval: the existing two-tier harness** (`scratch/eval_panel.py`,
  local-ceiling branch). Tuned model slots in as the setter — bare single-turn
  and scaffolded variants both — against the same screens, gate, and 12-word
  panel. Split training data by answer; exclude panel and held-out answers from
  training entirely.
- **Decision metric:** confirmed-bankable clues per GPU-minute vs v9, with a <$2
  Fable checkpoint on whatever the tuned setter banks (per the standing
  checkpoint agreement in `ceiling.md`).

## Stages

- **Stage 0 — plumbing.** Smallest Gemma variant + ~500 pairs; validate train →
  fuse → serve → eval end to end. Success is "the loop runs," not quality.
- **Stage 1 — the probe.** QLoRA gemma4-12B on 5–20k curated pairs, one
  overnight; evaluate via the harness. Tuned setter ≥ v9 on the decision metric
  → signal; otherwise record the negative and stop.
- **Stage 2 — only on signal.** Options, not commitments: more data/epochs; DPO
  from our own judge-labeled generations (every nightly batch produces
  accept/reject pairs — free preference data); tuning the 26B.

## Constraints and gates

- Model downloads are user-approved, per pull, per the campaign's standing rule
  (`ceiling.md`, Autonomy rules); fine-tuning runs are local-only.
- Fable spot-checks fall under the standing agreement: self-launch under
  ~$2
  estimated, $5 total between user check-ins.
- Thermal reality: training and big eval runs are overnight jobs, detached,
  under `caffeinate`.

## Open questions

- Stage-1 model size: 12B as proposed, or repeat stage 0's model at larger data
  first?
- Curation recipe specifics (which publications/eras, ?-subset share, length
  band).
- Whether stage 1's single-turn variant needs a short output-format wrapper
  (bare clue text vs JSON) — bare text avoids instruction-following decay and
  simplifies extraction.
