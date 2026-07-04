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

---

## Local ceiling campaign

**Goal:** Explore the quality ceiling of single American-style clue generation
in scratch probes. Spec, yardstick, and autonomy rules: `ceiling.md`. Runs on
branch `local-ceiling` in its own worktree; progress reports in `ceiling-log.md`
on that branch. Probe, checkpoint harness, v1–v6 iteration, and checkpoint 1 are
done — see the log for the curve and the criteria re-analysis.

- [x] **Local judge iteration** — RESOLVED 2026-07-01: production judge is the
      cascade (26B per-clue screen, 31B per-clue confirm), precision 1.00 on the
      calibration sample. Scoreboard and history: ceiling-log.md.
  - Note: repeated tuning against the same 40 clues risks overfitting the judge
    prompt to them; fine at prototype stage, flagged for later
- [x] **End-to-end pipeline** (`scratch/pipeline_local.py`) — setter → cascade →
      mechanical `?`-tidy → one feedback retry → bank. Setter iterated to v8
      (liveliness pressure, directive retry). 5/6 fresh words banked over
      cumulative `--skip-banked` passes; ~23% bank rate per word-run ≈ 7–8 min
      local compute per banked clue. Details: ceiling-log.md.
  - [-] Multi-candidate within one setter conversation — superseded: run-level
    best-of-N (repeated passes at temp 1.0) captures the same recall with no
    correlated-draft risk
- [x] **Held-out validation + checkpoint 2** — held-out 1/8 (category-dependent
      ceiling: numbers fall back to arithmetic-flat). Checkpoint 2 ($0.778): 7/8
      Fable accepts on pipeline banks — judge validated at ~0.9 precision on
      unseen words; 2 of 4 audited rejections were recall losses, now banked.
      Details: ceiling-log.md.
- [~] **Throughput exploration** — target an order of magnitude better than ~7–8
  min of local compute per banked clue; attack per-run bank rate (23% friendly
  categories, ~5% numbers) and per-run cost. Governing principles and hypothesis
  list: ceiling-log.md (Throughput brainstorm, 2026-07-02).
  - [x] Two-tier eval loop built (`scratch/eval_panel.py`); variant round run
        2026-07-02. Winners adopted as pipeline v9 (align edit turn, every-KEEP
        extract, 31B fixer replaces setter retry, model-batched phases);
        edit-cap and no-difficulty dead. Scorecards: ceiling-log.md.
  - [ ] User reads prompts + logs in detail before strong tweak opinions —
        deferred to a fresh-eyes session (2026-07-02); not blocking autonomous
        progress
- [~] **Autonomous iteration window** #window — user-granted ~5–10 h of
  self-directed iteration (2026-07-03) across judge quality, setter quality, and
  throughput, steered by apparent leverage. Protocol (validation ladder,
  adoption methodology, budgets: $10 Fable — $8.98 left, ≤45 min batches, ≤10
  tries/task): ceiling-log.md 2026-07-03 window entry. Per-idea record with full
  state and the morning queue: `scratch/window_ledger.md` — read it first on
  resume. Paused overnight 2026-07-03→04: the fine-tune thread has the machine
  for a large training run; NO local runs until morning. First morning task:
  build idea 10 (multi-turn confirm, code-side verdict — user-directed) and run
  its 14-row discrimination probe. Ollama server is DOWN — restart
  `ollama serve` first. Acquire the lease via MAIN's copy of compute_lease.py
  (process-scan fix edbfcc2); `wait` via this branch's copy.
- [~] **Judge: satisfaction criterion** #judge-satisfaction — the cloud verify
  contract now carries it (criterion 6 + mandatory `basis` output field,
  2026-07-02): flags flat glosses with `basis: null`, validated on a held-out
  flat set with zero liveliness false-positives; iteration story in ceiling-log.
  Local cascade alignment implemented 2026-07-02 (liveliness bullet gains both
  gradients; the NINE calibration example that blessed flat count metonymy is
  now a graded ELEVEN/NINE pair; stock-association example added). Agreement
  eval (`scratch/agreement_eval.py`) iterated to keeps 10/11 with flats dying in
  every run (iterations 3–6: basis-commitment mechanism, diagnosed-cluster
  fixes; full trajectory in ceiling-log 2026-07-03). Cascade redesigned from
  variance-probe evidence (`scratch/variance_probe.py`): screen = 26B taste +
  craft; confirm = 31B precision verification with its own protocol
  (`_CONFIRM_SYSTEM`/`_CONFIRM_PROMPT` — v2 kills ONE/FOURTEEN/FELIX-class
  precision errors 0:4 with zero false kills); the role split is an intermediate
  state, not settled — see #taste-31b. Remaining: (a) re-validate the full new
  cascade on the 49-clue combined set (concatenate
  `scratch/satisfaction_reference_verdicts.jsonl` +
  `scratch/fresh_validation_verdicts.jsonl`, pass to agreement_eval as its
  reference argument); (b) decide judge temperature (1.0 improved the screen's
  stable-wrongs with no control regressions — measure, don't assume); (c) known
  gaps for later — padding bites at no stage, GASP-class contested fun. Local
  runs; machine with the fine-tune thread — user-gated.
  - Note: the "fun" escape hatch is closed — a fun gradient (humor/surprise in
    the surface vs. recognition of stock associations) landed 2026-07-02; all
    five fun-basis chunk-1 accepts flipped to revise with regression accepts
    holding. Residual watch items: the judge runs stricter overall (9A/11RV on
    the 20-clue set vs. 15A/5RV before), and it now flags unmarked
    definition-by-example clues (MELODY "Whistleable earworm") — a spec
    ?-convention call, not a liveliness one.
- [ ] **Taste authority: give the 31B a fair shot** #taste-31b — the current
      role split (screen = 26B taste, confirm = 31B precision) rests on
      partially validated data: a handful of probe runs over a 12-clue sample,
      with six iterations of tuning invested in the 26B's taste prompt and zero
      in the 31B's (user judgment 2026-07-03: fine intermediate state, probably
      not the right end state — a priori, the dense 31B should out-judge the
      4B-active MoE 26B on taste). Queue: a symmetric taste-iteration campaign
      for the 31B — calibration and protocol tuned against ITS observed failure
      modes (starting from the charity/leniency pattern in the probe logs),
      evaluated with the distribution instrument (`scratch/variance_probe.py`)
      on a larger sample plus the 49-clue set; then re-decide role assignment on
      comparable-effort evidence. Local runs; user-gated.
