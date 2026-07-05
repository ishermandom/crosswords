# Pending tasks

Status key: `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` dropped ·
`[?]` uncertain/speculative

---

## Housekeeping

**Goal:** Clean up local model storage once QAT models are validated as the
preferred quantization.

- [ ] **Keep `cluegen/local/README.md` references up to date** — add links as
      good resources are found; remove ones that turn out not to be useful. Be
      selective: only include sources worth coming back to.

- [ ] **Delete MLX models from Ollama** (`gemma4:26b-mlx`, `gemma4:31b-mlx`)
      once the QAT variants (`gemma4:26b-qat`) are confirmed stable. MLX models
      are the fallback if a QAT issue comes up.

- [ ] **Retire the old Ollama store path** — the store moved to
      `/Users/Shared/models/gguf` (2026-07-02, shared-storage layout).
      `ceiling.md`'s cutover is done (main + local-ceiling worktree, verified
      2026-07-02) and the old store's contents are deleted; all that remains is
      the empty directory shell. User-run (sandbox lacks write on the parent):
      `rm -rf /Users/Shared/ollama`

- [ ] **Reinstall the venv's editable `clue-gen` from the main checkout after
      the `finetune-probe` branch merges** — the 2026-07-02 reinstall (which
      fixed the editable-install config and the broken `clue-gen` console
      script) ran from the probe worktree, so the venv's `.pth` resolves
      `cluegen.local` from `/Users/Shared/code/crosswords-finetune-probe`. Once
      that worktree is deleted, imports dangle. Fix:
      `cd /Users/Shared/code/crosswords/cluegen &&     pip install -e ".[dev,finetune]"`

---

## Git workflow

**Goal:** Implement the agent-managed git workflow (strict-linear main,
structural history preservation). Spec and full rationale: `docs/git-workflow/`.

- [ ] **GitHub rulesets** (user-run, GitHub UI): `main` → require linear
      history + block force pushes + block deletions, scoped to `main` only —
      and retire the current all-branches no-merge-commits rule;
      `refs/archive/**` → creation allowed, updates and deletions blocked.
- [ ] **Auto-archive Action** — `.github/workflows/archive-rewrites.yml`: on
      force-push and ref-deletion events, snapshot the `before` SHA to
      `refs/archive/<branch>/<utc-timestamp>` via the API. The dragnet layer;
      verify by force-pushing a throwaway branch and checking the archive ref
      appears.
- [ ] **Land script** — `scripts/land.py`: replay → presubmit (full suite once;
      per-commit flag) → FF-push main → archive superseded chain → reset branch
      onto main. Includes the archive recovery drill in its docs (one
      `ls-remote` pattern, one fetch/diff example). Depends on the rulesets
      existing (FF-rejection behavior).
- [ ] **Dotfiles migration** (after dotfiles construction settles): move
      `docs/git-workflow/` + `land.py` to dotfiles as the all-repos standard;
      add ruleset assertions to `gh-protect.sh`; narrow the git gate to
      lease-only-off-main (spec, Enforcement layer 4); enable `rerere` in global
      git config; roll rulesets + Action out to remaining personal repos.

---

## Fine-tuning probe

**Goal:** directional go/no-go on whether a locally QLoRA-tuned small Gemma
beats prompted-26B v9 as setter, in confirmed-bankable clues per GPU-minute.
Spec (decisions, stages, gates): `finetune.md`. Intended to run in its own chat
thread; the spec is self-contained.

- [x] Stage 0 — plumbing: `e2b-it-OptiQ-4bit` + ~500 pairs; `mlx_lm.lora` train
      → `optiq serve --adapter` → eval loop runs end to end. Completed
      2026-07-02. Model selection settled 2026-07-02 (see spec); E2B checkpoint
      is in the shared cache (`HF_HUB_CACHE=/Users/Shared/models/mlx`), 12B pull
      in progress. The user personally runs model/data downloads from a shopping
      list Claude supplies. Sub-step record:
  - Done 2026-07-02: `finetune` optional-dependency group in
    `cluegen/pyproject.toml` (`mlx-lm`, `mlx-optiq`), installed in the sandbox
    venv at 0.31.3 / 0.2.10; imports and both CLIs verified.
  - Done 2026-07-02: 500/50 train/valid slice built by
    `scratch/finetune/build_slice.py` (data/ gitignored); one clue per answer,
    answer-split, panel + held-out answers excluded and verified absent.
  - Done 2026-07-02: chat-template formatting verified via the checkpoint's own
    template — Gemma 4's turn tags are `<|turn>` / `<turn|>` (not Gemma 1–3's
    `<start_of_turn>`); exactly one BOS, no doubling under default tokenization.
    mlx-lm applies the template itself to messages-format JSONL.
  - Done 2026-07-02: sanity training confirmed — OptiQ-as-base trains under
    stock `mlx_lm.lora` (QLoRA auto-engaged, 0.147% trainable); 20 iters at
    batch 1: val loss 8.85 → 2.49, ~5 it/s, ~160 tok/s, peak 4.9 GB. Serve leg
    smoked too: `optiq serve --adapter` answered an OpenAI-style chat completion
    with the trained adapter.
  - Done 2026-07-02: eval client `scratch/finetune/eval_tuned.py` — standalone
    per prototyping independence (panel, judge prompt, and schema copied from
    the local-ceiling harness, not imported; no cross-branch edits). Bare
    single-turn setter via `optiq serve`, screen judge via Ollama
    (`gemma4:26b-qat`, same contract as the pipeline). Smoked end to end on 2
    panel words: generations screened, verdicts recorded to
    `scratch/finetune/evals/`. Clue quality was garbage as expected at 20 sanity
    iterations; stage 1 is the real read.
  - GPU coordination: the local-ceiling thread holds most of GPU/RAM; E2B-scale
    work fits alongside, but check with the user before anything heavier
    (scheduling protocol still TBD).
- [x] Data design round — settled 2026-07-02; see `finetune.md` (Data source,
      Difficulty conditioning, Curation recipe, Slice size bullets).
