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
  Trainer: stock `mlx_lm.lora` for plain `gemma4` checkpoints (stage 0 ran on
  it); for stage 1 the trainer is
  `optiq lora train --rank-scaling constant --preset default` — the 12B
  QAT-OptiQ checkpoint ships as `model_type: gemma4_unified`, which stock mlx-lm
  0.31.3 doesn't recognize, and optiq's entry points register the
  `gemma4_unified → gemma4` remap (12B sanity run 2026-07-02 confirmed it loads
  and trains). Constant rank 8 / alpha 8 approximates stock behavior; optiq's
  sensitivity-aware rank scaling stays a stage-2 lever. One training-objective
  difference from the stage-0 run: optiq masks prompt tokens from the loss by
  default (only the clue text trains), which is the better objective anyway.
  Framework survey (2026-07-02) confirmed mlx-lm is effectively the only mature
  option for this machine: Unsloth's Mac training is announced but unshipped,
  torchtune is unmaintained and stops at Gemma 2, LLaMA-Factory has no macOS
  backend. Fallback if mlx-lm hits a wall: Hugging Face PEFT + TRL on the
  PyTorch MPS backend — functional since bitsandbytes 0.49.2, but its 4-bit path
  is officially flagged as slow. Reference point: Mistral-7B, 5k examples, ~90
  min on an M2 Max at ~7GB peak; the fanless M4 Air runs slower sustained, so
  training is an overnight job under `caffeinate`.
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
- **Data source: the Kaggle NYT clue set, with doshea as backup** (design round
  settled 2026-07-02). Primary:
  `kaggle.com/datasets/darinhawley/new-york-times-crossword-clues-answers-19932021`
  — 781,573 rows, each with a full date (the set opens on the first
  Shortz-edited puzzle, 1993-11-21), answer, and clue; one 11.5 MB zip; latin-1
  encoding; needs a Kaggle account (user-run download). Backup and cross-check:
  `github.com/doshea/nyt_crosswords` — per-day puzzle JSON 1976–2018 with an
  explicit weekday field. Rejected: CrosswordQA (6.78M rows, no dates → no
  difficulty proxy); public xd for stage 1 (clue rows carry year only; the dated
  `gxd` corpus is by-request via Discord); cryptics (wrong style). The xd copy
  stays around for frequency cross-checks.
- **Difficulty conditioning: one conditioned adapter, coarse weekday buckets.**
  Mon–Tue → easy, Wed–Thu → medium, Fri–Sat → hard, Sun → medium (bigger grid,
  mid-week difficulty; the Mon→Sat ramp is stable across the Shortz era). The
  bucket enters the training prompt as a difficulty token; eval prompts say
  medium, matching the harness. One pooled fine-tune rather than per-difficulty
  adapters: cluing skill is shared across difficulties, so at 5–20k pairs
  pooling feeds the shared skill all the data instead of a third of it, for one
  overnight instead of three; and same-answer contrast pairs across buckets (see
  the answer cap) are exactly what teach the token. After training, a cheap
  steering spot-check (same answer prompted easy vs hard); per-difficulty
  adapters are the recorded stage-2 fallback if the token doesn't steer.
