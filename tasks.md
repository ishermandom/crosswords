# Pending tasks

Status key: `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` dropped

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

- [x] **Resolve: Turn 5 results → extract flow**
  - Decision: extract all candidates (option a) — validation sorts.
  - Rationale: fresh-context validation is more reliable than in-context Turn 5
    judgment (context dilution by turn 7); no candidates are lost to Turn 5
    noise; the extract schema stays a flat `{"clues": [...]}` list. The Bullshit
    Rating failure mode (fake alternatives) is covered once
    `conventions.has_genuine_alternatives` lands in the quality schema — that
    field makes quality validation the authoritative backstop for this check.
  - Dependency: the quality schema update task must land before or alongside the
    brainstorm implementation; without `has_genuine_alternatives`, fake-
    ambiguity clues can pass validation undetected.

- [x] **Write tests for brainstorm prompt sequence** (TDD — tests before
      implementation)
  - `test_prompt.py`: stubs for `brainstorm_system_prompt` and
    `brainstorm_turns` added to `prompt.py`; 8 xfail tests cover turn content,
    difficulty calibration, and extract schema
  - `test_generator.py`: 3 xfail tests cover 7-call count, message accumulation,
    and `response_format` on the extract call; `FakeChatClient.response_formats`
    field added to support the last assertion

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

- [ ] **Update quality schema** (separate from brainstorm work; can be done in
      parallel)
  - In `clue_gen/quality.py`:
    - Rename `scales.wordplay_complexity` → `scales.elasticity`; update
      description to "supports multiple coherent interpretations, not just
      complexity" (background rewards LS/EL, not raw complexity)
    - Add `scales.cross_check_payoff` (1–5 + rationale): does the clue leave
      meaningful ambiguity for crosses to resolve, or does it already determine
      the answer?
    - Add `conventions.has_genuine_alternatives` (boolean): the Bullshit Rating
      — "the clue suggests plausible alternative answers that are real words or
      phrases a solver would actually consider"
  - Update `_QUALITY_FORMAT` JSON schema, `_STRUCTURED_OUTPUT_PROMPT` example,
    `_SYSTEM_PROMPT_TEMPLATE` descriptions, and parsing code
  - Update `clue_gen/tests/test_quality.py` to cover new fields

- [x] **Write tests for updated quality schema** (TDD — before schema changes)
  - `_make_updated_reply` helper added to `test_quality.py` with new field names
  - 5 xfail tests cover: `has_genuine_alternatives=False` fails; parse errors
    for non-boolean `has_genuine_alternatives`, old `wordplay_complexity` field
    name, missing `cross_check_payoff`, and out-of-range `cross_check_payoff`

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
    `_make_updated_reply`

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
