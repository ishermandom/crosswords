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
  mature Apple Silicon stack with Gemma support and one-command training.
  Trainer: stock `mlx_lm.lora`; optiq's own trainer (sensitivity-aware adapter
  sizing, standard adapter output) is the recorded fallback if stock balks on
  the OptiQ base, and a possible stage-2 lever. Framework survey (2026-07-02)
  confirmed mlx-lm is effectively the only mature option for this machine:
  Unsloth's Mac training is announced but unshipped, torchtune is unmaintained
  and stops at Gemma 2, LLaMA-Factory has no macOS backend. Fallback if mlx-lm
  hits a wall: Hugging Face PEFT + TRL on the PyTorch MPS backend — functional
  since bitsandbytes 0.49.2, but its 4-bit path is officially flagged as slow.
  Reference point: Mistral-7B, 5k examples, ~90 min on an M2 Max at ~7GB peak;
  the fanless M4 Air runs slower sustained, so training is an overnight job
  under `caffeinate`.
- **Models: `gemma-4-e2b-it-OptiQ-4bit` for stage 0,
  `gemma-4-12B-it-qat-OptiQ-4bit` for stage 1** (both under `mlx-community` on
  Hugging Face; 5.3 and 9.0 GB; settled 2026-07-02). OptiQ is a
  sensitivity-aware mixed-precision quantization — 4-bit or 8-bit chosen per
  layer by measured sensitivity — and it beats uniform 4-bit on measured
  capability at every Gemma 4 size (+2.1 for E2B, +6.4 for 12B); the stage-1
  checkpoint stacks that allocation on Google's quantization-aware-trained
  weights (weights trained to survive 4-bit compression). Using the same scheme
  family at both stages makes stage 0 a rehearsal of stage 1's exact path.
  Instruction-tuned start: the harness and scaffold speak chat format, and the
  quantization-aware checkpoints ship instruction-tuned only. Plain uniform
  4-bit checkpoints are the compatibility fallback. Training over an OptiQ base
  is expected to be routine QLoRA but is not explicitly documented anywhere — a
  few sanity training steps gate each stage before any long run.
- **Setter-only tuning.** The 26B screen and 31B confirm stay prompted and
  unchanged: an external quality bar a worse setter cannot silently degrade — it
  just banks less. (Judge tuning lacks labels at scale anyway; our
  Fable-verified verdicts number in the dozens.)
- **Data: unscoped — everything on the data side is provisional.** Source,
  curation recipe, and difficulty conditioning all get a dedicated design round
  before stage-1 data prep (user direction 2026-07-02); none of them is settled
  here. Candidate facts gathered so far, recorded only as input to that round:
  the xd corpus (xd.saul.pw) is one candidate source — a free download of 8.0M
  answer/clue pairs whose `clues.tsv` carries only `pubid`, `year`, `answer`,
  and `clue`, so difficulty conditioning would need its fuller metadata, the
  by-request raw puzzle corpus, or a different source; the question stays open.
  Its licensing is gray for redistribution, standard for personal research use.
  The cryptics dataset (cryptics.georgeho.org, ODbL) remains out of scope —
  wrong style for this track.
- **Curation is the core risk control.** Fine-tuning pulls toward the corpus
  median, and for any crossword corpus the median is dictionary-flat Monday
  fill. Recipe specifics (era, publications, question-mark share, length bands,
  dedup) belong to the data design round above. Stage 0 doesn't wait on that
  round: its ~500 pairs only exercise plumbing, so any clean slice works,
  subject to the answer-split rule below. Judges remain the backstop.
- **Serving for eval: `optiq serve` with the unfused adapter, not Ollama.** The
  tuned setter runs as the base checkpoint plus the trained adapter
  (`optiq serve --adapter`), never fused: fusing over a quantized base
  re-quantizes each merged layer and stacks fresh compression error on the
  result — the same warning `toolchains.md` §4.3 reached independently — so
  unfused serving means the eval measures exactly the artifact that was trained.
  The server speaks an OpenAI-style API behind a small client adapter in the
  scratch harness (the Ollama endpoint is a single constant in
  `pipeline_local.py`); stock `mlx_lm.server --adapter-path` is the fallback
  server, same API shape. The GGUF-import-into-Ollama route is rejected on
  evidence (2026-07-02): mlx-lm has no GGUF export for Gemma, llama.cpp
  conversion of Gemma 4 safetensors has unresolved failure reports, Ollama's MLX
  import is broken on exactly these checkpoints — and the
  de-quantize/re-quantize round trip would fold conversion loss into the
  measurement. Judges stay on Ollama; v9's model-batched phases keep the two
  servers from needing to be resident at the same time.
- **Eval: the existing two-tier harness** (`scratch/eval_panel.py`,
  local-ceiling branch). Tuned model slots in as the setter — bare single-turn
  and scaffolded variants both — against the same screens, gate, and 12-word
  panel. Split training data by answer; exclude panel and held-out answers from
  training entirely.
- **Decision metric:** confirmed-bankable clues per GPU-minute vs v9, with a <$2
  Fable checkpoint on whatever the tuned setter banks (per the standing
  checkpoint agreement in `ceiling.md`).

## Stages

- **Stage 0 — plumbing.** E2B + ~500 pairs; validate train → serve → eval end to
  end, including the harness's client adapter for `optiq serve`. Success is "the
  loop runs," not quality.
- **Stage 1 — the probe.** QLoRA gemma4-12B on 5–20k curated pairs, one
  overnight; evaluate via the harness. Tuned setter ≥ v9 on the decision metric
  → signal; otherwise record the negative and stop.
- **Stage 2 — only on signal.** Options, not commitments: more data/epochs; DPO
  from our own judge-labeled generations (every nightly batch produces
  accept/reject pairs — free preference data); tuning the 26B.

## Constraints and gates

- The user personally runs every model pull, pip install, and data download
  (user direction 2026-07-02, superseding the approve-per-pull rule for this
  probe); Claude supplies exact commands, repo ids, and URLs at each point.
  Fine-tuning runs are local-only.
- Fable spot-checks fall under the standing agreement: self-launch under ~$2
  estimated, $5 total between user check-ins.
- Thermal reality: training and big eval runs are overnight jobs, detached,
  under `caffeinate`.
- Local compute is shared with the actively running local-ceiling thread, which
  holds most of the GPU and RAM; a scheduling protocol between the two threads
  is not yet defined. Until it is, this thread keeps its footprint small
  (E2B-scale) and treats anything larger as needing coordination.

## Open questions

- Stage-1 model size: 12B as proposed, or repeat stage 0's model at larger data
  first? Decide after stage 0, with its training timings in hand.
- Everything on the data side — source, curation recipe, difficulty conditioning
  — a dedicated design round before stage-1 data prep.
- Whether stage 1's single-turn variant needs a short output-format wrapper
  (bare clue text vs JSON) — bare text avoids instruction-following decay and
  simplifies extraction.
- Whether the harness adapter can rely on schema enforcement under
  `optiq serve`: Ollama's `format` key has no verified equivalent there. Bare
  text for the single-turn variant sidesteps this; the scaffolded variant's
  extract turn may need prompt-and-parse instead.