- [ ] Stage 1 — probe: QLoRA `12B-it-qat-OptiQ-4bit` on 5–20k curated pairs;
      evaluate via the eval client (bare single-turn and scaffolded); Fable
      spot-check <$2. Depends on stage 0 (done). Sub-steps, in order:
  - Done 2026-07-02: corpora pulled to `/Users/Shared/data/` (Kaggle CSV
    verified: 781,573 rows; doshea clone; xd moved alongside).
  - Done 2026-07-02: slice builder `scratch/finetune/build_stage1_slice.py`
    implements the spec recipe; prompt template frozen in
    `scratch/finetune/prompts.py` (shared with `eval_tuned.py`, which now takes
    `--difficulty`). Provisional 10k slice built and verified: funnel 543,762
    pairs after dedup / 62,955 answers; train 10,000 pairs / 3,444 answers,
    buckets 15/54/31% (matches weekday-weight prediction), 2,232 contrast
    answers, median year 2010; valid 1,382 pairs / 500 answers. Rebuild at the
    final `--size` once 12B timing lands.
  - Done 2026-07-02 (user-cleared): 12B sanity steps. Stock `mlx_lm.lora`
    rejected the checkpoint (`model_type: gemma4_unified` unknown to mlx-lm
    0.31.3); switched to the spec's recorded fallback
    `optiq lora train --rank-scaling constant --preset default`, which registers
    the remap — loads and trains cleanly (val loss 12.99 → 5.40 over 20 iters).
    Timing anchor at batch 1: ~0.21 it/s, peak 9.9 GB (32 GB machine — optiq's
    "10% of total RAM" log line is misleading; user-corrected).
  - Done 2026-07-02 (user-cleared): batch-4 timing run — 0.059–0.062 it/s × 4 ≈
    0.24 examples/s vs batch 1's 0.21: only ~15% gain for +0.6 GB, so batch
    stays 1 (and keeps 4× more optimizer steps per epoch). Slice sized at 5,000
    pairs (~6.6 bench-hours; thermal margin for the fanless overnight) and
    rebuilt: 1,712 answers, buckets 16/54/30%, 1,119 contrast answers, median
    year 2010; valid unchanged (1,382 pairs / 500 answers).
  - Overnight train (user-gated; footprint ~10 GB, ~7–8 h). Launch procedure for
    a fresh session:
    1. Acquire the machine-wide compute lease (protocol in the script
       docstring). No `--pid` — the trainer doesn't exist yet; the 480-min
       estimate times the grace factor is the staleness backstop:
       `python cluegen/local/compute_lease.py acquire --holder finetune --task 'stage-1 overnight' --minutes 480`
    2. Launch detached (`project-detached-runs` memory): the Desktop app kills
       the session's process group after ~15 min hidden, so a plain Bash command
       — backgrounded or not — dies mid-run. From `cluegen/scratch/finetune/`:
       `python3 -c "import os, subprocess; env = dict(os.environ, HF_HUB_CACHE='/Users/Shared/models/mlx'); p = subprocess.Popen(['caffeinate', '-is', os.path.expanduser('~/.venvs/default/bin/optiq'), 'lora', 'train', 'mlx-community/gemma-4-12B-it-qat-OptiQ-4bit', '--data', 'data_stage1', '-o', 'adapters_12b_stage1', '--rank-scaling', 'constant', '--preset', 'default', '--batch-size', '1', '--iters', '5000'], env=env, stdout=open('train_stage1.log', 'w'), stderr=subprocess.STDOUT, start_new_session=True); print(p.pid)"`
    3. Attach an expendable background watcher on the printed pid — poll
       `kill -0 <pid>` every minute; when the trainer exits, run
       `python cluegen/local/compute_lease.py release --holder finetune`. A
       reaped watcher is harmless: the detached trainer keeps running, a fresh
       watcher can re-attach, and lease expiry covers a lost release. Progress
       readable any time via `tail train_stage1.log`.
  - Morning-after protocol, in order: (1) loss curve + best-checkpoint val; (2)
    loss-gap diagnostics (`scratch/finetune/loss_gaps.py`) base vs tuned —
    answer-shuffle gap measures answer-conditional content learning,
    difficulty-swap gap measures whether the conditioning token is load-bearing;
    shape-only learning = val loss fell but gaps didn't grow. The register
    control (WordNet flat definitions) adds: register separation (definitions −
    real clues; growth = quality not flatness) and the flat-under-hard penalty
    (difficulty token acting on register). Baseline (2026-07-02, n=200 + 103
    definitions): base — true 9.99, answer gap +0.59, difficulty gap −0.19
    (noise), register sep −1.38, flat@hard +0.84; 20-step adapter — true 6.37,
    answer gap +0.19, difficulty gap +0.00, register sep −0.55, flat@hard +0.02.
    Reading: early training is shape-dominated; it diluted answer-conditioning
    and erased the base's difficulty sensitivity (both difficulty instruments
    agree), while register separation moved the right way (−1.38 → −0.55),
    likely partly residual shape (definitions run longer than real clues).
    Overnight content bars: answer gap past +0.59; difficulty gap clearly
    positive; flat@hard recovering past +0.84; register sep continuing toward 0;
    (3) panel eval at medium via `eval_tuned.py` + screen; (4) steering
    spot-check (same answers at easy vs hard); (5) decision-metric read:
    confirmed-bankable per GPU-minute vs v9.
  - Done 2026-07-03: overnight run completed — 5,000 iters in 6.9 h, no thermal
    drift, peak 9.9 GB. Val curve: 13.86 → plateau ~4.6–5.2 from ~iter 2200;
    best val 4.647 at iter 2799 (auto-kept in `adapters_12b_stage1/best/`);
    final 4.899.
  - Done 2026-07-03: loss-gap diagnostics on best checkpoint (n=200 + 103
    definitions): true 5.830, answer gap +0.001, difficulty gap +0.001, register
    sep +0.688, flat@hard +0.002. Every content bar missed: the answer gap
    collapsed monotonically with training (+0.59 base → +0.19 at 20 steps →
    +0.001 at 2799) while register was fully learned (separation crossed zero —
    real clues now outscore flat definitions). Reading: the tuned model writes
    clue-register text while ignoring the prompt — both the answer and the
    difficulty token. Open discrepancy to reconcile: trainer's best val 4.647 vs
    the script's true-condition 5.830 on the same val distribution (token
    weighting? subset?). No stage-1 verdict until the discrimination ladder
    (task below) separates "model really ignores the prompt" from "measurement
    artifact".
