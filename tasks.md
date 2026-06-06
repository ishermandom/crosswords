# Pending tasks

Status key: `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` dropped ·
`[?]` uncertain/speculative

---

## Phase 7 — Brainstorm prompt redesign

**Goal:** Replace the single-turn brainstorm placeholder with a multi-turn
conversation implementing the 8-phase clue development workflow, so the
generator explores mechanisms before writing clues and self-critiques before
committing.

### Background

Two source documents drive this work:

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

- `clue_gen/prompt.py`: `brainstorm_messages(word, difficulty)` returns a
  single-turn placeholder (system + one user message)
- `clue_gen/generator.py:49`:
  `TODO: Phase 3 — replace with multi-turn brainstorm sequence`
- `clue_gen/generator.py` Stage 1: one `client.chat(brainstorm_messages(...))`
  call, then a second call to extract a `{"clues": [...]}` JSON list of
  candidates
- `clue_gen/generator.py` Stage 2 (already implemented — do not break): iterates
  over extracted candidates; runs `validate_solvability` + `validate_quality` on
  each; returns the first passing candidate as `ClueResult(clues=[clue])`; falls
  back to `candidates[0]` if none pass
- Currently `ClueResult.clues` always contains one entry. The `--candidates N`
  flag (pending Phase 3 in `plan.md`) will let callers request N clues. Design
  the extract turn to produce multiple candidates so Stage 2 has a pool to
  filter from.
- Quality schema lives in `clue_gen/quality.py`: `_QUALITY_FORMAT`,
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
   `clue_gen/solvability.py`)

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

- [x] **Split probe into shared harness and per-task scripts**
  - `scripts/probe.py` currently mixes harness logic (CLI, logging, HTTP) with
    prompt content. As more probes are added (brainstorm turns, other quality
    dimensions), this becomes unwieldy.
  - Split into: a shared harness module (CLI skeleton, tee logging, Ollama call)
    and small per-task scripts that supply their own prompt strings and invoke
    the harness. Each per-task script is self-contained and readable on its own.

- [ ] **Explore other quick wins for fast iteration**
  - After splitting the probe, survey what else would make prompt iteration
    faster or lower-friction before diving into the quality task queue.

- [x] **Switch probe harness to Ollama native API + add timing section**
  - [x] Step 1 — diagnostic: confirmed `usage.model_extra: {}` via OpenAI-
        compatible endpoint; per-phase durations not available that way.
  - [x] Step 2 — switched `harness.py` from openai SDK to `httpx.post` against
        `http://localhost:11434/api/chat`. Reasoning field is
        `message.thinking`. Schema passed as `format:` top-level key.
  - [x] Step 3 — added `--- timing ---` section: load ms, prefill tok/s,
        generation tok/s, ~reasoning/~content split (char-ratio estimate),
        overhead ms, wall s.

- [ ] **Investigate dense model attention across multiple conventions**
  - Observed: `gemma4:31b-mlx` (dense, not MoE) keeps reasoning tight and
    attention focused even when evaluating all five conventions in a single turn
    — the failure mode that motivated separating convention 2 may not apply to
    this model.
  - Questions to resolve: does the dense model consistently outperform the MoE
    model on multi-convention focus? Is the gap large enough to change model
    selection for the conventions turn? Does this make the "Separate convention
    2" task unnecessary for dense models?
  - Use `scripts/probe_conventions.py` to compare side-by-side.

- [ ] **Explore token-reduction prompting**
  - Question: can we prompt the model to produce shorter responses without
    regressing reasoning quality? Shorter outputs reduce latency and make logs
    easier to scan.
  - Directions to try: explicit length instructions ("be concise"), structured
    verdict-first format (verdict before reasoning, not after), chain-of-thought
    compression prompts.
  - Measure: output token count and elapsed time vs. correctness on known test
    cases.

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
  - Use `scripts/probe_wordplay.py` with `--clue` and `--answer` overrides.
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

- [ ] **Decide `cross_check_payoff` day-range profiles and add calibration
      tests**
  - Day-range tests for `cross_check_payoff` were deferred from the schema test
    task — the acceptable score bounds per day are not yet decided
  - Mon: low CP likely acceptable (clue can be fairly direct); Sat: high CP
    expected (clue should leave genuine ambiguity for crosses) — exact bounds
    TBD
  - Once decided: add ranges to `DAY_PROFILES` in `quality.py`, add
    corresponding xfail tests to `test_quality.py` (before updating
    `_scores_match_day`), and update the `cross_check_payoff` default in
    `_make_reply`

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
    - Add `--candidates N` flag to `clue_gen/cli.py` (default 1); pass `N`
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