- [~] **Fixer: preserve angle and misdirection** — chunk 1 showed the repair
  path flattens drafts into unimpeachable facts (all six fixer banks lost their
  `trap`). Prompt updated 2026-07-02: the angle is named as what the clue does
  well, must survive the repair and land in the `trap` field; flatness critiques
  demand a fresh angle, not a rephrase. Remaining: validation probe — replay
  chunk-1's ~10 fixable critiques under the new prompt, check angle/trap
  survival. Local runs; user-gated on machine availability.
- [x] **Reject bank** #reject-bank — `cluegen/local/reject_bank.jsonl` (user
      request 2026-07-03): correctly-rejected clues with labeled reasons — eval
      data now, judge fine-tuning data later. Capture is wired:
      `scratch/reject_bank_append.py` appends Fable revise/reject verdicts from
      any checkpoint results file (dedupe, disjoint-from-bank invariant, banked
      hits surface as purge candidates). Run it after every checkpoint.
- [~] **Batch 4** #batch4 — all unbanked, non-held-out words.in entries
  (`scratch/batch4_words.txt`, 493 words) via the chunked detached driver
  (`scratch/batch4_driver.py`; per-chunk `--skip-banked`, stop-file drain,
  relaunch resumes where it left off). Chunk 1 done, drained 2026-07-02
  (findings: ceiling-log). Next: chunk 2 as the integration test of the purge +
  judge + fixer changes; chunks 2–7 carry the name section — the judge-v2
  name-word live test (v1 ran 31% screen-bad). Run after #judge-satisfaction's
  agreement eval and the fixer replay. Local runs; user-gated.
- [ ] **Mechanism tagger: tighten the dominant-mechanism instruction** — it
      over-attributes frame-anchored clues to sense pivot (2026-07-02 audit);
      matters once bank-level angle passes consume the tags.
- [ ] **Align local vs cloud judge requirements** #judge-alignment — both judges
      should enforce the same requirement set, each via methodology fitting the
      model's strength (user direction 2026-07-04). Audit findings (window
      session, 2026-07-04): (a) answer/root/cognate leakage — cloud has
      mechanical `has_answer_leak` + stem soft-flags + a judge check with the
      etymology exception; local has only setter self-check. The mechanical half
      is pure code to copy local-side (copy, not import — prototyping
      independence); the judgment half needs a home in the cascade. (b) The
      local setter emits a required `trap` field no local judge reads — verify
      it (cloud check #7: trap proportionate to difficulty) or stop emitting it.
      (c) Non-pinning prosecution is a local-only invention absent from
      CLUE_SPEC — removal in flight (window idea 11 + confirm at adoption). (d)
      Cross-clue independence: intentionally out of local scope — see
      #angle-distinct.
  - Note: consider a requirements trace (each CLUE_SPEC §A2 invariant → where
    the local cascade checks it) so this audit is mechanical next time; two
    drift types showed up (a dropped requirement and an invented one).
- [ ] **Angle-distinct: reevaluate at cleanup** #angle-distinct — cross-clue
      angle distinctness is intentionally OUT OF SCOPE for the local run (user
      direction 2026-07-04): multiple similar banked clues for one word are fine
      in the meantime, and anticipated fine long-run — the cloud judge measured
      independence to control for laziness in the cloud setter, and the local
      structure has no analogous need. Reevaluate then rather than enforce now.
  - Note: sibling leak, cross-word rather than same-word — chunk 1 banked the
    "X's total/tally" template three times across different words. A per-clue
    judge can't see it; part of the same reevaluation.
- [x] **Satisfaction-mechanism taxonomy** — written as
      `cluegen/local/satisfaction.md` (local-ceiling branch, 2026-07-02): five
      bases of satisfaction (aha is not mandatory — user note), ten mechanisms,
      failure modes, pipeline uses. Standing rule preserved there: no
      single-mechanism hints in prompts; banks are biased inputs, never the
      standard.

---

## Fine-tuning probe

**Goal:** directional go/no-go on whether a locally QLoRA-tuned small Gemma
beats prompted-26B v9 as setter, in confirmed-bankable clues per GPU-minute.
Spec (decisions, stages, gates): `finetune.md`. Intended to run in its own chat
thread; the spec is self-contained.

- [ ] Stage 0 — plumbing: smallest Gemma + ~500 pairs; train → fuse → serve →
      eval loop runs end to end. Model download needs user approval.
- [ ] Stage 1 — probe: QLoRA gemma4-12B on 5–20k curated xd pairs (answer-split;
      panel + held-out answers excluded); evaluate via `eval_panel` (bare
      single-turn and scaffolded); Fable spot-check <$2. Depends on stage 0.
- [ ] Stage 2 — only on stage-1 signal: more data/epochs, DPO from judge labels,
      or 26B tune. Not committed.

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