- [x] Conditioning-collapse discrimination ladder — resolved 2026-07-03 at rungs
      (a)–(c); (d)/(e) fold into the next-run design below.
  - Done (a): masking is loss-only (optiq delegates to mlx-lm ChatDataset;
    prompt tokens stay in the input) — the model saw every answer. The
    4.647-vs-5.830 val discrepancy is the trainer's 25-example in-file-order val
    subset plus min-over-noisy-estimates selection bias; the script's
    200-example seeded measurement is the trustworthy one. No mechanical
    exoneration.
  - Done (b): generation probe, two paths. Via `optiq serve`: the literal string
    'An double' for every panel word, every difficulty, even at temperature 1.0
    (4/4 identical — the server likely ignores sampling parameters; side
    mystery, logged, not load-bearing). Via direct `mlx_lm.load` (the scorer's
    path): greedy gives '"""s'; temperature 1.0 gives varied word salad with
    malformed subwords ('Pickyt athletic car', 'Needrettitch'). Broad
    distribution consistent with the 5.83-nat score; content degenerate. The
    adapter is genuinely damaged, not mismeasured.
  - Done (c, partial): iter 400 gaps: answer −0.001, difficulty +0.000 —
    collapse complete by step 400 (vs +0.19 at 20 steps, +0.59 base). The 1400
    point was killed mid-run during the lease-overlap incident (below) and is
    not needed: 20 → 400 brackets the death.
  - Verdict: training destroyed prompt-conditioning within ~400 steps and
    autoregressive coherence along with it, while teacher-forced loss kept
    improving — the signature of an over-hot update rate. Suspect #1: LR
    2.000e-04 constant, batch 1, no warmup, no decay (the preset default, never
    tuned for this). Amplifier: a single fixed prompt template, so every step
    pushes the same pathway. Next-run design (rehearse on e2b first, per the
    task below): LR sweep starting ~1e-5–5e-5 with warmup + cosine decay;
    prompt-template variety (several phrasings); sanity-check generations + gaps
    at step ~200 before committing to a long run. The capacity-vs-data pair and
    the 26B loss anchor stay deferred until a non-degenerate run exists to
    compare against.
  - Incident (2026-07-03, lesson for every detached batch): the diagnostics
    batch was leased for 50 min but overran (per-step model reloads + the
    definition control running over all val answers); the lease expired at 15:03
    mid-step, ceiling legitimately acquired at 15:04 and loaded 31b, and our
    still-running step overlapped it — memory pressure until the step was killed
    at ~15:08. Rule going forward: size lease estimates to worst case including
    model-load overhead per step, and make drivers self-terminate at lease
    expiry rather than trusting the estimate.
  - Done 2026-07-03 (rehearsal run 1/4, e2b at LR 2e-4, deadline-capped at ~560
    iters, best = 400): the collapse did NOT reproduce. e2b base: true 8.543,
    answer gap +0.740, register sep −0.978. e2b tuned: true 3.669, answer gap
    +0.630, difficulty gap −0.000, register sep +0.006; generations coherent and
    on-answer (VIOLET → 'Purple', 'Berry blue'; flaws: greedy answer-echo
    'Score' for SCORE, difficulty token still inert). Same data/trainer/LR/steps
    as the 12B whose gap was +0.001 at iter 400 — so LR alone is not the killer,
    e2b cannot proxy-clear 12B runs, and suspicion moves to the 12B QAT-OptiQ
    path itself (QAT checkpoint × LoRA interaction, or the unified export's
    gemma4_unified remap). Also suspicious: tuned e2b fits val clues at 3.67
    nats vs the tuned 12B's 5.83. Side note: tuned e2b's ps RSS 4.4 GiB
    validated the lease script's new process-table busy check against live MLX
    (main's copy only — worktree copies gain it at their next merge-from-main).
  - Run 2/4 launched 2026-07-04 00:05: 12B at LR 5e-5, 250 iters, evals on the
    final adapter. Decision tree: healthy answer gap → the QAT 12B is
    LR-fragile, train colder and the overnight recipe is salvageable; dead gap →
    LR exonerated, the 12B base export is implicated and the next move is a
    different base checkpoint, not more tuning. Mechanics fix from run 1: the
    caffeinate wrapper lingered ~88 min after the script finished (leaked
    multiprocessing resource tracker), so the pid-keyed watcher released 88 min
    late; run-2+ watchers key on the driver log's `done` marker instead.
  - Done 2026-07-04 (run 2/4, deadline-capped ~220 iters): LR-fragility
    CONFIRMED — the QAT 12B at 5e-5 is the best model of the probe. True 3.162
    (overnight-2e-4 best: 5.83), answer gap +1.318 (base +0.59 — conditioning
    strengthened, not just preserved), register sep +0.007, val 2.719 at iter
    200 (the 7-h overnight never beat 4.647). Generations coherent and on-answer
    (SCORE → 'Win', 'Gamble', "Ringer's aim"). Verdict: 2e-4 sits past the
    QAT-OptiQ 12B's stability cliff (e2b tolerates it; the QAT export doesn't);
    base checkpoint exonerated; recipe salvageable by LR alone. Difficulty token
    inert in every run — a stage-2 data/conditioning question, not an LR one.
    Budget stopped at 2/4: without a trainer resume flag, a third boxed run
    cannot exceed run 2's iteration horizon, and the remaining risk (delayed
    collapse past ~220 iters) is covered by the overnight re-run itself —
    checkpoints land every 100 iters, so the morning protocol adds a gap-trace
    across them (evaluate `--adapter` on 3–4 checkpoint dirs) before trusting
    the final adapter.
  - Next — USER-CLEARED 2026-07-04 (green light given; launch is the next action
    after the session compact). Overnight 12B re-run at 5e-5, from
    `cluegen/scratch/finetune/` in the probe worktree:
    1. `python cluegen/local/compute_lease.py acquire --holder finetune --task '12B overnight re-run at 5e-5' --minutes 600`
       — sized for the full run plus eval-and-release slack; the ceiling thread
       queues tasks behind this run, so release promptly on completion.
    2. Launch detached under caffeinate (per project-detached-runs memory):
       Popen(`['caffeinate', '-is', <venv>/bin/optiq, 'lora', 'train', 'mlx-community/gemma-4-12B-it-qat-OptiQ-4bit', '--data', 'data_stage1', '-o', 'adapters_12b_stage1_lr5e5', '--rank-scaling', 'constant', '--preset', 'default', '--batch-size', '1', '--iters', '5000', '--learning-rate', '5e-5']`,
       stdout to `train_12b_lr5e5.log`, `start_new_session=True`), with
       `HF_HUB_CACHE=/Users/Shared/models/mlx` in env.
    3. Watcher keys on trainer pid AND releases the lease on exit (the trainer
       process is the done signal here; for multi-step drivers use the log's
       `done` marker — the caffeinate wrapper can linger after work ends, run-1
       lesson). Re-attach on reaping. Morning protocol as recorded above, with
       these updates from the register-preference discussion (2026-07-04):
       flat-under-hard is a HEADLINE content bar (base +0.84; every adapter so
       far ≈0 — recovery toward +0.84 = the model re-learning that flat text is
       wrong under a hard prompt); add the checkpoint decoupling trace —
       loss_gaps on 3–4 checkpoint dirs, watching for real-clue loss and
       definition loss SPLITTING (falling together = still treating registers as
       equals). Val-based best/ keeper handles early best-val (5e-5 hit 2.72 by
       iter 200). Budget note: boxed-run budget stood at 2/4 used when the
       overnight was cleared.
  - Done 2026-07-04 (overnight re-run at 5e-5, launched 01:22 via probe_run.sh
    so the gen probe + loss gaps ran inside the lease; lease released by the
    done-marker watcher on completion). All 5,000 iterations, no collapse: best
    val 1.898 at iter 3399, late-run val oscillating 1.9–2.4 (noise, not
    divergence). Final-adapter gaps (n=200): true 2.635, answer gap +1.790 (base
    +0.59, run-2 +1.318 — conditioning kept strengthening), difficulty gap
    +0.011 (still inert), register sep +0.372 (base −1.38 — crossed zero:
    definitions now LESS likely than real clues), flat@hard +0.030 (headline bar
    NOT met; base +0.84). Generations in clue register and varied: VIOLET →
    'Color of the 1990s', 'Flower in a wreath', 'Periwinkle'; SCORE →
    'Scoreboard' (invalid — contains the answer), 'Rating: Abbr.', 'Sporting
    need'. Scorecard vs the overnight content bars: answer gap ✅, register sep
    ✅, difficulty gap ❌, flat@hard ❌ — both misses are the known inert
    difficulty token (stage-2 data/conditioning), not training health. Remaining
    morning protocol (each needs a lease + user go-ahead): gaps on best/
    (iter 3399) vs final, checkpoint decoupling trace, panel eval at medium,
    steering spot-check, decision vs v9.
  - Done 2026-07-04 13:26–13:46 (morning analyses, 2 of the 4-task user budget;
    driver morning_run.sh; lease waited behind the ceiling thread's stale 31b
    until the user pinged that session to unload). Best-vs-final at full n=200:
    statistically equivalent (best: true 2.621, answer gap +1.665, register sep
    +0.397; final: 2.635 / +1.790 / +0.372) — carry the FINAL adapter forward;
    the trainer's val-keeper preference for iter 3399 was 25-example noise.
    Decoupling trace (n=40, matched subset, iters 400/1400/2400/5000): real-clue
    loss fell monotonically 2.64 → 2.53 → 2.50 → 2.40 while definition loss held
    flat at ~2.9–3.1 — the registers DID split, and register sep grew through
    training (+0.22 → +0.55 → +0.51 → +0.64), still rising at the 1-epoch mark.
    Reading: register preference is being learned and had not plateaued; more
    data/epochs should push it further. flat@hard ≈0 at every checkpoint —
    difficulty conditioning never engages at any point in training, cementing
    the stage-2 diagnosis. Runs finished ~2× faster than the 25-min planning
    estimate (~9 min for full-n gaps on an otherwise-empty machine); future
    lease sizing can assume ~10 min per full-n gaps run plus load time.
    Remaining (2 budget tasks): panel eval at medium + steering spot-check,
    decision metric vs v9.
