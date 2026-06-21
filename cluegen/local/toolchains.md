# Local LLM stack for crossword clue generation — analysis & decision record

**Last validated:** 2026-06-20 **Status:** Living document. Sections 1–3 are
durable; **Section 4 is timestamped and will go stale** — see the re-run
guidance in Section 3.

This document captures the full end-to-end analysis for running (and
fine-tuning) a local LLM that generates crossword clues. It is written to be
self-contained: a reader who has never seen the originating discussion should be
able to act on it.

---

## 1. Core problem & constraints

### Hardware (fixed, long-term)

- **2025 MacBook Air, base M4** (not Pro/Max), **32 GB unified memory**, **~120
  GB/s** memory bandwidth.
- **Fanless / passively cooled.** Consequence: sustained 100%-GPU loads (e.g.
  training, long batch runs) **thermally throttle**; short inference bursts
  mostly do not.
- No hardware upgrades planned. Treat 32 GB / 120 GB/s as permanent.

### Goal

- Machine generation of crossword clues using a **purely locally-running LLM**.
  - "Local" is a constraint on the **deployed generator** (inference). It does
    **not** forbid using cloud/borrowed hardware for _offline_ dev work like
    fine-tuning — the deployed artifact stays local.
- **No compromise on the underlying model.** The chosen model is **Gemma 4 31B
  (dense)** (released 2026-04-02; ~30.7B params; Gemini-3-derived). Anything
  smaller has been judged unacceptable on quality.

### Model facts that drive the analysis (Gemma 4 31B dense)

- **Hybrid attention:** interleaved local sliding-window + global layers;
  **global layers use unified (shared) K/V** and pruned/proportional RoPE. Net
  effect: **KV cache is small** — ~10k tokens is **sub-1 GB**, so KV is _not_ a
  binding memory constraint here.
- **Hybrid-thinking model:** thinking mode is toggleable per request. Thinking
  steps emit many more tokens (latency/throughput cost); terse steps emit few.