- **Curation recipe** (settled 2026-07-02; motivation: fine-tuning pulls toward
  the corpus median, so the recipe shapes the distribution the setter imitates —
  but filters need evidence, not vibes, so speculative cutoffs were dropped):
  - Era: no cutoff. The dataset is entirely Shortz-edited — no convention break
    inside it — and gradual reference-staleness is barely visible to the judge
    metric. Recency enters only as a mild sampling weight: linear in year, 1.0
    (1993) rising to 2.0 (2021).
  - Sampling weights (builder round 2026-07-02): every sampling choice weights a
    row by weekday weight × recency weight. Weekday weights, Mon→Sun: 1 / 1.5 /
    2 / 4 / 3 / 2 / 4 (user-set) — Thursday is the top target difficulty, Sunday
    sits with it, Monday stays present at low frequency. Bucket-level
    consequence: easy ≈ 2.5, medium ≈ 10, hard ≈ 5 — a medium-centered tilt
    matching the eval register.
  - Dedup: normalized collapse — case/punctuation/whitespace-insensitive
    (answer, clue) key — keeping the most recent copy.
  - Answer cap: ≤ 4 clues per answer, drawn by the combined sampling weight
    without replacement. Same-answer contrast pairs (the conditioning token's
    teaching signal) still land for most multi-bucket answers; the funnel report
    counts them.
  - Answers: all of them, 3–15 letters A–Z, flattened phrases included; narrow
    to single dictionary words only if evidence shows phrase answers hurt
    single-word deployment.
  - Clues: non-empty; drop cross-references ("17-Across"), clue-contains-
    answer, and encoding-mangled rows. Bracketed meta-clues stay; question-mark
    share stays natural (the difficulty token already carries that signal).
  - Mechanism diversity (`satisfaction.md`): considered explicitly, no active
    balancing. The recipe filters nothing style-shaped, so natural-frequency
    sampling carries the corpus's own mechanism spread into the slice; tagging
    clues to balance them would need exactly the expensive evaluator we're
    avoiding. The existing diversity-audit practice (satisfaction.md, "Uses in
    the pipeline") applies unchanged to tuned-setter output, so a mechanism
    monoculture would surface at the bank audit rather than pass silently;
    mechanism-balanced sampling is the recorded lever if an audit ever shows
    collapse.
  - Split: by answer; panel + held-out answers excluded (rule below). The
    validation set is a fixed ~500 answers rather than a percentage — enough for
    a stable loss curve without shrinking training data as the slice grows.
    Stage 0 didn't wait on this round: its ~500 pairs only exercised plumbing.
    Judges remain the backstop for whatever curation misses.
- **Training prompt: a fixed natural-English single-turn instruction** (builder
  round 2026-07-02):
  `Write a {difficulty} crossword clue for the answer: {answer}`, difficulty ∈
  easy/medium/hard, no system prompt, target output the bare clue text. This
  string is a frozen interface — the eval client reproduces it exactly and the
  steering spot-check varies only the difficulty word — and it lives in one
  shared constants module so builder and eval can't fork. Rationale: adapter
  benefit tracks distribution proximity, not exact wording, and a short natural
  instruction doubles as an invocation phrase a future scaffolded pipeline can
  append at its clue-emission turns — with unfused serving, the adapter is a
  register module the pipeline applies per turn (base model for reasoning
  turns), so the fine-tune retains value even if one-shot quality falls short.
  Training bare (no system prompt) keeps the adapter uncoupled from the
  still-evolving v9 setter prompt. Distilling real scaffold traces into training
  data stays a stage-2 lever.
- **Slice size: set by 12B sanity timing.** Run the gated 12B sanity steps, take
  tokens/sec, and size the slice so one epoch fits one overnight under
  `caffeinate`, within the 5–20k band.
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

- The user personally runs every model pull and data download, from either
  account (user direction 2026-07-02, superseding the approve-per-pull rule for
  this probe); Claude supplies exact commands, repo ids, and URLs at each point.
  Model checkpoints land in the shared Hugging Face cache at
  `/Users/Shared/models/mlx/` (`HF_HUB_CACHE`; layout and rationale:
  `~/.claude/docs/shared-storage.md`); the harness and trainer refer to models
  by repo id and resolve through the cache. Python dependency syncs are the
  carve-out: declared in a reviewable `cluegen/pyproject.toml` edit, then
  installed by Claude into the sandbox venv without a further gate. Fine-tuning
  runs are local-only.
- Fable spot-checks fall under the standing agreement: self-launch under
  ~$2
  estimated, $5 total between user check-ins.
- Training runs are user-gated: no fine-tune training iterations — however
  brief, any model size — without the user's explicit go-ahead (user direction
  2026-07-02). Data prep, serving, and eval stay under the ordinary footprint
  rules below.
- Thermal reality: training and big eval runs are overnight jobs, detached,
  under `caffeinate`.
- Local compute is shared with the actively running local-ceiling thread, which
  holds most of the GPU and RAM; a scheduling protocol between the two threads
  is not yet defined. Until it is, this thread keeps its footprint small
  (E2B-scale) and treats anything larger as needing coordination.

## Open questions

- Stage-1 model size: 12B as proposed, or repeat stage 0's model at larger data
  first? Decide after stage 0, with its training timings in hand.
- Whether stage 1's single-turn variant needs a short output-format wrapper
  (bare clue text vs JSON) — bare text avoids instruction-following decay and
  simplifies extraction.
- Whether the harness adapter can rely on schema enforcement under
  `optiq serve`: Ollama's `format` key has no verified equivalent there. Bare
  text for the single-turn variant sidesteps this; the scaffolded variant's
  extract turn may need prompt-and-parse instead.