- [ ] AUTONOMOUS STRETCH (granted 2026-07-04, pre-compact; user away). Execute
      every queued task that precedes the 15k overnight rung, in this order: 1.
      Stratified false-signal check (~15 min, tuned adapter). 2. mlx-lm launcher
      build (code only). 3. One boxed session: batch-size exploration on e2b (1
      vs 2 vs 4 — tokens/sec, peak memory, loss smoothness) + learning-rate
      range test ON THE 12B via the launcher (user decision 2026-07-04: 12B
      directly, overriding the e2b-rehearsal reminder for this ramp — the QAT
      12B's cliff is the one that matters). 4. Matched-pair
      difficulty-preference instrument (reframed 2026-07-04: weekday proxies
      difficulty, not liveliness): build + run base vs tuned (pulled up
      2026-07-04 to precede the 15k rung, so the ladder measures difficulty
      preference from the start). 5. Build the 15k slice (existing recipe,
      --size 15000; same methodology). The rung will train FROM SCRATCH (user
      decision) and presumably batched, per whatever the batch-size data says.
      Budget: the queued tasks plus up to 3 discovered tasks of comparable size.
      The grant explicitly covers the training steps inside these tasks (e2b
      batch runs, 12B ramp) — do not re-litigate the training gate for them.
      Machine: ceiling hands over at its next natural pause; acquire per-session
      leases, release between sessions, wait-queue when held. HARD STOP after
      step 5: write up recommended launch settings (batch size, learning-rate
      peak + schedule) and CHECK IN — the user launches the 15k overnight
      explicitly (user decision 2026-07-04; no self-launch). Progress
      (2026-07-04, in flight): step 2 DONE — `launch_train.py` wraps optiq's
      `train_lora` with a warmup/hold/cosine schedule passed as a step→lr
      callable (MLX optimizers accept one; `train_lora` feeds
      `config.learning_rate` straight to AdamW) plus resume via a wrapper around
      the adapter-apply step; schedule shape and CLI verified free of the
      machine, live validation rides window B. Step 5 DONE — `data_stage1_15k/`
      built via a new `--output-dir` flag on the slice builder (15,000 pairs,
      5,184 answers vs 1,712 in the 5k, median year 2010, 1,382 valid pairs);
      the 5k slice stays untouched for comparisons. Steps 1+4 DONE — window A
      ran 17:11–17:22 on the ceiling's handoff; results on the two instrument
      items below. Step 3 IN FLIGHT — window B (`window_b.sh`) launched 17:55,
      one deviation from the queued wording: batch timing runs on the 12B
      directly (30 iters at batch 1/2/4) instead of e2b, because the 15k
      recommendation needs the 12B's peak memory and throughput at batch 4,
      which e2b cannot supply; loss-smoothness evidence comes from the 80-iter
      scheduled range runs (5e-5 / 1e-4 / 2e-4 at batch 4). Incident note:
      pausing window A for the reframe edit killed only the caffeinate leader,
      not its process group — the orphaned zsh driver survived and raced the
      relaunched one for the lease (harmless here: instruments ran exactly once,
      on the reframed scripts, and both drivers exited). To pause a detached
      driver, kill the process group (`kill -TERM -<pid>` / `os.killpg`), not
      the pid.
- [ ] Before the next 12B fine-tune run: rehearse the identical recipe on the
      cheap e2b variant first and sanity-check the outputs — generate a few
      clues and run the loss-gap gaps — before spending a 7-hour 12B night. The
      overnight run's failure mode (degenerate generations, collapsed
      conditioning) would have shown up in minutes at e2b scale. Reminder only;
      no action now (user request, 2026-07-03). While the rehearsal runs, also
      validate the lease script's new process-table busy check against a live
      MLX job (`compute_lease.py status` from a second shell; expect "model
      workload running") — the check is unit-tested and live-checked against an
      ollama runner, but not yet against MLX residency.
- [ ] Measure the learning-rate basin (methodology; queued 2026-07-04). One
      short range-test run: ramp LR exponentially from ~1e-6 toward ~5e-4 over a
      few hundred steps, log loss per step, plot loss vs LR. The usable basin is
      where loss falls smoothly; the cliff is where it spikes. Current knowledge
      is a two-point bracket (5e-5 stable, 2e-4 fatal on the QAT 12B; e2b
      tolerates 2e-4). Sets a principled peak (⅓–½ of cliff) for any future
      schedule. ~15 min boxed run; needs the trainer to accept a per-step LR
      callback or the mlx-lm launcher below.
- [x] Stratified false-signal check — DONE 2026-07-04 (stretch step 1;
      `strata_check.py`, `strata_tuned.log`; tuned adapter, 5 draws x 20 answers
      per stratum, medium prompt). Rates: long_word_concept 2/100 (ROUSSEAU →
      'Swiss philosopher hon.', WELFARE → 'Human assistance, for short'),
      polysemous 1/100 (RATE → 'Update, for short'), easy 1/100 (RAMI → 'Popular
      Gen. Fred'). Findings: (1) the overall false-signal rate is ~1.3% (4/300),
      consistent with the earlier 0/60 bound — false signals are rare
      everywhere, and the SCORE/VIOLET 2-of-8 panel observation now reads as
      small-sample noise on specific panel words, not a common failure; (2) the
      VIOLET collision theory gets only weak, statistically insignificant
      support (2 vs 1 hits — would need ~10x the draws to resolve a 2%-vs-1%
      split), though both long-word hits rhyme with it (ROUSSEAU's invented
      'hon.' truncation next to 'philosopher'); (3) under-signaling on
      abbreviation answers (12%, prior probe) remains the dominant
      abbreviation-rule failure by an order of magnitude. Original motivation
      and theory preserved in git history (this item, prior revision).
- [ ] Scaled-slice design (queued 2026-07-04; the corpus-as-supervision scaling
      path from the style-rule discussion). Composition finding (measured
      2026-07-04): the recipe's weights are exonerated — the ': Abbr.' tag rate
      drifted 0.76% (1990s) → 1.67% (2005–09) → 0.88% (2020–24), so the slice's
      0.8% matches MODERN style; recency weighting reproduces current
      conventions, which is the goal. Rare-rule starvation is rarity × slice
      size, and at fixed size composition tweaks buy ≤2× (tagged answers are
      1.7% of distinct answers vs 0.8% of examples) — SCALE is the lever. So:
      keep the existing recipe, extend --size. Fresh-data-over-repeat-epochs
      ADOPTED (user, 2026-07-04) — never re-epoch a small slice when a larger
      one is available. Ladder gated by cheap instruments first (user,
      2026-07-04): 15k slice → one overnight → probe suite (abbreviation
      sensitivity, flat@hard, register sep, decoupling trace, answer gap) →
      decide the ~50k rung by whether rule internalization scales with exemplar
      count. Bank affords ~200k post-dedup. Prerequisites: batch-size throughput
      win + mlx-lm launcher resume (both queued above); at batch-4 throughput
      15k ≈ one overnight, 50k ≈ 2–3 with resume.
- [ ] Adaptive learning-rate schedule via mlx-lm launcher (methodology; queued
      2026-07-04). optiq's supervised path is constant-LR only (warmup/decay
      wired for DPO alone). Write a ~30-line launcher that calls optiq's
      `register()` shim then mlx-lm's tuner with an `lr_schedule` config: linear
      warmup 0→peak over ~3–5% of steps, hold, cosine to ~10% of peak over the
      final ~20–30%. mlx-lm also brings `--resume-adapter-file`, which unlocks
      hold-then-decay adaptivity (decay from a held checkpoint when content
      metrics plateau) and longer boxed probes. Ideal-design rationale in the
      2026-07-04 session; importance ranking: peak ≫ warmup > decay shape.
- [ ] Batch-size exploration (methodology; queued 2026-07-04). Today's runs use
      `--batch-size 1`, and prompt masking means each step's gradient comes from
      only ~8 response tokens — extremely noisy. A larger batch (2–8, or
      gradient accumulation if the launcher path lands) averages that noise,
      which may widen the stable-LR basin (the QAT 12B's 2e-4 cliff could be
      partly noise-kicked) and should raise tokens/sec by amortizing
      dequantize-in-backward across the batch — same lever the throughput task
      points at. Constraints: 32 GB total RAM with 9.9 GB peak at batch 1, so
      headroom is comfortable — still record peak memory per batch size; and LR
      moves with batch size (linear-to-sqrt scaling), so run this WITH the LR
      basin test, not before or after it. Cheap boxed e2b run: batch 1 vs 2 vs
      4, compare tokens/sec, peak memory, and loss-vs-step smoothness.
- [x] Matched-pair difficulty-preference instrument — DONE 2026-07-04 (stretch
      step 4; `register_pairs.py`, `register_pairs_{base,tuned}.log`; 100
      Monday/Saturday pairs, same answer, both members scored under the hard
      prompt; REFRAMED 2026-07-04 per user: weekday proxies difficulty through
      obscurity/terseness, NOT liveliness — 'Blois is on it' vs 'Longest river
      in France' for LOIRE are comparably flat phrasings with different trivia
      depth; liveliness (wordplay, misdirection) needs its own instrument, e.g.
      NYT's '?' wordplay-marker convention as a marker-cost analogue — not
      queued). Results: base — Saturday win rate 57/100, sequence margin +2.44
      nats, per-token margin −1.01 nats/token; tuned — 41/100, −2.90, −0.71.
      Reading: (1) neither model prefers the hard member per-token under the
      hard prompt (both margins negative); (2) tuning moved per-token pricing
      TOWARD the Saturday member by +0.30 nats/token (−1.01 → −0.71) — the
      diffuse difficulty-conditioning rule moved a little, in the right
      direction; (3) the sequence-level swing the other way (+2.44 → −2.90) is a
      length artifact of the common-mode register shift: tuning cheapens
      real-clue tokens across the board, and total-NLL gains scale with token
      count, favoring the longer Monday members — so the per-token margin is
      this instrument's headline number, tracked per rung (base −1.01 → 5k −0.71
      → 15k ?). Same shape as the abbreviation finding: common-mode shift large,
      conditional rule small — the 15k rung tests whether exemplar count scales
      the conditional part. Complements flat@hard (within-model suppression) and
      the decoupling trace (training-dynamics view).