- **Ships an MTP (Multi-Token Prediction) drafter** for speculative decoding.
  The "MTP drafter" and the "assistant drafter" are the **same mechanism** (a
  small ~4-layer model sharing the target's embedding table and last-layer
  activations, sharing the target's KV cache).
- Multimodal, but this workflow is **text-only**.
- Inference on this hardware is **memory-bandwidth-bound** (decode speed ≈
  bandwidth ÷ bytes-read-per-token).

### Priorities (strict order)

1. **Never swap memory** (swapping collapses throughput to <1 tok/s — unusable).
2. **Quality.**
3. **Speed.**
4. **Convenience.**

Willing to trade a _tiny_ amount of quality for a _significant_ speed gain.
KV-cache target ≈ 10k tokens — a rough figure chosen as a deliberate
over-estimate of the largest single-prompt context, so the never-swap budget has
margin rather than running close.

### Candidate workflows

- **Workflow A — 20-prompt pipeline.** ~20 model calls per clue, split roughly
  evenly between generation and validation, decomposing the task into guided
  steps; mix of thinking / non-thinking; fully scripted (never run by hand).
  Buys quality with inference-time orchestration + verification.
- **Workflow B — single-prompt pipeline + skill-distilled LoRA.** One call per
  clue; a LoRA trained on a database of high-quality clue/answer pairs
  internalizes the _cluing skill_. Required output is **fresh** clues
  (generalization), **not** retrieval/regurgitation of the database.
- **Workflow Hybrid — short pipeline + strong LoRA.** A few prompts (a light
  verification tail) on top of a strong LoRA. Workflow A doubles as the
  **offline data factory** that produces Workflow B's training set.

---

## 2. The search space

Three independent axes: **quantization × toolchain × acceleration**, plus
**fine-tuning** and **pipeline architecture** as separate decisions.

### 2.1 Quantizations (Q4 tier — see Section 3 for why Q4 is fixed)

GGUF (llama.cpp / Ollama / LM Studio ecosystem):

- **Unsloth QAT `UD-Q4_K_XL`** — QAT-based + Unsloth dynamic repack. Best
  quality-per-byte in GGUF; ~17–18 GB. _(top contender)_
- **Google official QAT `Q4_0`** — same QAT base, but plain Q4_0 packing
  under-performs Unsloth's dynamic version. Dominated.
- **Unsloth Dynamic 2.0 (non-QAT)** — best non-QAT dynamic on the bf16 base; ~20
  GB.
- **bartowski imatrix** — `Q4_K_M` ≈ 19.6 GB, `Q4_K_S` ≈ 18.2 GB. Reliable,
  battle-tested standard.
- **lmstudio-community** — bartowski-lineage repackaged for one-click LM Studio.
  Convenience.

MLX (mlx-lm / optiq / LM Studio MLX ecosystem):

- **mlx-community `OptiQ-4bit`** — sensitivity-aware mixed 4/8-bit; beats stock
  uniform 4-bit on every benchmark at ~same disk size; ~16.5 GB. **Specifically
  handles Gemma 4's Per-Layer-Embedding (PLE) problem.** _(top contender)_
- **mlx-community stock uniform 4-bit** — weak _for this model_: Gemma 4's
  PLE/ScaledLinear layers amplify uniform-quant error. Superseded by OptiQ.
  Avoid.

GPU-only (NOT runnable on the Mac — listed for completeness / future offload):

- AWX/AWQ-4bit, NVFP4, Intel int4-AutoRound. vLLM/CUDA path only.
  <!-- TODO: validate "AWX" — confirm whether it's a distinct method or a typo
  for AWQ; it may be a newer methodology. -->

**Ruled out:** 8-bit (~34 GB) does not fit 32 GB → would swap → violates
Priority #1. (And QAT 4-bit is already near-bf16, so 8-bit buys little.)

### 2.2 Toolchains

- **llama.cpp / `llama-server`** (GGUF) — grammars/JSON-schema constrained
  decoding, MTP spec-decode, prefix caching, rich metrics endpoint, portable to
  non-Apple hardware. _(top for GGUF)_
- **mlx-lm / `optiq serve`** (MLX) — native Apple Silicon; spec-decode via
  assistant drafter; prompt caching. Use `optiq serve` (or mlx-vlm), **not**
  vanilla `mlx_lm.server`, to get MTP — several loaders don't register Gemma 4's
  drafter arch. _(top for MLX)_
- **mlx-openai-server** (MLX) — continuous batching, decode-concurrency,
  prompt-cache sizing. Only worth it if concurrency is needed (it isn't here).
- **vllm-mlx** (MLX) — throughput leader on Apple Silicon, but has had
  Gemma-family misclassification bugs (disabled prefix caching). Verify before
  trusting.
- **Ollama** (currently in use) — convenient, but hides MTP/drafter config,
  gives coarse cache control, and owns the chat template (awkward for per-step
  thinking toggles).
- **LM Studio** — convenience GUI/daemon; its MLX backend **can't combine
  speculative decoding with batching**. A sidegrade from Ollama, not an upgrade.

### 2.3 Acceleration techniques

- **MTP speculative decoding** — the biggest lever; **lossless** (target
  verifies every token). Up to ~2–3× in the ideal case, but
  **content-dependent**: the drafter is code-tuned, so prose-like clue
  generation yields lower acceptance and lower speedup (can approach 1× on terse
  steps). **Always measure acceptance rate per pipeline step.**
- **Flash attention (Metal)** — effectively free, keep on; prerequisite for
  KV-cache quantization.
- **Prefix / prompt caching** — pipeline-level win across the 20 calls;
  **front-load the invariant prefix** so it cache-hits.
- **Prefill batch tuning** (`-b`/`-ub`) — minor, free.
- **KV-cache quantization** — _marginal_ on GGUF here (KV is already tiny);
  **blocked on MLX** for Gemma 4 (mixed-precision KV fails on shared-KV
  attention) → MLX runs **fp16 KV**.
- **Fine-tuning (LoRA/QLoRA)** — a _quality_ lever; near-free on inference RAM
  (+~0.3 GB unfused) and speed (≤3%). See Sections 3 and 4.

---

## 3. Effective end-to-end analysis

### 3.1 What is FIXED by the hardware/constraints (stable across re-runs)

- **Q4 quantization tier.** 8-bit doesn't fit 32 GB; Q4 (~16–18 GB weights) is
  the operating point.
- **Never-swap budget holds for all Q4 configs.** Typical total ≈ **23–25 GB**
  (weights + ~4.5 GB OS overhead + sub-1 GB KV + ~1.5 GB compute buffers + ~1 GB
  MTP drafter), leaving ~7–9 GB headroom on 32 GB.
- **KV cache is not the binding constraint** — Gemma 4's sliding-window +
  unified-KV makes 10k tokens sub-1 GB.
- **Memory bandwidth (~120 GB/s) sets the absolute speed ceiling.** Decode is
  bandwidth-bound.
- **Local fine-tuning of 31B is infeasible** — 32 GB can train ~12B-class at
  most; 31B training gradients exhaust memory. Training must happen off-machine
  (cloud or borrowed ≥48–64 GB Mac).
- **The model is fixed** (Gemma 4 31B dense) until a clearly-better _local_
  model appears.

### 3.2 What is VARIABLE / fast-moving (RE-RUN PERIODICALLY)

> **The best options in this space change rapidly, and the current best is
> almost always _newer than any model's training cutoff_. Do not trust a model's
> built-in knowledge for these — search/verify current state each time.**

Re-validate at least these:

- **Best Q4 quant** (QAT vs sensitivity-aware vs new methods; vendors keep
  shipping improvements).
- **Toolchain maturity & bug status** (especially MLX loader/feature gaps, which
  were live as of this writing).
- **Accelerator support** (MTP implementation quality; KV-quant fixes; new
  spec-decode methods).
- **Cloud GPU prices** (trending down; verify before each training campaign).
- **The model itself** (Gemma 5+ / a better local model may reset the whole
  analysis).

### 3.3 The re-runnable procedure

1. **Confirm the model.** Is Gemma 4 31B still the best _local_ model for this
   task? Check new releases.
2. **Derive the quant tier** from the memory budget (weights + ~4.5 GB OS +
   sub-1 GB KV + ~1.5 GB buffers + ~1 GB drafter must fit 32 GB with headroom →
   Q4).
3. **Enumerate current Q4 quant candidates** per ecosystem (QAT,
   sensitivity-aware mixed, imatrix).
4. **Pick a toolchain** per ecosystem; check current bug/maturity status (don't
   assume last run's status holds).
5. **Identify applicable accelerators**; verify which actually work for _this_
   model _now_ (e.g. KV-quant was blocked on MLX for Gemma 4).
6. **Quantify** RAM / tok/s / relative quality — measure where possible; clearly
   label estimates.
7. **Decide the fine-tuning path** (cloud-train / local-infer; source data from
   your own pipeline).
8. **Decide the pipeline architecture** (orchestration vs distilled single-shot
   vs hybrid).

### 3.4 Durable reasoning principles (transferable across re-runs)

- **Bandwidth-bound regime:**
  `tok/s ≈ (bandwidth × efficiency) ÷ bytes-read-per-token`. Lower bandwidth
  lowers _absolute_ speed but does **not** hurt — slightly _helps_ — the
  speculative-decoding multiplier.
- **Speculative decoding (MTP) payoff grows the more bandwidth-starved you are**
  (the verify of K tokens is hidden under longer memory stalls). It is eroded
  only by **low acceptance** (content-dependent), not by bandwidth. So expect a
  comparable-or-better _multiplier_ than higher-end Macs, on a lower absolute
  baseline.
- **Fine-tuning closes _style/alignment_ gaps, not _capability_ gaps.** LoRA
  steers existing capability; it does not install new capability.
- **MoE vs dense:** the 26B (Gemma 4's MoE sibling in the same release, raised
  here only as the cheaper-but-weaker alternative the dense 31B is chosen over)
  is MoE with ~3.8B _active_ params/token vs the 31B's 30.7B active.
  Reasoning-heavy, single-pass tasks (like cluing) expose this; fine-tuning
  cannot close an architectural active-param ceiling.
- **Pipeline length ∝ 1 / generator quality.** A 20-prompt pipeline's value is
  mostly verification/search; a strong LoRA lets you collapse orchestration.
  **Single-shot exposes raw per-token capability**, so collapse the pipeline on
  the _dense_ model, not the MoE.
- **Distillation pattern:** run the expensive orchestration _offline_ to build a
  high-quality dataset → train a LoRA → deploy cheap single-/few-shot inference.
  The pipeline that scores quality also generates the training data.
- **Keep inference behind an OpenAI-compatible boundary** → the model/toolchain
  choice stays _reversible_ (llama-server ↔ mlx-lm swap with near-zero pipeline
  change). This lowers the stakes of every choice above.

---

## 4. Top contenders — as of 2026-06-20

> **Timestamped snapshot. Expect this section to be the first to go stale.
> Re-run Section 3.3 before relying on it.**

### 4.1 The two finalists (one per ecosystem)

1. **GGUF:** Unsloth **Gemma-4-31B QAT `UD-Q4_K_XL`** on **`llama-server`**.
2. **MLX:** mlx-community **Gemma-4-31B `OptiQ-4bit`** on **`mlx-lm` /
   `optiq serve`**.

Quality between them is a wash today (QAT has a slight theoretical edge; within
noise). Break the tie on ecosystem alignment with fine-tuning (Section 4.3) or
on whichever you'll instrument fastest. **Given live MLX bugs at this writing,
`llama-server` is the faster path to a working, observable setup.**

### 4.2 Quantified comparison (base M4 Air, 32 GB, 10k KV)

Confidence: **weights = high; RAM = medium (±~2 GB); tok/s = low/medium (±~50%);
quality = constructed/ordinal.** tok/s is extrapolated from a measured ~15–25
tok/s for 31B-Q4 on an M4 Pro (273 GB/s), scaled by bandwidth (~120/273) and
sanity-checked against first principles. The slight MLX-over-GGUF edge in the
base rows reflects estimated Metal kernel efficiency plus reported numbers, not
a measurement — both are bandwidth-bound at the same ~120 GB/s, so confirm or
erase the gap with a local A/B run.

| Config (model · MTP · LoRA)    | Quant weights | Workflow RAM (incl. OS) | Decode tok/s (est.) | Rel. quality (est.) |
| ------------------------------ | ------------- | ----------------------- | ------------------- | ------------------- |
| QAT-GGUF · no MTP · no LoRA    | ~17 GB        | ~23–24 GB               | ~5–8                | 100 (ref)           |
| QAT-GGUF · no MTP · **+LoRA**  | ~17 GB        | ~23–24 GB (+~0.3)       | ~5–8                | ~120 \*             |
| QAT-GGUF · **+MTP** · no LoRA  | ~17 GB +draft | ~24–25 GB               | ~7–12 †             | 100                 |
| QAT-GGUF · **+MTP · +LoRA**    | ~17 GB +draft | ~24–25 GB (+~0.3)       | ~7–12 †             | ~120 \*             |
| OptiQ-MLX · no MTP · no LoRA   | ~16.5 GB      | ~23 GB                  | ~6–9                | ~98                 |
| OptiQ-MLX · no MTP · **+LoRA** | ~16.5 GB      | ~23 GB (+~0.3)          | ~6–9                | ~118 \*             |
| OptiQ-MLX · **+MTP** · no LoRA | ~16.5 GB +dr. | ~24 GB                  | ~7–11 †             | ~98                 |
| OptiQ-MLX · **+MTP · +LoRA**   | ~16.5 GB +dr. | ~24 GB (+~0.3)          | ~7–11 †             | ~118 \*             |

`\*` LoRA quality is **directional only** — the real magnitude depends entirely
on your dataset and is the point of doing it. `†` MTP speedup is
content-dependent; can fall to ~1× on terse/low-acceptance steps — **measure
acceptance rate.**

Two facts the table encodes:

- **MTP changes quality by zero** (lossless) — the +MTP rows equal their non-MTP
  twins.
- **LoRA is a near-free quality lever** — negligible RAM/speed cost; it's the
  only quality column-mover.
- **All eight configs fit with ~7–9 GB headroom → none swap** (Priority #1
  satisfied everywhere).

Dimensions that aren't rows but matter: **thinking mode** (dominates effective
throughput via tokens-per-clue, not via tok/s) and **prefill /
time-to-first-token** (with 20 calls/clue and short outputs, prefill can
dominate wall-clock — favor prefix-cache structuring over chasing decode tok/s).

### 4.3 Fine-tuning recommendation

- **31B fine-tuning cannot run on the Air.** Required path: **cloud-train →
  local-infer.** A single **A100 80GB** (~$1–2/hr on-demand on budget clouds;
  spot lower) runs 31B QLoRA comfortably; a typical run is **~30 min–2 hr ≈
  $2–10**; a full dev cycle of 10–20 runs ≈ $20–100. You carry back only a
  **few-MB LoRA adapter**, so the deployed generator stays 100% local.
- **Alternative — borrowed 64 GB M1:** clears the memory bar (and if it's a
  MacBook Pro/Studio, the fanless thermal problem disappears), but an M1 is
  ~5–10× slower than an A100 → a 31B LoRA run is **several hours to overnight**.
  Good for a free, fully-local _final_ run or a one-shot pipeline validation;
  bad for iteration. (M1 Max ~400 GB/s vs M1 Ultra ~800 GB/s — confirm which;
  Ultra ~halves run times.)
- **Iterate on a 12B proxy:** your own 32 GB Air _can_ train a ~12B-class
  Gemma 4. Debug the harness, data format, and eval loop there with fast local
  runs; commit the final **31B** run to cloud/borrowed-M1. The model you iterate
  on need not be the model you ship.
- **Serve quantized-base + adapter (QLoRA on the 4-bit base)** to **preserve the
  QAT/OptiQ quant.** Do **not** fuse-then-requantize — that downgrades your QAT
  lattice to a self-made PTQ and gives back the quality edge.
- **Config caveat:** more training RAM buys comfort (batch size, sequence
  length, no swap), **not** a precision upgrade. Since you serve 4-bit, train
  QLoRA against that same 4-bit base for train/serve alignment.
- **Data source:** your existing generate-and-judge pipeline is a **data
  factory** — rejection-sample its best outputs to build the training set; this
  aligns the tuned model to your own quality bar.
- **Bonus — fine-tune the MTP drafter** on your clue domain: reported ~×2.5
  acceptance on domain data. Since low acceptance is what erodes your MTP
  speedup on prose, a domain-tuned drafter directly buys back speed. The drafter
  is tiny (~4 layers) → cheap, possibly even locally trainable.

### 4.4 Pipeline architecture recommendation

- **Workflow A (20-prompt)** maximizes quality and is the data factory — but on
  this hardware it's roughly **minutes per clue → hours per ~75-clue puzzle.**
  Caveat: this estimate assumes burst-rate decode, but an hours-long puzzle run
  is _sustained_ load on the fanless Air — exactly the regime Section 1 flags as
  thermally throttling. Real wall-clock could run longer than the burst-rate
  figure implies; **measure sustained decode tok/s locally** before trusting the
  per-puzzle number.
- **Workflow B (single-prompt + distilled LoRA)** is **~30–100× faster per
  clue** (one call, short output), but trades away per-instance verification
  (fatter defect tail) and risks **regurgitation** — note LoRA _learns the
  cluing skill from_ the database; it does not _store_ it, and over-training
  tips skill → memorization. Needs anti-memorization discipline (dedup, hold out
  answers, early stop, novelty eval).
- **Recommended: Hybrid.** Strong LoRA (distilled from A's best output) + a
  **short verification tail** (2–3 prompts, not 20) to recover the reliability
  floor and screen for regurgitation. Most of B's speed, most of A's floor. The
  number of prompts you need shrinks as the LoRA improves.
- **Decision hinge = volume:** at scale, A is near-impractical on this hardware
  → hybrid/B is needed; for a small artisanal batch, A's reliability floor is
  worth the minutes.

### 4.5 26B (MoE) vs 31B (dense) — quality gap under fine-tuning

- Observed **without** fine-tuning (workflow-specific): ~**100 vs ~60**.
- But general benchmarks show only a **~2–3% gap** (Arena ELO ~1452 vs ~1441). A
  large _workflow_ gap against a tiny _general_ gap is the tell: the gap is
  **capability-driven** (the MoE's ~3.8B active path failing on cluing's
  per-token reasoning), **not** style-driven — i.e. the **sticky** kind
  fine-tuning can't fix.
- **Estimated residual gap after fine-tuning both:** ~**50–70%** of original
  under single-shot; ~**30–50%** under heavy orchestration (the scaffold masks
  the capability deficit). Roughly **12–28 points** remain.
- **Implication:** the residual gap is smallest where you least need it (heavy
  orchestration) and largest exactly where you want to go (single-shot). **If
  you collapse the pipeline, do it on the dense 31B.** The 26B's ~3–4× speed
  edge only cashes out if you prop it up with orchestration — which gives the
  speed back.
- **Cheap experiment:** tune both on the same held-out set and measure — the gap
  that remains _is_ the capability component, by definition.

---

## Appendix: confidence & provenance notes

- **Measured / sourced** (as of 2026-06-20, via web research): model
  architecture & release; quant file sizes; M4-Pro 31B-Q4 tok/s anchor; MoE
  active-param count; Arena ELOs / "2–3% behind" benchmark gap; cloud GPU
  prices; local-training memory ceilings; MLX KV-quant / loader limitations.
- **Modeled estimates** (clearly flagged in text): base-M4 tok/s
  (bandwidth-scaled), workflow RAM totals, MTP effective multiplier on prose,
  per-clue/per-puzzle wall-clock.
- **Constructed/ordinal** (lowest confidence): all relative-quality numbers,
  including the LoRA uplift and the 26B-vs-31B residual gap. These are
  reasoning, not measurement — convert them to measurements with your own eval
  harness where they're load-bearing.