- [ ] Panel eval vs v9 via a standalone bridge (queued 2026-07-04; user deferred
      — "come back to it later"). The spec's stage-0 client adapter for the
      harness was never built: ceiling's `pipeline_local.py` speaks only to
      Ollama, and `optiq serve` is untrustworthy for generation (the 'An double'
      sampling mystery). Bridge plan, touching nothing on the ceiling branch:
      (1) batch-generate the 12 panel words × 3 runs at medium via direct
      `mlx_lm.load` (~20 min); (2) screen with the 26B Ollama judge by COPYING
      the screen-prompt text from ceiling's `pipeline_local.py`
      (prototyping-independence rule), compute screen-bankable clues per
      GPU-minute against v9's tier-1 numbers in ceiling's `evals/` (~25 min).
      Panel-word exclusion from stage-1 train/valid data verified clean
      2026-07-04. Tier-2 31b confirm + the <$2 Fable checkpoint on banked clues
      follow as separately gated steps per the spec.
- [ ] Abbreviation-conditioning instrument (ACTIVE 2026-07-04; user-prioritized
      as a case study: a useful fine-tune must learn implicit semantic style
      rules, not just surface structure — abbreviations are the quick metric for
      NYT style-guide internalization overall, not the target themselves).
      Measures whether the model binds abbreviated clue forms to abbreviated
      answers — a conditional register rule with only ~40 exemplars in the
      5,000-example stage-1 train set (0.8%), so expect it unlearned at one
      epoch. Two views, sharing the matched-pair scoring machinery above: (a)
      likelihood — score "Abbr."-marked clues from the bank (excluding train
      examples; val has ~11, pull more bank-wide) under their true abbreviated
      answers vs matched full-word answers, gap = answer-form conditioning; (b)
      generation — sample clues for clearly full-word answers and compare the
      abbreviation-marker rate against the 0.8% corpus base rate. Context:
      overnight-5e-5 samples misapplied the convention (VIOLET → 'Chrys.
      relative', SCORE → 'Rating: Abbr.'). If the rule is absent, remedies in
      order: larger stage slice (more absolute exemplars), more epochs (weak —
      memorizes the 40), explicit answer-form tag in the prompt (stage-2
      conditioning design, with difficulty).
  - Built and run 2026-07-04 (abbr_probe.py; user generalized the target: any
    abbreviated word in the clue is the signal, e.g. 'Sci.' cluing PHYS — the
    tag is one special case). Instruments: swap cost (clue scored in abbreviated
    vs expanded form under the true answer, e.g. 'Bug grp.?' vs 'Bug group?' for
    CIA; diff-of-diffs across answer groups), marker cost (± ': Abbr.' suffix),
    generation signal rate. First run (swap n=15/40):
    - Swap instrument, authoritative n=60 rerun (expanded 34-pair lexicon from
      the bank survey — 635 tagged answers / 6,253 swappable clues; pooled
      historical clues; quote + signal-purity filters): BASE diff-of-diffs
      +3.03, TUNED +2.52 — the base model holds the general rule at modest
      strength and tuning roughly PRESERVED it (neither taught nor erased; the
      first run's dramatic "+7.63 base, eroded to +2.50" was an artifact of the
      noisy n=15 cell plus residual-signal contamination in the old full-word
      items — tuned was +2.50/+2.52 across both runs, base moved). Tuning's real
      effect is common-mode: abbreviated forms ~3 nats cheaper everywhere
      (in-register shift), conditional structure unchanged. Behaviorally the
      rule is weak in both models: prefers-abbreviated only 20%→8% (abbreviation
      answers) vs 13%→2% (full-word).
    - Tuning STRENGTHENED the explicit tag rule (n=40 cells, first run): marker
      diff-of-diffs +1.27 (base) → +4.49 (tuned); the tag also became
      in-register overall (cost −11.8 nats on abbreviation answers). The ~40 tag
      exemplars taught a localized pattern conditionally; the diffuse
      form-agreement rule stayed flat — localized anchors learn from sparse
      data, diffuse rules don't move.
    - Generation (tuned): 0/60 false signals on full-word answers — a LOW rate
      (consistent with up to ~5%), not zero: the probe exists because the model
      false-signaled on panel words ('Rating: Abbr.' for SCORE, 'Chrys.
      relative' for VIOLET; 2 in 8 draws there), so the rate is likely
      answer-dependent. 7/60 signaled on abbreviation answers (12% — severe
      under-signaling is the dominant failure). OCT → 'Fall month: Abbr.'
      correct; EPISC → 'Totalitarian dictator: Abbr.' (form right, content
      wrong).
    - Logs: abbr_probe_{base,tuned}.log (marker + generation, first-run swap
      superseded), abbr_swap_{base,tuned}.log (authoritative swap).
- [ ] Hand-tagged quality bank (user-in-the-loop; queued 2026-07-03). User walks
      a sample of the data bank in a review UI and hand-tags examples on
      multiple quality dimensions, fast per item. Design TBD: possibly several
      single-dimension passes rather than one heavy pass; UI should make tagging
      a few seconds per clue (keyboard-driven, batched). Dimensions worth
      considering: bankable yes/no, difficulty read, register/flavor, mechanism
      (per satisfaction taxonomy), dated/evergreen. Payoffs, in order:
      calibration set for the local judge; seed preference pairs for DPO;
      validation set for the judge-filtered-training knob; ground truth for any
      future curation filter. Priority raised 2026-07-04: the user wants a
      golden set tuned to their taste — the register-preference discussion
      showed "coherent" is far below "satisfying" ('Purple' for VIOLET is
      coherent yet rates low), and satisfaction is what the corpus cannot define
      on its own. First in line once a usable fine-tuned model exists.
- [ ] Investigate training throughput (after the overnight run; needs the
      lease). The log's `Tokens/sec` ≈ 1.5–2.0 counts only trained (response)
      tokens — ~8/example under prompt masking — so it is not comparable to
      inference decode tok/s. But the implied full-sequence rate (~0.21 it/s ×
      ~40 tokens forward+backward through the 12B 4-bit model) still looks low
      vs MLX prefill throughput. Suspects, in order: backward pass through
      quantized layers (dequantize cost), batch-1 hardware underutilization
      (batch 4 gave only ~15% more examples/s — itself evidence the bottleneck
      isn't compute saturation), fanless thermal throttling on a multi-hour run.
      Cheap probes: time a forward-only pass over the same batch shape vs the
      training step; compare early-run vs late-run it/s in `train_stage1.log`
      for thermal drift. Note (2026-07-03): the overnight run answered the
      thermal probe — it/s held steady (~0.19–0.25, no downward drift) across
      all 6.9 hours, so throttling is ruled out; remaining suspects are the
      quantized-backward path and per-example/batch behavior. Payoff: if step
      time is fixable, stage-2 epochs get cheaper across the board. If it is
      dequantize-in-backward, the first question is which form: MLX has native
      transposed quantized-matmul kernels, so backward _can_ run on 4-bit
      weights directly (then the cost is ~3× weight reads per step —
      bandwidth-bound, near a hardware floor); a dequantize-then-matmul fallback
      in optiq's unified path would instead be fixable software waste (grep the
      training path for explicit dequantize; check newer mlx/optiq releases).
      Levers either way: gradient checkpointing off if the preset enables it
      (9.9 GB peak on 32 GB — memory headroom is not the constraint); fewer
      adapted layers (halves backward weight traffic; capacity tradeoff —
      stage-2 only); more tokens per step via batching or sequence packing
      (weight reads are per step, not per token) — though batch 4's mere ~15%
      gain cuts against the pure bandwidth story and itself wants explaining
      (per-example serialization? short-sequence kernel inefficiency?).
- [ ] Stage 2 — only on stage-1 signal. Options, not commitments: more
      data/epochs; DPO from judge labels (converts judge preferences into the
      training objective — the quality-not-shape lever); judge-filtered training
      subset (screen training clues through the local judge — the
      previously-rejected expensive evaluator, justifiable only on signal);
      optiq sensitivity-aware rank scaling; 26B tune; scaffold-trace
      distillation (train on v9 conversation prefixes → final clue).

---

## Phase 7 — Brainstorm prompt redesign

**Goal:** Replace the single-turn brainstorm placeholder with a multi-turn
conversation implementing the 8-phase clue development workflow, so the
generator explores mechanisms before writing clues and self-critiques before
committing.

### Background

Three source documents drive this work:

- `cluegen/local/README.md` — goals, pipeline overview, and design rationale;
  the authoritative description of what the tool does and why
- `background.md` — lessons from ChatGPT experiments; defines the 8-phase
  workflow and quality dimensions (LS, EL, CP, RF, SQ, IN, Bullshit Rating)
- `prompting.md` — local model guidance; one cognitive mode per turn, state
  dilution mitigation, schema enforcement

**Core LLM failure mode to engineer around** (from `background.md`): the model
finds one mechanism, produces variations, and overrates them. Fix: separate
_analyze → mechanisms → filter → clues → solver sim → refine → extract_.

**Goal reframe** (from `background.md`): the clue does not need to uniquely
determine the answer. Goal is elegant ambiguity that resolves through crosses —
a small cloud of plausible answers that collapses to one. Unique determination
is for easy weekday clues only.

### Current code state

- `cluegen/local/prompt.py`: `brainstorm_messages(word, difficulty)` returns a
  single-turn placeholder (system + one user message)
- `cluegen/local/generator.py:49`:
  `TODO: Phase 3 — replace with multi-turn brainstorm sequence`
- `cluegen/local/generator.py` Stage 1: one
  `client.chat(brainstorm_messages(...))` call, then a second call to extract a
  `{"clues": [...]}` JSON list of candidates
- `cluegen/local/generator.py` Stage 2 (already implemented — do not break):
  iterates over extracted candidates; runs `validate_solvability` +
  `validate_quality` on each; returns the first passing candidate as
  `ClueResult(clues=[clue])`; falls back to `candidates[0]` if none pass
- Currently `ClueResult.clues` always contains one entry. The `--candidates N`
  flag (pending Phase 3 in `plan.md`) will let callers request N clues. Design
  the extract turn to produce multiple candidates so Stage 2 has a pool to
  filter from.
- Quality schema lives in `cluegen/local/quality.py`: `_QUALITY_FORMAT`,
  `_SYSTEM_PROMPT_TEMPLATE`, `_STRUCTURED_OUTPUT_PROMPT`
- Reference: `validation.md` documents the two-call validation architecture

### Proposed brainstorm turn structure

Seven model calls, each targeting one cognitive mode:

1. **Answer analysis** (Phase 0): part of speech, morphology, near-miss answers
   of the correct letter count, related words a solver might try
2. **Mechanism brainstorm** (Phase 1): generate 20+ mechanisms (map
   reinterpretation, idiom → literal, cultural reference, homophone, domain
   ambiguity, etc.). Explicit instruction: _do not write clues yet_
3. **Mechanism filter** (Phase 2): keep 5–7 strongest + 1–2 rough-but-high-
   ceiling ideas; prefer a weird high-upside idea over a safe predictable one
4. **Clue drafting** (Phase 3): 3–5 candidates per surviving mechanism; wide
   exploration, label each with mechanism type
5. **Solver simulation + credibility** (Phases 4 + Bullshit Rating): for each
   candidate, list plausible alternative answers a real solver would consider;
   check that those alternatives are real words/phrases; flag any clue where the
   ambiguity is invented rather than genuine
6. **Refinement + diversity audit** (Phases 5–7): tighten wording, strip hedge
   words and filler, ensure surviving clues use _different mechanisms_ — not
   just different wording of the same mechanism (directly addresses "many
   versions of 'Down, on a map'" failure)
7. **Extract** (Phase 8): schema-enforced `{"clues": ["...", ...]}` JSON list
   via `response_format` (same pattern as `_GUESSES_PROMPT` in
   `cluegen/local/solvability.py`)

### Tasks

- [ ] **Implement multi-turn brainstorm in `prompt.py`**
  - Interface decision: `brainstorm_turns(word, difficulty) -> Sequence[str]`
    returns the 7 user-turn strings; generator owns message accumulation. Keeps
    `prompt.py` focused on text and `generator.py` focused on orchestration.
  - Write the system prompt: NYT constructor persona; state the goal as elegant
    ambiguity resolving through crosses; encode per-day difficulty (Mon: direct
    definitions acceptable; Sat: misdirection required, no direct definitions)
  - Write each of the 7 user turn strings (Turns 1–7 above)

- [ ] **Update `generator.py` to drive multi-turn brainstorm**
  - Replace single `client.chat(brainstorm_messages(...))` call with a loop
    through all turns, accumulating messages after each reply
  - Remove or replace the separate extract call (Turn 7 becomes the extract)
  - The brainstorm client is separate from the validation clients
    (`solvability_client`, `quality_client`) — `generate_clue` will need to
    accept separate client parameters so the brainstorm fake sees exactly 7
    calls in tests
  - Remove the `TODO: Phase 3` comment when done

- [ ] **Explore other quick wins for fast iteration**
  - After splitting the probe, survey what else would make prompt iteration
    faster or lower-friction before diving into the quality task queue.

- [ ] **Investigate dense model attention across multiple conventions**
  - Observed: `gemma4:31b-mlx` (dense, not MoE) keeps reasoning tight and
    attention focused even when evaluating all five conventions in a single turn
    — the failure mode that motivated separating convention 2 may not apply to
    this model.
  - Questions to resolve: does the dense model consistently outperform the MoE
    model on multi-convention focus? Is the gap large enough to change model
    selection for the conventions turn? Does this make the "Separate convention
    2" task unnecessary for dense models?
  - Use `cluegen/scratch/probe_conventions.py` to compare side-by-side.

- [ ] **Calibrate sampling temperature**
  - Harness default is 0.2; Gemma4's native default is 1.0. Research suggests
    thinking models need ≥ 0.6 to avoid repetition loops — too-low temperature
    may be causing the double-reasoning pass.
  - Hypothesis: 0.6–0.7 balances coherence with enough randomness to break the
    repetition pattern, without the variance of 1.0 on an evaluation task.
  - Evaluate: run probe_quality_single at 0.2, 0.6, 0.7, and 1.0; compare
    reasoning token count (proxy for doubling), output correctness, and wall
    time. Pick the lowest temperature that eliminates doubling.
  - Update harness default and production client once a value is chosen.

- [ ] **Explore token-reduction prompting**
  - Question: can we prompt the model to produce shorter responses without
    regressing reasoning quality? Shorter outputs reduce latency and make logs
    easier to scan.
  - Directions to try: explicit length instructions ("be concise"), structured
    verdict-first format (verdict before reasoning, not after), chain-of-thought
    compression prompts.
  - Measure: output token count and elapsed time vs. correctness on known test
    cases.

- [ ] **Switch solve-first persona from crossword editor to crossword solver**
  - The solve-first conversation in `probe_quality_multi.py` currently uses the
    editor persona ("You are an experienced NYT crossword editor"). The solver
    role is more natural for this turn — it's asked to work through how a solver
    reaches the answer, not to evaluate the clue.
  - Change `_SYSTEM_PROMPT_INTRO` to a solver persona (e.g. "You are an
    experienced NYT crossword solver.").

- [ ] **Update `quality.py` prompts from curl script iterations**
  - Several prompt improvements were developed and validated in
    `test_wordplay.sh` and `test_conventions.sh` but not yet ported to
    `quality.py`:
    - Gatekeeper persona: "quality gatekeeping: catch errors before they reach
      solvers… well-intentioned but inexperienced constructor — expect mistakes…
      passes only when it genuinely satisfies the requirement, not when a
      justification can be found for it"
    - C1 reframe: "The answer having multiple meanings is irrelevant; the only
      question is whether the clue's surface requires lateral thinking to reach
      it" (replaces "even if extra meanings exist")
    - Solver simulation framing: "Reason from the clue to the answer, not the
      other way around. Imagine a solver seeing this clue for the first time…"
    - Few-shot examples for the `?` convention (see task below)

- [ ] **Separate convention 2 (`?` indicator) into its own evaluation turn**
  - Convention 2 requires genuine interpretive judgment; conventions 1, 3, 4, 5
    are largely mechanical (often vacuous passes). When evaluated together,
    convention 2 dominates the model's attention and produces worse reasoning
    than when evaluated in isolation.
  - Validated in curl script runs: isolated convention 2 produces tighter,
    faster, more reliable reasoning.
  - Implementation: split `_CONVENTIONS_SCRATCHPAD_PROMPT` into two turns — one
    for convention 2 alone, one for the remaining four. Update
    `validate_quality` to drive the extra turn and combine results.
  - Note: the dense model investigation may change this conclusion — if
    `gemma4:31b-mlx` handles multi-convention focus reliably, separation may
    only be needed for MoE models. Revisit after that task.

- [~] **Add few-shot examples to the quality conventions scratchpad prompt**
  {#few-shot-examples}
  - Examples developed and validated in `test_wordplay.sh`:
    - Earned: "Semi professional?" → TEAMSTER; "Perpetual homebody?" → SNAIL
    - Unearned: "Keeps time?" → CLOCK; "Points the way?" → COMPASS; "Draws
      blood?" → NEEDLE
  - Not yet ported to `quality.py`
  - Open question: model evaluates `?` by trying to find the wordplay path — if
    it can't identify the mechanism (e.g. brand knowledge required), it
    incorrectly concludes the `?` is unearned. May need escape-hatch handling
    (see escape-hatch task below).

- [ ] **Add escape hatch for unidentifiable wordplay** {#escape-hatch}
  - When the model cannot identify the wordplay mechanism, it currently
    concludes the `?` is unearned — a false FAIL. It should instead flag
    uncertainty explicitly.
  - Prompt change: "If you cannot identify any wordplay path, note that
    explicitly rather than concluding the `?` is unearned."
  - Open question: what does this mean for structured output? Options: add a
    confidence field, use a nullable boolean, or treat explicit uncertainty as a
    PASS with a flag. Decide before porting to `quality.py`.
  - Observed failure case: "Focuses on the road?" → FORD. The model tried
    river-crossing, car-and-road association, acrostic, and hidden-word
    constructions, but never arrived at the key pivot: Ford makes a model called
    the Focus. Correctly concluded FAIL for the wrong reason (knowledge gap, not
    bad clue). Use this as a test case when implementing the escape hatch.
  - Depends on #few-shot-examples

- [ ] **Validate `?` evaluation in both directions**
  - All curl testing so far has used a clue that should FAIL (unearned `?`).
    Need to verify the model also correctly:
    - PASSes clues with a legitimate earned `?` (e.g. "Semi professional?" →
      TEAMSTER, "Perpetual homebody?" → SNAIL)
    - FAILs clues that are missing a `?` when one is required
  - Use `cluegen/scratch/probe_wordplay.py` with `--clue` and `--answer`
    overrides.
  - Rationale: examples in the prompt are calibrated around unearned-`?`
    detection; the earned direction may be over-triggered toward FAIL.

- [?] **Consider including a clue-to-answer explanation in generator output**
  - The brainstorm extract turn could include a brief explanation of how each
    clue maps to its answer — useful for tricky clues where the validation step
    would otherwise have to independently discover the lateral leap.
  - Open question: the explanation may also bias validation toward over-trust
    (accepting a clue because the explanation sounds plausible rather than
    because the wordplay is genuinely sound). Not an obvious improvement.
  - If pursued: add an optional `explanation` field to the extract schema;
    thread it through to `validate_quality` as additional context; measure
    whether pass rates improve or degrade on known-bad clues.

- [ ] **Add few-shot examples for all other evaluations**
  - The `?` convention now has examples; the rubric dimensions and other
    conventions (tense, abbreviation, fill-blank, genuine alternatives) do not.
  - Approach: identify the failure modes for each evaluation that are most
    likely given LLM-generated clues, then construct targeted examples as done
    for `?`.

- [-] **Decide `cross_check_payoff` day-range profiles and add calibration
  tests**
  - Dropped: `cross_check_payoff` is a quantification of genuine alternatives
    and doesn't add a distinct signal beyond elasticity + the genuine
    alternatives convention. Remove from `quality.py` rubric when porting prompt
    improvements.

- [ ] **Evaluate thinking mode performance and decide on a long-term strategy**
  - Thinking mode is currently enabled by default (`reasoning_effort=None` in
    `ModelOptions`). It reliably produces correct convention reasoning but adds
    significant latency (~107s/turn for gemma4:26b vs ~25s without thinking).
  - Questions to resolve: is the latency acceptable for batch use? Should
    thinking be selective (conventions turn only, not rubric or structured
    output)? Would few-shot examples recover correct convention reasoning
    without thinking mode, making the performance cost avoidable?
  - Depends on `[?]` **Add few-shot examples** — try few-shot first; if it works
    reliably without thinking, thinking mode may not be needed.

- [ ] **Fix convention transcription failure in structured output turn**
  - The structured output JSON returns `false` for conventions that the
    scratchpad correctly reasoned as PASS (observed: `is_abbreviation_signaled`
    and `uses_fill_format` both `false` despite explicit PASS verdicts).
  - Hypothesis: the JSON template in `_STRUCTURED_OUTPUT_PROMPT` shows all
    convention fields as `false`, acting as a gravitational prior that overrides
    weak PASS signals during transcription.
  - Options to consider:
    - (a) Make the transcription step explicit: add instruction "Encode each
      PASS verdict as `true` and each FAIL as `false`" to the structured output
      prompt
    - (b) Change the template placeholder values to avoid a `false` prior (e.g.
      use `true`, or omit placeholder values entirely)
    - (c) Combination of (a) and (b)
  - Note: rubric scores transcribe correctly because the scratchpad's explicit
    numbers (e.g. 3, 5) clearly override the placeholder `3` — the boolean case
    is weaker because `false` in the template is a valid final value.

- [ ] **Support multiple candidates output** (`--candidates N`)
  - Several other tasks assume a pool of candidates flows through Stage 2 to
    produce multiple outputs; this task makes that end-to-end
  - `ClueResult.clues` currently always has one entry (the first passing
    candidate, or `candidates[0]` as fallback)
  - Changes needed:
    - Add `--candidates N` flag to `cluegen/local/cli.py` (default 1); pass `N`
      through to `generate_clue`
    - Update `generate_clue` in `generator.py`: Stage 2 currently stops at the
      first passing candidate — change to collect up to N passing candidates
    - Update `ClueResult.clues` return to contain up to N entries
  - Note: the brainstorm extract turn should produce enough raw candidates to
    give Stage 2 a meaningful pool. With N=1 and 15–20 brainstorm candidates,
    the pipeline has headroom; design the extract count with N in mind.

- [ ] **Surface failure when all candidates fail validation**
  - Currently `generate_clue` falls back to `candidates[0]` when no candidate
    passes Stage 2 validation. That silently returns a clue known to be bad.
  - Change: when all candidates fail, raise a purpose-built exception class
    (e.g. `AllCandidatesFailedError`). No built-in exception type fits this
    failure mode; a custom class makes every `except` clause unambiguous. A
    typed result union was considered but an exception is the right contract
    here — this is unexpected failure state, not a normal return path.
  - CLI behaviour: print an error message to stderr and exit non-zero for the
    affected word; continue processing remaining words in batch mode.

- [ ] **Compensate for LLM letter-counting failures**
  - LLMs tokenize text and cannot reliably count letters in a word (e.g., they
    may claim NEIGHBOR has 7 letters when it has 8). This matters in two places:
    - **Answer analysis (Turn 1)**: the model is asked to list near-miss answers
      of the correct letter count — it may produce words of the wrong length
    - **Solvability validation**: the blind call asks the model to guess the
      answer given only clue + letter count; if the model miscounts, it may
      treat a correct guess as wrong or vice versa
  - Options to consider:
    - (a) Inject the answer letter-by-letter in the prompt (e.g.,
      `N-E-I-G-H-B- O-R, 8 letters`) so the model sees explicit length without
      counting
    - (b) Inject a numbered list: `1:N 2:E 3:I 4:G 5:H 6:B 7:O 8:R`
    - (c) Post-process model output: filter candidate lists by length in Python
      (reliable, but doesn't help the model reason about alternatives)
    - (d) Combination: inject explicit length in prompts + filter in Python as a
      safety net
  - Note: option (c) is already partially in place — `validate_solvability`
    checks whether the answer appears in the model's guess list, which is a
    Python-level comparison. The gap is that the model may fail to generate the
    correct answer as a guess at all because it misjudged the length constraint.

---

## Findings

Empirical observations that should survive task cleanup.

- **Ollama `format` key adds real overhead on MLX models.** Passing a JSON
  schema as the native `format` key roughly doubles wall time (~50% overhead in
  observed runs), even though the MLX backend doesn't enforce the grammar
  constraint (known bug: https://github.com/ollama/ollama/issues/16563). The
  grammar engine runs on the CPU host side; its time lands in `total_duration`
  but not in any of the bucketed fields (`load_duration`,
  `prompt_eval_duration`, `eval_duration`), so it appears as unexplained
  overhead in the timing section. Omit the `format` key when targeting MLX
  models.

- **Long conversations trigger a generation-speed cliff on `gemma4:31b-mlx`.**
  After `think=True` turns with large reasoning traces (270+ tok), generation
  drops to 0.2–0.3 tok/s (15–25× slower) while prefill stays normal — pointing
  at memory compression rather than thermal throttling (yellow memory pressure,
  8–10 GB compressed, persists with all other apps closed). What accumulates (KV
  cache, thinking tokens, output) is unconfirmed. Mitigation: split work into
  short conversations so the KV cache is discarded before state builds up —
  verified to eliminate the cliff across a full 12-turn run.
