# Handoff log

---

## 2026-06-09 — First clue_gen_cloud smoke batch (3 words, Fable)

**Accomplished**

- Ran the first real batch through the new `clue_gen_cloud` pipeline: a 3-word
  smoke test from a clean `out/` (no prior state).
- Command: `python3 pipeline.py run --batch-size 3 --limit 3 --model
  claude-fable-5` (run from `clue_gen_cloud/`). Single batch, two `claude -p`
  calls (GENERATE + VERIFY).
- Processed the top three words of `words.in` (pre-sorted by value): ZERO, NIL,
  ONE.
- Result line: `[batch 1] words=3 (retries=0) clues=12 mech_pass=12/12 verdicts:
  accept=11 revise=1 reject=0`.
  - 12/12 clues passed mechanical checks (enumeration, anagram/hidden-string
    math, leakage, uniqueness).
  - Judge: 11 accept, 1 revise, 0 reject. 11 clues accepted into the bank
    (6 American / 5 cryptic; 10 high-confidence, 1 medium).
  - The lone revise was on NIL (cryptic "Nothing found in manila folder (3)"),
    so NIL is the 1 word "awaiting retry"; ZERO and ONE are fully settled
    (`completed_words=2/547`).

- **Accepted clues** (recorded here because `out/accepted.jsonl` is git-excluded):
  - ZERO — american/medium "Chance of rolling snake eyes with one die";
    american/hard "Climax of a countdown?";
    cryptic/medium "Duck found in blaze, roasting (4)";
    cryptic/medium "Love to set rifle sights (4)"
  - NIL — american/medium "Goose egg, across the pond";
    american/hard "Either side of a goalless draw?";
    cryptic/medium "Zip almost all of the Nile (3)"
  - ONE — american/medium "Formal alternative to \"you\"";
    american/hard "Singular figure?";
    cryptic/medium "Unit of money, in part (3)";
    cryptic/medium "Individual working with energy (3)"

**Decisions**

- **Default clue counts** (2 American + 2 cryptic per word) and **Fable
  model** (`claude-fable-5`) for the run, per user direction. Dry-run skipped.
- **No PR of generated output**: `out/` is gitignored append-only derived
  state by design, so the clue bank is intentionally not committed.

**Environment notes**

- No `~/.claude/oauth-token` file present; the CLI wrapper fell back to the
  account's default credentials and the calls succeeded.
- Repo is a sparse checkout (cone mode); only `clue_gen_cloud` was initially
  present. Added `.claude` to the sparse set to materialize this handoff.

**Next steps**

- Scale up: a larger `--limit` (or no limit) will pick up the NIL retry plus
  fresh words from the top of `words.in`.
- Consider `python3 pipeline.py stats` (incl. the by-batch-size table) once
  more data accumulates, to calibrate `--batch-size`.

---

## 2026-06-05 — Convention 2 prompt engineering

**Accomplished**

- Restructured `quality.py` system/user prompt split: all convention and rubric
  definitions moved into their respective user turns (recency bias; system
  prompt now just persona + day)
- Enabled thinking mode by default in `OllamaClient` (`reasoning_effort=None`);
  added reasoning trace logging with estimated token count
- Added `GEMMA4_26B_MLX`, `QWEN36_27B_MLX`, `QWEN36_35B_MLX` to `Model` enum
- Created `test_conventions.sh`: isolated multi-convention curl probe with
  header logging, timing, and reasoning output
- Overhauled `test_wordplay.sh`: updated to gatekeeper persona, C1 reframe,
  solver simulation framing, few-shot examples, safe `jq --arg` construction,
  reasoning output, and timing
- Iterated through a sequence of prompt improvements for the `?` convention,
  validated in curl scripts: gatekeeper persona → C1 reframe ("answer having
  multiple meanings is irrelevant") → solver simulation framing ("reason from
  clue to answer, not the other way around") → few-shot examples
- Updated `tasks.md` with 6 new tasks; updated `prompting.md` with 4 new
  generalizable findings from this session

**Decisions**

- **Gatekeeper persona over evaluator persona**: default "evaluator" framing
  produces approval-seeking behavior; "quality gatekeeping: catch errors" +
  "well-intentioned but inexperienced constructor" removes the implicit prior
  that the submission is probably correct
- **C1 reframe over C2**: "the answer having multiple meanings is irrelevant"
  replaced "even if extra meanings exist" — reframes as a positive test rather
  than arguing against a misreading
- **Few-shot examples as primary intervention**: pattern-matching against
  concrete examples (CLOCK, NEEDLE, TEAMSTER, SNAIL) proved more reliable than
  refining abstract rules; the model directly compared the test case against the
  examples rather than reasoning from first principles
- **Convention 2 deserves its own turn**: validated structurally — it dominates
  attention when co-evaluated with conventions 1/3/4/5, which are largely
  vacuous passes. Isolated evaluation produces tighter, faster reasoning. Not
  yet implemented in `quality.py`.
- **Prompt improvements not yet ported**: all changes validated in curl scripts
  only; `quality.py` still has old prompts. Deliberate — iterate in scripts
  first, port when stable.

**Files modified**

- `clue_gen/client.py` — thinking mode default, reasoning trace logging, new
  Model enum entries
- `clue_gen/quality.py` — system/user prompt restructure (definitions in user
  turns); committed as `6cfe241` (earlier in prior session context)
- `test_conventions.sh` — new file; gatekeeper persona, C1 reframe, solver
  simulation framing, reasoning output, timing
- `test_wordplay.sh` — full overhaul (see above)
- `tasks.md` — 6 new tasks, existing few-shot task updated to `[~]`
- `prompting.md` — 4 new sections in Validation design + Multi-turn design

**Next steps**

1. Overhaul iteration scripts (first in task list): auto-timestamped log files,
   prompt written to log, consider Python rewrite for ergonomics
2. Validate `?` evaluation in both directions with updated `test_wordplay.sh`
   (TEAMSTER and SNAIL as earned-? test cases)
3. Port prompt improvements to `quality.py` once validation is complete
4. Separate convention 2 into its own evaluation turn in `validate_quality`

**Avoid**

- **Adding a procedural stop condition alone**: "once you find a direct reading,
  stop" — we considered this (option B) but the model's problem is deeper than
  missing a stop rule; it keeps deliberating past correct conclusions. Persona
  - examples addressed the root cause more reliably.
- **Refining the rule text in isolation**: multiple rounds of rewording "even if
  extra meanings exist" / "not when a justification can be found" produced
  diminishing returns. Examples proved more effective.
- **Using "Focuses on the road?" → FORD as a test case**: requires brand
  knowledge (Ford makes a model called the Focus) that the model doesn't
  reliably have. The model falsely FAILs it. Tracked in escape-hatch task.

**Reflection**

_Token efficiency_:

- **Large log file reads**: `2026-06-04T22-35-12.log` (~38KB, ~9,500 tokens) was
  read in full. The relevant content was the convention 2 reasoning and final
  verdict — perhaps 20% of the file. The cause: no grep/offset was used to
  locate the relevant section first. Mechanism: use
  `grep -n "conventions scratchpad\|wordplay" <log>` to find line numbers, then
  read a targeted range.
- **Research subagent**: returned ~42K tokens of content for the few-shot
  examples task, most of which was source citation detail not needed for the
  prompt. Cause: the prompt didn't cap response length or specify "just the
  examples and reasoning, no sourcing detail." Mechanism: add "under 300 words,
  examples and reasoning only" to research prompts when the output feeds
  directly into prompt text.

_Attention efficiency_:

- **Extended whack-a-mole on convention 2 wording**: four rounds of prompt
  iteration (original → "even if extra meanings exist" removal → gatekeeper →
  solver simulation → examples) happened sequentially with a model run between
  each. The final intervention (examples) was available as an option early (it
  was `[?]` in tasks.md). We could have reached it faster by testing examples
  alongside the other changes rather than treating them as a later phase.
  Diagnosis: existing task list wasn't consulted as a source of candidate
  interventions mid-iteration. Mechanism: at the start of a prompt-iteration
  session, review pending tasks for related interventions and plan the test
  sequence rather than improvising.
- **FORD test case**: running "Focuses on the road?" → FORD consumed a full
  model run (~108s) and produced a false FAIL for a non-obvious reason. The risk
  was flagged before the test ("requires brand knowledge") but the test was run
  anyway. Mechanism: when a test case has a known risk factor, resolve it
  (confirm model knows the pivot) or pick a safer case before running.

---

## 2026-05-22 — Solvability implementation

**Accomplished**

- Implemented `validate_solvability` in full: two-turn call structure
  (scratchpad + guesses), length filtering, pass/fail rank check
- Added `SolvabilityParseError` with logging of the raw reply on failure;
  `_check_solvability` in CLI catches it and emits error JSON
- Added `format` parameter to `ChatClient` protocol, `OllamaClient`, and
  `FakeChatClient`; guesses call passes `_GUESSES_FORMAT` JSON schema to Ollama
  to constrain output shape
- Added debug logging: scratchpad reply, raw guesses (count + values),
  length-filtered guesses (count + values or `(none)`), answer rank or absence
- Removed all `xfail` markers from `test_solvability.py` and the four
  now-passing CLI tests; cleaned up stale `answer_rank` references
- Renamed "Turn 1/Turn 2" to "scratchpad/guesses" throughout
- Added `qwen3.5:4b`, `qwen3.5:9b`, `qwen3.5:27b` to `Model` enum
- Added TODO coverage for: parse errors, fence stripping, lowercase
  normalization, structured output format assertion (needs FakeChatClient
  extension), and all new logging behaviors

**Decisions**

- `validate_solvability` returns `bool` only — rank is debug-logged but not
  exposed to callers; `answer_rank` references removed from plan and tests
- `format` is a per-call parameter on `chat()`, not in `ModelOptions`, because
  scratchpad (free text) and guesses (JSON schema) need different values in the
  same function
- `SolvabilityParseError` catches both `json.JSONDecodeError` and `KeyError`
  from `_parse_guesses`, logged with the raw reply before raising

**Files modified**

- `clue_gen/solvability.py` — full implementation
- `clue_gen/client.py` — `format` param on `ChatClient` + `OllamaClient`; new
  model entries
- `clue_gen/cli.py` — catches `SolvabilityParseError`; updated import
- `clue_gen/tests/fake_client.py` — `format` param; TODO for `formats` list
- `clue_gen/tests/test_solvability.py` — xfails removed; TODOs added
- `clue_gen/tests/test_cli.py` — xfails removed; `_ConnectionErrorClient`
  updated; `answer_rank` assertion dropped
- `plan.md` — return type entry updated

**Next steps**

- Implement the `test_solvability.py` TODOs (parse errors, fence stripping,
  lowercase normalization, logging, structured output format)
  - Format TODO requires extending `FakeChatClient` with a `formats` list first
- Smoke-test with `qwen3.5:9b` or `qwen3.5:27b` — 4b produced only 1
  length-matched guess for "Celestial body" / MOON
- Implement `validate_quality` (next phase per plan.md)

**Avoid**

- `replace_all=True` with a replacement containing `\n` to remove decorators —
  leaves double blank lines requiring a follow-up cleanup pass. Target each
  removal individually instead.

**Reflection**

- _Token efficiency_: The `replace_all=True` decorator-removal approach required
  five follow-up Edits to fix double blank lines — six round-trips where two
  targeted Edits (one per decorator block) would have sufficed. Diagnosis:
  reached for the blunt tool without checking how the replacement string would
  interact with surrounding whitespace. Mechanism: before using `replace_all`
  with whitespace in the replacement, mentally simulate what the result looks
  like at one occurrence.
- _Attention efficiency_: The `answer_rank` cleanup (removing from test and
  plan) was prompted by the user pointing to the log — it could have been caught
  during the same turn that dropped the field from the return type, since `grep`
  on the symbol would have surfaced both sites immediately. Mechanism: after
  intentionally removing a named concept, grep for it before closing the turn.

---

## 2026-05-21 — Solvability TDD + API simplification

### Accomplished

- Implemented all TDD stubs in `clue_gen/tests/test_solvability.py` (10 tests
  across 4 sections: input shape, multi-turn structure, length filtering,
  pass/fail criterion)
- Added `_validate_solvability` wrapper to hide irrelevant params at call sites
- Simplified `SolvabilityResult` dataclass away entirely —
  `validate_solvability` now returns `bool`; updated `cli.py` and `validator.py`
  accordingly
- Updated `~/.claude/rules/testing.md` with two new rules: "Comment non-obvious
  expectations" and "Only expose relevant parameters at call sites"

### Decisions

- **`bool` over `SolvabilityResult`**: `is_solvable` was derivable from
  `answer_rank` and the threshold; `answer_rank` wasn't needed by callers. Rank
  can be logged inside the function if diagnostics are needed later.
- **`_validate_solvability` wrapper with `*` keyword-only params**: forces call
  sites to name every non-default argument, making tests self-documenting and
  preventing silent positional-order mistakes.
- **Literal guesses over `DEFAULT_MAX_ANSWER_RANK`**: tests choose their own
  small N rather than tying to the production constant — decouples tests from
  calibration decisions.

### Files modified

- `clue_gen/tests/test_solvability.py` — all test stubs implemented
- `clue_gen/solvability.py` — `SolvabilityResult` removed; return type → `bool`
- `clue_gen/cli.py` — `dataclasses.asdict(result)` → `{'is_solvable': result}`
- `clue_gen/validator.py` — `SolvabilityResult | None` → `bool | None`
- `~/.claude/rules/testing.md` — two new testing rules added

### Next steps

- Implement `validate_solvability` (production logic); all tests are xfail stubs
  ready to drive TDD
- Remove `@pytest.mark.xfail(strict=True)` markers as each TODO in the function
  body is implemented
- Fix duplicate TODO comment at lines 50–55 (already collapsed to one test, but
  double-check the file is clean)

### Avoid

- Don't restore `SolvabilityResult` — the simplification was deliberate. If rank
  is needed for metrics/logging later, add it back then with a concrete use
  case, not speculatively.

### Reflection

- _Token efficiency_: the main cost was re-reading `solvability.py` twice — once
  for the return type, once for the full file before the `Write`. The second
  read could have been avoided by scoping the first grep wider (pulling the full
  function body alongside the return type). Diagnosis: two separate narrow reads
  where one slightly broader read would have sufficed.
- _Attention efficiency_: the two-assert vs. one-assert detour on
  `test_rank_recorded_on_fail` was a small but avoidable inconsistency — the
  split assertion style had no justification given the established pattern. A
  pre-write style check against the existing tests would have caught it before
  the user had to.

---

## 2026-05-21 — First solvability test (TDD)

**Accomplished**

- Added `@pytest.mark.xfail(strict=True)` rule to `~/.claude/rules/testing.md`
- Wrote `test_answer_word_absent_from_solvability_call` in
  `clue_gen/tests/test_solvability.py` — marked xfail, uses `_make_replies`
  builder
- Added `_make_replies` builder: accepts native `Sequence[str]` for guesses,
  serializes to JSON internally

**Decisions**

- Builder named `_make_replies` (not `_replies`) per testing guide
  `_make_foo`/`_build_foo` convention
- `guesses` param is `Sequence[str]` (abstract) with a `list` default; builder
  serializes to `{"guesses": [...]}` JSON — callers never touch wire format
- `xfail(strict=True)` so the suite flags when the production code lands and the
  marker needs removal

**Files modified**

- `clue_gen/tests/test_solvability.py`
- `~/.claude/rules/testing.md` (added xfail rule)

**Next steps**

- Implement `test_answer_length_present_in_solvability_call` — assert the
  answer's letter count (not the word) appears in messages sent to the client
- Continue through the remaining 10 TODO tests in order, one per increment
- After all tests are xfail-written, implement `validate_solvability`

**Avoid**

- Copying `test_generator.py`'s `_replies()` helper as a model — it violates
  both the naming rule (`_make_foo`) and the serialization rule (callers pass
  raw JSON strings). That file needs the same fix before new tests follow its
  pattern.

**Reflection**

- _Token efficiency_: largest cost was reading `client.py` (~7 KB) and
  `validation.md` in two passes (~3 KB total) — both were necessary for
  understanding the function signature and output format. The real waste was
  reading `~/.claude/docs/testing-guide.md` at the old path (file has since
  moved); the content was returned but the CLAUDE.md instruction pointing there
  is stale. Fix: update the CLAUDE.md reference to `~/.claude/rules/testing.md`
  so future sessions don't follow a stale path.
- _Attention efficiency_: three rounds of back-and-forth on rule violations
  (`xfail`, `_replies` naming, serialization, default list vs. tuple) that
  should have been caught in one pass before presenting code. Each was a
  separate rule in the testing guide I had just read. Mechanism: before
  presenting any test code, explicitly diff it against the testing guide
  bullet-by-bullet — not just recall it from memory.

---

## 2026-05-21 — Validator stubs, CLI subcommands, testable pipeline

### Accomplished

- Added `solvability.py`, `quality.py`, `validator.py` with frozen dataclass
  result types and `NotImplementedError` stubs ready for TDD implementation
- Refactored `cli.py`: argparse subparsers (`run`, `generate`, `solvability`,
  `quality`); extracted `_run_pipeline` to separate file I/O from logic;
  `main()` accepts injectable `argv`, `client`, `output` for testing
- Wrote 4 CLI solvability tests (strict xfail) using builder pattern, testing
  through `main()` including arg parsing
- Deleted dead `load_words_file` (cli.py now opens files itself)
- Spent a full session segment reviewing/improving `testing-guide.md`: added
  builder naming convention, "don't wrap the subject under test," "vary inputs
  not the fake," trigger-based rewrites of DAMP and I/O boundary rules, split
  scripted fakes into implementing vs. using

### Decisions

- `main()` takes `argv`, `client`, `output` parameters — avoids monkeypatching
  `sys.argv`/`sys.stdout` and enables tests to exercise arg parsing
- `_run_pipeline` accepts `io.TextIOBase` stream, not a file path — enables
  `io.StringIO` in tests with no temp files
- `xfail(strict=True)` so unexpected passes surface as errors, forcing marker
  removal when implementation lands
- `load_words_file` deleted; its only test covered built-in `open()` behavior

### Files modified

- `clue_gen/cli.py` — subcommands, `_run_pipeline`, injectable `main()`
- `clue_gen/word_parser.py` — removed `load_words_file`
- `clue_gen/tests/test_cli.py` — solvability xfail tests, builders
- `clue_gen/tests/test_word_parser.py` — removed `load_words_file` test
- `clue_gen/quality.py`, `solvability.py`, `validator.py` — new stubs
- `clue_gen/tests/test_quality.py`, `test_solvability.py`, `test_validator.py` —
  new TODO stubs
- `plan.md`, `validation.md` — updated status and checklist
- `~/.claude/docs/testing-guide.md` — rule additions (uncommitted in dotfiles)

### Next steps

1. Implement `validate_solvability` in `solvability.py` — makes the 4 xfail CLI
   tests pass; design doc and checklist are in `validation.md`
2. Implement `validate_quality` in `quality.py`
3. Implement `validate_clue` in `validator.py`
4. Implement `_run_generate` and `_run_quality` in `cli.py`

### Avoid

- `tmp_path` for word list tests — use `_make_words_input(['WORD', ...])` which
  returns `io.StringIO`
- Custom stub client subclasses to vary reply content — pass different scripted
  replies to `FakeChatClient` instead
- Implementing production logic before writing tests (TDD violation)

### Reflection

**Token efficiency**

- Linter `system-reminder` blocks re-sent the full contents of `cli.py` and
  `test_cli.py` after every edit — roughly 5–6 reads of each file (~2K tokens
  per read) contributed by the hook, not by explicit `Read` calls. Diagnosis:
  iterative small edits to the same files triggered many linter notifications.
  Mechanism: batch related edits to the same file into fewer tool calls.
- `claude-rules-style.md` (~5KB) was read to apply style checks, then its
  content was actively used in the reflection discussion — justified cost.

**Attention efficiency**

- The tmp_path → io.StringIO → \_run_pipeline refactor required three rounds of
  steering. Diagnosis: I started implementing tests before reading the testing
  guide carefully enough to see "no temp files" and the I/O boundary pattern
  clearly applied. Mechanism: after reading the testing guide, explicitly verify
  each rule against the planned test structure before writing any test code.
- The "vary inputs not fakes" and TDD-order corrections share a root cause:
  writing code before fully applying the constraints. Both would have been
  caught by a pre-implementation checklist pass against the loaded rules.

---

## 2026-05-21 — Validation design doc

**Accomplished**

- Created `validation.md`: full design for the two-call validation architecture,
  including solvability call, quality call, six rubric scales, day profiles,
  output schemas, error handling, and open questions
- Updated `plan.md`: Phase 2 description updated to reflect two-call design;
  Phase 3 "Design validation prompt" task now points at `validation.md`; added
  task to consider different models for generation vs. evaluation (qwen for
  brainstorm, gemma4 for validation as one candidate split)

**Decisions**

- **Two-call architecture**: solvability call is blind (no answer word); quality
  call is answer-aware. Single call can't satisfy both constraints.
- **Style hint instead of day name** in solvability call: naming the day
  contaminates the model's guess distribution with day-type priors (it "knows"
  Thursday answers are tricky), producing false passes on weak clues. Style hint
  ("this clue may use wordplay; consider multiple interpretations") calibrates
  persistence without that contamination.
- **Six rubric scales, not anti-patterns list**: angle craft, misdirection,
  wordplay complexity, reference accessibility, surface coherence, fairness of
  deception. Anti-patterns are the low end of these scales, not a separate list.
- **Craft and fairness are quality floors**: high scores expected on all days;
  misdirection/wordplay/accessibility are the difficulty axes.
- **Convention failures reject immediately**: rubric scales not evaluated on a
  convention violation.
- **Solvability rank recorded regardless of pass/fail**: secondary difficulty
  signal (rank 1 on a Saturday clue = clue may be too easy for day).
- **Score range mapping**: low = 1–2, mid = 3, high = 4–5 (provisional, to be
  tightened against golden set).

**Files modified**

- `validation.md` (new)
- `plan.md` (updated)

**Next steps**

- Build a golden set of known-good NYT clues spanning Mon–Sat to calibrate N,
  validate day profiles, and derive pass/fail thresholds
- Implement the two-call validation infrastructure (per `plan.md` Phase 3)
- Write the actual prompt text for both calls, matching the spec in
  `validation.md`

**Avoid**

- Providing the difficulty day name to the solvability call — contaminates
  guesses with day-type priors; use a style hint instead
- Aggregating rubric scales into a single score — pass/fail requires matching a
  day-appropriate profile, not crossing a total threshold
- Separate anti-patterns section — they're the low end of the scales

**Reflection**

_Token efficiency_

- The web research subagent for solver enjoyment dimensions (~10 items with
  citations) was the largest single output. Justified by the user's explicit
  "brainstorm and/or research" request, but the agent returned full citation
  URLs that weren't needed. Mechanism: add "findings only, no source URLs unless
  essential for a follow-up action" to subagent prompts by default (already in
  CLAUDE.md's cap-subagent-output rule — just apply it).
- plan.md and prompting.md were auto-injected via system-reminder, which was
  appropriate. No unnecessary re-reads during the session.

_Attention efficiency_

- The `git -C` mistake cost one round-trip and a correction. Diagnosis: habit
  from multi-repo contexts bled in; the rule is in CLAUDE.md but wasn't checked
  before the git commands. Mechanism: before any git command, confirm `pwd`
  explicitly rather than assuming.
- The AskUserQuestion calls were well-placed and consistently moved decisions
  forward; no significant back-and-forth tangents.

---

## 2026-05-19 — Code review + mypy/style cleanup

### Accomplished

- Full self-review of all Python source files
- Fixed all 47 mypy errors across 5 files:
  - Added `-> None` to all test functions
  - `reasoning_effort: str` → `Literal[...]` in `ModelOptions` to satisfy SDK
    overload
  - Replaced `**extra_kw: dict[str, object]` with direct `max_tokens=` kwarg
    (was breaking overload resolution)
  - Fixed `'str' in content` checks with `isinstance(content, str)` narrowing
  - Moved `GenerationError` import in `test_generator.py` to its canonical home
    (`clue_gen.client`)
- Replaced `Any` with `object` in `_extract_json_object` return type; tightened
  call site to fall back on non-string `clue` field
- Fixed docstring bug: `OllamaClient.chat` said "Raises ValueError", code raises
  `GenerationError`
- Renamed `_noisy` loop variable → `logger_name` (underscore prefix implied
  unused)
- Fixed `__exit__` docstring line length in `fake_client.py`
- Rewrote `test_prompt.py` from class-based grouping to flat functions with
  comment section headers (matching `test_generator.py` style)
- Updated `~/.claude/rules/python.md`: added `No Any` rule and a `## Testing`
  section with the grouping preference

### Decisions

- `object` over `Any` for `_extract_json_object` return type — forces explicit
  narrowing at every use site; `Any` silently skips type checking
- `object` over union (`dict[str, str | bool | ...]`) — the union offers no
  benefit (still requires narrowing) and would break on unexpected model output
  shapes
- Flat test functions over test classes — less nesting, same grouping
  expressiveness via comments; classes only warranted when shared fixtures are
  needed

### Files Modified

- `clue_gen/client.py` — `Literal` type for `reasoning_effort`; removed
  `extra_kw`; docstring fix
- `clue_gen/generator.py` — `Any` → `object`; removed `from typing import Any`;
  tightened `clue` field extraction
- `clue_gen/cli.py` — renamed `_noisy` → `logger_name`
- `clue_gen/tests/fake_client.py` — `__exit__` docstring line length
- `clue_gen/tests/test_cli.py` — `-> None` annotations
- `clue_gen/tests/test_generator.py` — `-> None`; `GenerationError` import
  source; `isinstance` narrowing
- `clue_gen/tests/test_prompt.py` — full rewrite: class → flat functions
- `clue_gen/tests/test_word_parser.py` — `-> None` annotations
- `~/.claude/rules/python.md` (dotfiles) — `No Any` rule; `## Testing` section

### Next Steps

- Commit all changes before continuing Phase 3 prompt work
- Phase 3: redesign brainstorm and validation prompts (several TODOs in test
  files reference this)

### Avoid

- `**extra_kw: dict[str, object]` unpacked into an overloaded SDK call — mypy
  cannot verify value types through `**kwargs`, causing the entire overload to
  fail. Pass optional params directly with their typed values instead.

### Reflection

- **Token efficiency**: The `Explore` subagent call to read all 11 source files
  upfront was the largest single cost (~15k chars of file content ≈ ~4k tokens),
  but it was justified — the review genuinely needed all files in context
  simultaneously. The bigger inefficiency was the first mypy fix attempt: I
  wrote `reasoning_effort: Literal[...]` but missed that `**extra_kw` was the
  actual overload-breaking culprit, requiring a second round. Diagnosis: I
  pattern-matched to the `reasoning_effort` type mismatch mentioned in the error
  without reading the full overload failure message carefully. Mechanism: when a
  `call-overload` error lists multiple argument types, check for `**kwargs`
  expansion first — it's a common cause that invalidates the entire call
  regardless of individual arg types.
- **Attention efficiency**: The `_noisy` naming issue and line-length fixes were
  flagged in the review but didn't get fixed until explicitly asked. These
  should have been bundled into the first round of fixes rather than left as
  trailing work across multiple turns.

---

## 2026-05-18 — Performance debugging + Ollama options

**Accomplished**

- Added per-call timing and token-count logging to `client.py`; added stage
  labels and wall-clock logging to `generator.py`
- Diagnosed and fixed thinking-model slowness: `reasoning_effort='none'` is the
  correct control via the `/v1` endpoint; `think=False` in `extra_body` is
  silently ignored
- Replaced `ModelOptions` with full parameter set (OpenAI top-level:
  `temperature`, `max_tokens`, `frequency_penalty`, `reasoning_effort`; Ollama
  options: `num_ctx`, `keep_alive`, `top_k`, `top_p`, `repeat_penalty`,
  `num_gpu`); added `DEBUG_OPTIONS` constant hardcoded as default
- Suppressed HTTP stack debug noise (`httpcore`, `openai._base_client`); added
  model-reply content logging in `generator.py` instead
- Updated `CLAUDE.md`: subagent output cap rule, incremental file reading rule,
  flipped "Check context before Read" to "Don't Read without justification"
- Updated `wrap-session` skill to require quantitative token reflection

**Decisions**

- `reasoning_effort='none'` confirmed working via curl before changing code;
  `think=False` in `extra_body` confirmed non-functional
- `DEBUG_OPTIONS` hardcoded as `OllamaClient` default with TODO to switch to
  `ModelOptions()` once prompt tuning is complete
- `max_tokens` raised 64 → 256 → 512; 64 and 256 both caused truncated JSON in
  brainstorm and validation calls; 512 adequate for validation but brainstorm
  still hits cap

**Files Modified**

- `clue_gen/client.py`, `clue_gen/generator.py`, `clue_gen/cli.py`
- `~/.claude/CLAUDE.md` (via dotfiles), `~/.claude/skills/wrap-session/SKILL.md`

**Next Steps**

- Phase 3 prompt design: brainstorm turns, validation prompt, extract
  instruction — extract is the most broken (model stops mid-JSON reliably)
- Brainstorm always hits the 512-token cap; either raise further or redesign
  prompt to produce concise output
- Check `ollama show qwen3.5:2b` quantization — Q4_K_M would be ~1.5–2× faster
- Consider per-call `max_tokens` override so brainstorm gets more room than
  validation

**Avoid**

- `think=False` in `extra_body` — silently ignored by `/v1` endpoint; use
  `reasoning_effort='none'` as a top-level param instead
- `max_tokens` below 512 for this pipeline — validation JSON schema requires
  ~150+ tokens minimum; brainstorm needs more

**Reflection**

- _Token efficiency_: Four source files read in full early in session (~16,054
  chars → ~4,000 tokens); research agent output with 35 URLs (~7,500 chars →
  ~1,900 tokens); re-read of `client.py` (4,745 chars → ~1,186 tokens) after it
  was already in context. The re-read was the clearest avoidable waste — I
  reached for Read without checking context. Mechanism: new "Don't Read without
  justification" rule requires an explicit statement of why context is
  insufficient before calling Read.
- _Attention efficiency_: Background curl tests (think=true, OpenAI-endpoint)
  ran for many minutes and returned empty responses, consuming two turns to
  diagnose. The key finding could have been reached with a single foreground
  curl. Mechanism: for quick binary API tests, run foreground; reserve
  background for calls expected to take >30s where other work can proceed.

---

## 2026-05-18 — Model options + plan tasks

**Accomplished**

- Added `qwen3.5:0.8b` and `qwen3.5:2b` to the `Model` enum; marked `qwen3.5:2b`
  as the default smoke-test model in comments
- Added `ModelOptions` dataclass (`num_ctx=8192`, `temperature=0.7`,
  `min_p=0.05`) to `client.py`; `OllamaClient` accepts it at construction and
  passes all three fields via `extra_body.options` on every call
- Added two Phase 3 plan tasks: benchmark inference speed (new first unresolved
  task), and decide whether brainstorm vs. validation calls need separate
  `ModelOptions`

**Decisions**

- All three generation params go in `extra_body.options` rather than mixing
  top-level and extra_body — consistent for an Ollama-only client
- `ModelOptions` is constructor-level for now; per-call override deferred to the
  validation prompt design phase, tracked in plan.md
- `ChatClient` Protocol kept minimal — `ModelOptions` is Ollama-specific

**Files Modified**

- `clue_gen/client.py` — new `ModelOptions` dataclass, updated
  `OllamaClient.__init__` and `chat()`
- `plan.md` — two new Phase 3 tasks

**Next Steps**

- Benchmark inference speed: measure latency/tokens-per-sec per model, compare
  against expected Ollama throughput, investigate GPU vs CPU fallback if needed
- Decide brainstorm vs. validation `ModelOptions` split — natural to resolve
  when designing the validation prompt

**Avoid**

- Nothing tried and abandoned this session

**Reflection**

- `AskUserQuestion` for the `extra_body` placement was correct defensively, but
  the prompting guide already answered it — stating a recommendation and
  proceeding would have saved a round-trip. Mechanism: when an existing doc
  directly resolves a design question, cite it and move rather than polling.
- The per-call vs. constructor options question surfaced mid-implementation
  rather than in the upfront design pass. Mechanism: before touching code,
  enumerate all callers and check whether they'd need different values — that
  surfaces this class of question early.

---

## 2026-05-18 — Prompting guide written

**Accomplished**

- Researched best practices for prompting LLMs (two research rounds via web
  agents): first round covered local-model-specific mechanics; second round
  covered general prompting fundamentals and the reasoning-vs-non-reasoning
  distinction
- Wrote `prompting.md`: project-scoped reference for future prompt design
  sessions, covering the central frame, fundamentals, CoT scaffolding,
  multi-turn design, validation failure modes, JSON reliability, and local model
  parameters; ends with a pipeline map orienting each section to the brainstorm
  vs. validation call
- Reordered Phase 3 tasks in `plan.md`: prompting guide → validator design →
  brainstorm design → candidates/rejection/evaluation
- **Uncommitted**: `plan.md` has the prompting guide task marked `[x]` — commit
  this at the start of the next session

**Decisions**

- Guide framed around **reasoning vs. non-reasoning** capability, not local vs.
  hosted infrastructure — the latter is a proxy for the former and misled the
  first research round
- Project-scoped (not a general reuse artifact); lives at project root alongside
  spec.md and plan.md for now, moves to clue_gen/ during Phase 3 cleanup
- Cut from the guide: self-consistency (doesn't apply to creative generation),
  external grounding bullet (redundant with structured property checking),
  repeat penalty (too generic to be actionable), YAML alternative and GBNF
  grammar enforcement (out of scope for our stack)
- Validation call noted as "possibly multi-turn" — fresh context is the
  invariant, not single-turn

**Files modified**

- `prompting.md` — new
- `plan.md` — Phase 3 reordered; `[x]` mark on prompting guide task
  (uncommitted)

**Next steps**

- Commit the `plan.md` `[x]` mark
- Begin validator design: read spec.md, plan.md, and prompting.md at session
  start before designing the validation prompt

**Avoid**

- Framing the local/hosted distinction as the primary axis — it obscures the
  reasoning-vs-non-reasoning gap that actually drives prompting differences

**Reflection**

- Two research rounds were needed because the first was framed around local vs.
  hosted mechanics rather than the reasoning capability gap. A clarifying
  question before dispatching the first agent ("what aspect of local model
  behavior are you most concerned about?") would have caught this. Mechanism:
  before spawning a research agent on a broad topic, ask one scoping question if
  the user's framing could map to multiple distinct problems.
- Three items added in self-review (persona persistence, CoT self-initiation,
  assistant priming) ended up bolted onto existing prose rather than integrated
  into the doc's architecture. This is structural debt from patching rather than
  revising. Mechanism: when a self-review surfaces more than one addition,
  consider a partial rewrite that integrates them cleanly rather than inserting
  each in place.
- The `[x]` mark on plan.md wasn't committed with the main commit because it was
  applied after the fact. Mechanism: update plan.md status before committing,
  not after.

---

## 2026-05-17 — Testing complete; gate_auto_tools hook

**Accomplished**

- Added fence-stripping tests to `test_generator.py` — `_strip_fences` was
  called but never triggered by prior test inputs; two tests now exercise it via
  fenced extract and validation replies
- Added `test_cli.py` with two CLI error-path tests: `APIConnectionError` → exit
  1, `GenerationError` → exit 1; used a stub client for the former and
  `FakeChatClient(['brainstorm', '[]'])` to naturally trigger the latter
- Loosened `_generate_clues` signature from `OllamaClient` to `ChatClient` to
  enable fake injection
- Testing section of `plan.md` fully resolved (tasks done/dropped with
  rationale)
- Added `gate_auto_tools.sh` global PreToolUse hook blocking
  pytest/ruff/mypy/prettier; hard block with behavioral guidance in
  `permissionDecisionReason`
- Added Configuration section to `CLAUDE.md` (global-by-default rule for hooks +
  all config); added Hooks scope-check as first bullet in Hooks section
- Added named regex components rule to Shell section of `CLAUDE.md`
- Removed "Trust hook automation" from Standing Rules — moved into hook's
  `permissionDecisionReason`, where it surfaces at the relevant moment

**Decisions**

- Hard block over "ask": user should not be prompted on reflexive tool use;
  self-assessment happens before reaching for the tool, not via a permission
  prompt
- `permissionDecisionReason` as model-facing memo: carries both the "why"
  (mid-turn false results) and the "what to do" (escalate to user with
  `! <command>`); surfaces at exactly the moment needed
- Dropped options/extra_body integration test: manual smoke test covers the same
  ground; automated test requires Ollama running and can't run in CI

**Files modified**

- `clue_gen/cli.py` — `_generate_clues` signature loosened to `ChatClient`
- `clue_gen/tests/test_generator.py` — two fence-stripping tests added
- `clue_gen/tests/test_cli.py` — new (2 tests)
- `plan.md` — Testing tasks resolved
- `/Users/Shared/code/dotfiles/claude/hooks/gate_auto_tools.sh` — new (renamed
  from block_pytest.sh)
- `/Users/Shared/code/dotfiles/claude/settings.json` — hook reference updated
- `/Users/Shared/code/dotfiles/claude/CLAUDE.md` — Configuration section; Hooks
  scope-check; Shell named-regex rule; Trust-hook-automation removed

**Next steps**

- Phase 3: `--candidates N` flag (next plan item)
- Phase 3: brainstorm turn design — difficulty encoding, style mix
- Phase 3: validation turn design — structured verdict per clue

**Avoid**

- "ask" mode for gate_auto_tools: prompts user every time; self-assessment is
  the model's job
- Project-scoped config for universal behavioral rules

**Reflection**

- Hook design required multiple correction rounds (project → global scope;
  pytest-only → all auto-tools; ask → hard block). Root cause: implemented
  before fully reasoning through the user's goal — "who should do the
  assessing?" is the key question for behavioral constraints and should be asked
  before choosing a mechanism. Upfront: one question ("should the user approve,
  or should you self-assess?") would have reached hard-block in one step.
- Tried to run tests manually despite the CLAUDE.md rule. Root cause: the rule
  was filed under "context efficiency" — wrong mental category for a reflexive
  verification habit. The gate_auto_tools hook now interrupts the reflex
  mechanically; the `permissionDecisionReason` explains both why and what to do.
  No further instruction needed.
- Initial hook placed in project `.claude/settings.json` rather than global
  `~/.claude/settings.json`. Root cause: no scope check before deciding where to
  put config. Mechanism: the new CLAUDE.md Configuration section + Hooks
  scope-check bullet is now the first thing encountered when adding a hook.

---

## 2026-05-17 — test_generator.py cleanup

**Accomplished**

- Flattened `TestGenerateClueCallSequence` and `TestGenerateClueResult` classes
  into top-level functions with section comments — indentation cost, no shared
  fixtures to justify classes
- Updated all tests to consistently use `with FakeChatClient(...) as fake:` —
  zero cost, and the reply-exhaustion check fires for free where it's meaningful
- Added module-level TODO about Phase 3 evolving the test assumptions
- Migrated two "possible future coverage" notes (exception injection,
  `APIConnectionError` propagation) from `testing.md` into the test file; framed
  as exploratory, not actionable
- Deleted `testing.md` (fully absorbed) and obsolete
  `feedback_formatter_aware_editing.md` memory

**Decisions**

- Section comments over classes: no shared state or fixtures meant classes were
  pure indentation overhead
- "Possible future coverage" framing: the two missing-coverage scenarios aren't
  pressing enough to frame as TODOs

**Files modified**

- `clue_gen/tests/test_generator.py`
- `testing.md` (deleted)

**Next steps**

- Phase 3 implementation — LLM interactions will likely require revisiting test
  assumptions

**Avoid**

- Nothing tried and abandoned

**Reflection**

- Used `Write` for the class-flattening edit based on a now-deleted memory
  (formatter-aware editing) that had already been superseded — wasted a
  full-file rewrite when sequential `Edit` calls would have done. Diagnosis:
  memory wasn't marked stale when the hook model changed. Mechanism: delete
  obsolete feedback memories promptly when the underlying assumption is
  corrected, rather than leaving them as partially-true caveats.
- Session was otherwise well-focused; no context drift.

---

## 2026-05-17 — generate_clue unit tests + run_tests Stop hook

### Accomplished

- Wrote `clue_gen/tests/test_generator.py`: 14 tests covering the brainstorm →
  extract → validate call sequence, `ClueResult` assembly, fallback behavior,
  error propagation, and multi-word answer length stripping; all passing
- Refactored tests from DAMP-violating module-level constants to inline literals
- Added global Stop hook (`~/.claude/hooks/run_tests.sh`) that calls
  `./run_tests` at end of each turn; blocks the turn and surfaces output when
  tests fail
- Added `@pytest.mark.wip` marker and `PYTEST_FROM_HOOK` env var so WIP tests
  are silently skipped by the hook but run when invoking `./run_tests` directly
- Updated global `CLAUDE.md`: added Shell section (named scripts, descriptive
  variables, arrays for optional args, no `set -e`, inline comments on flags)
  and Hooks section (trivial inline / nontrivial in scripts, Stop preference,
  validate after adding)
- Updated `~/.claude/docs/testing-guide.md`: added DAMP principle

### Decisions

- **Stop hook over PostToolUse**: a single turn often has dependent multi-file
  edits; PostToolUse fires between them and produces false failures
- **Hook in global settings, not project**: any project with a `./run_tests`
  script at the root benefits automatically; the hook exits silently when absent
- **`@pytest.mark.wip` + `PYTEST_FROM_HOOK`**: marks a test as intentionally
  failing during TDD; skipped by the hook, executed manually. Apply at the start
  of TDD work, before the hook has fired multiple times
- **Full output + blocking on failure**: the hook surfaces the full pytest
  failure to Claude; acceptable noise tradeoff vs. missing a genuine failure

### Files Modified

- `clue_gen/tests/test_generator.py` — new (14 tests)
- `clue_gen/client.py` — `ChatClient` protocol; `Sequence` types
- `clue_gen/generator.py` — `ChatClient` parameter; `Sequence` annotation
- `clue_gen/prompt.py` — `Sequence` return types
- `pyproject.toml` — `wip` marker registered
- `run_tests` — `PYTEST_FROM_HOOK` support; `-q` flag
- `/Users/Shared/code/dotfiles/claude/hooks/run_tests.sh` — new global hook
- `/Users/Shared/code/dotfiles/claude/settings.json` — hook added to Stop
- `/Users/Shared/code/dotfiles/claude/CLAUDE.md` — Shell + Hooks sections
- `/Users/Shared/code/dotfiles/claude/docs/testing-guide.md` — DAMP added

### Next Steps

1. `--candidates N` flag (next Phase 3 task in `plan.md`)
2. Design brainstorm turns: difficulty encoding, style mix
3. Design validation turn: structured verdict per clue
4. Add `options` dict to `OllamaClient`/`chat()` for integration smoke tests

### Avoid

- **PostToolUse for test hooks**: fires between dependent edits; use Stop
- **Inline shell logic in `settings.json` command field**: use `.claude/hooks/`
  scripts instead; they're auditable without running anything
- **Module-level test constants**: masks the inputs that define each test;
  inline literal values directly (DAMP principle)

### Reflection

- The hook went through ~6 iterations (PostToolUse → Stop, project → global, cd
  removed, hardcoded python command → `./run_tests`, file guard removed, output
  not surfaced → JSON blocking output). Root cause: each iteration fixed one
  constraint at a time rather than reading existing hooks + testing-guide.md
  first to understand the full pattern. Mechanism: before writing any hook, read
  the existing hook scripts and testing-guide.md — both document the conventions
  that drove every correction.
- The pipe-test attempt was blocked; the right verification pattern (deliberate
  failure + observe) emerged only after the skill prompt was re-read. Root
  cause: defaulted to the update-config skill's verification pattern rather than
  inferring from project conventions. Mechanism: when adding a hook, check
  existing hook scripts for the established verification approach before
  reaching for a generic workflow.
- DAMP refactor was a second pass after initial test writing. Root cause: wrote
  tests optimizing for DRY rather than readability. Mechanism: testing-guide.md
  now documents DAMP — reading it before writing tests would catch this in the
  first draft.

---

## 2026-05-17 — FakeChatClient + style-guide enforcement

**Accomplished**

- Created `clue_gen/tests/fake_client.py`: `FakeChatClient` with scripted
  replies, call recording, and context-manager support (`__enter__`/`__exit__`)
  that asserts all replies were consumed when the `with` block exits cleanly
- Updated `CLAUDE.md` (via dotfiles): added style-guide check reminder to the
  Review approach section
- Saved `feedback_style_check.md` memory with incident context

**Decisions**

- `__exit__` skips exhaustion check when an exception is already propagating, to
  avoid masking the real failure with a secondary assertion
- `not exception_type` over `exception_type is None` — idiomatic truth-value
  testing per style guide
- Universal rule goes in `CLAUDE.md`; incident context goes in memory

**Files modified**

- `clue_gen/tests/fake_client.py` — created
- `/Users/Shared/code/dotfiles/claude/CLAUDE.md` — style-check reminder added
- `memory/feedback_style_check.md` — created

**Next steps**

- Write `clue_gen/tests/test_generator.py`: start with the two test cases in
  `testing.md` (`test_uses_validator_clue_field`,
  `test_falls_back_to_first_candidate_when_validation_fails`)
- `FakeChatClient` is ready; open `testing.md` and `fake_client.py` for context

**Avoid**

- Nothing abandoned this session

**Reflection**

- Three style violations (naming, idiomatic `not`, missing docstrings) required
  user correction. Root cause: rules applied from memory while attention was on
  logic, with no explicit checklist step before presenting. Mechanism: the new
  CLAUDE.md line makes the checklist a standing rule rather than a mental note.
- The `__enter__` docstring took two rounds. First draft restated the code;
  second was closer but still needed a nudge. Root cause: didn't ask "what would
  a reader not already know from reading the code?" before writing. Mechanism:
  treat that question as a pre-writing prompt for every docstring.

---

## 2026-05-17 — ChatClient protocol + Sequence types

### Accomplished

- Added `ChatClient` Protocol to `client.py` (structural; `OllamaClient`
  satisfies it without changes)
- Updated `generate_clue` signature in `generator.py` to accept `ChatClient`
  instead of `OllamaClient`
- Changed `ChatResult.messages` from `tuple[Message, ...]` to
  `Sequence[Message]` — API contract expresses read-only intent; implementations
  use lists
- Updated `OllamaClient.chat` and `ChatClient.chat` parameters to
  `Sequence[Message]`
- Updated `brainstorm_messages` and `validation_messages` return types to
  `Sequence[Message]`; switched return literals from tuples to lists throughout
- Updated all prose comments that said "tuple" to say "list"
- Added three rules to global `CLAUDE.md`: plan documents, hook automation,
  abstract types in API signatures

### Decisions

- **`Sequence` over `list`/`tuple` in signatures**: `Sequence` is read-only (no
  mutation methods), so it expresses immutability at the interface level without
  over-constraining implementations. `list` implementations are fine and clearer
  — they're the more foundational primitive.
- **`ChatClient` as a Protocol**: structural (no inheritance); `OllamaClient`
  satisfies it without modification, same pattern as `TextIO`/`io.StringIO`
- **"list" in prose**: plain-language term for any ordered sequence; callers can
  inspect the type annotation for the concrete constraint

### Files Modified

- `clue_gen/client.py` — `ChatClient` Protocol; `Sequence` types throughout
- `clue_gen/generator.py` — `ChatClient` parameter; `Sequence` annotation;
  `[*messages, turn]` spread instead of tuple concat
- `clue_gen/prompt.py` — `Sequence` return types; list literals
- `/Users/Shared/code/dotfiles/claude/CLAUDE.md` — three new rules

### Next Steps

1. Create `clue_gen/tests/fake_client.py` with `FakeChatClient` (see
   `testing.md` for the full design)
2. Write `clue_gen/tests/test_generator.py`: happy path, fallback, call sequence
   assertions

### Avoid

- Nothing new this session.

### Reflection

- Early scope overreach (starting `fake_client.py` without being asked) and then
  a mis-read of the correction (reverting a correct generator change) cost two
  round-trips. Both traced back to treating a plan doc as authorization to
  proceed rather than a queue to pull from one item at a time.
- The duplicate `ChatResult` class was introduced by adding to a file without
  reading it first — a `Read` before any structural addition would have caught
  it immediately.
- Session produced lasting config value (three CLAUDE.md rules) alongside the
  code changes; the steering discussion was well-spent.

---

## 2026-05-17 — Testing doc: Protocol-based fake for LLM interaction

### Accomplished

- Wrote `testing.md` at project root: focused design doc answering "how to
  unit-test `generate_clue` without a live Ollama server"
- Established the `ChatClient` Protocol approach (single `chat` method),
  analogous to `load_words(stream: TextIO)` accepting `io.StringIO` in tests
- Designed `FakeChatClient` (scripted replies + call recording); decided shared
  location at `clue_gen/tests/fake_client.py`
- Included two worked test examples (happy path, fallback) and a limitations
  section with a TODO for exception injection

### Decisions

- **`ChatClient` Protocol over subclassing `OllamaClient`**: protocol-based
  fakes are lighter and don't inherit irrelevant state; matches the existing
  `TextIO` pattern in `word_parser`
- **Scripted string replies only (no per-call exception injection)**: the
  malformed-JSON error path in the validation loop is testable by scripting a
  bad JSON string — exception injection not needed for coverage. TODO added for
  the cases that do need it (brainstorm/extract `GenerationError` propagation).
- **Protocol lives in `client.py`**: minimal new surface; `OllamaClient`
  satisfies it structurally without changes
- **Fake in `clue_gen/tests/fake_client.py`**: shared across test files as
  coverage grows

### Files Modified

- `testing.md` — new

### Next Steps

1. Add `ChatClient` Protocol to `client.py`; change `generate_clue` type
   annotation from `OllamaClient` to `ChatClient`
2. Create `clue_gen/tests/fake_client.py` with `FakeChatClient`
3. Write `test_generator.py`: call sequence, `ClueResult` assembly, fallback,
   fallback warning, JSON extraction helpers exercised through public API
4. Add `options` dict to `OllamaClient`/`chat()` (plan task); write integration
   smoke tests

### Avoid

- **Testing `_strip_fences` / `_extract_json_list` / `_extract_json_object`
  directly**: per prior decision; exercise through `generate_clue`'s public API

### Reflection

- Session was lean and well-scoped: brainstorm → two AskUserQuestion decisions →
  write doc. No unnecessary implementation work.
- The `io.StringIO` framing was productive — it gave a concrete existing pattern
  to reason from rather than designing the Protocol from scratch.
- Effort level was set to `high` for a doc-writing session; `medium` would have
  been sufficient.

---

## 2026-05-17 — Test infrastructure: word_parser + prompt unit tests

### Accomplished

- Added pytest to dev deps; wired `[tool.pytest.ini_options] testpaths` in
  `pyproject.toml` so `python -m pytest` works without arguments
- Refactored `word_parser.load_words` to accept `TextIO`; added
  `load_words_file(path)` as the thin file-open wrapper; updated CLI caller
- Wrote 16 unit tests, all passing: 7 in `test_word_parser.py`, 9 in
  `test_prompt.py`; Phase 3 TODO comments on both prompt test classes
- Moved tests under `clue_gen/tests/` (not top-level) to keep the module
  self-contained for a repo that may grow to contain other tools
- Created `run_tests` executable at repo root
- Updated `plan.md`: marked word_parser and prompt test items `[x]`;
  consolidated generator helper tests into the `generate_clue` unit test item;
  renamed "integration test" → "unit tests for `generate_clue` via a fake
  `OllamaClient`"; added Cleanup phase for moving spec/plan into `clue_gen/`

### Decisions

- **Tests under `clue_gen/tests/`**: repo may grow to contain other tools;
  clue_gen should be fully self-contained. Top-level `tests/` was the initial
  choice and was corrected mid-session.
- **Private helpers not tested directly**: `_strip_fences`,
  `_extract_json_list`, `_extract_json_object` will be exercised through
  `generate_clue`'s public API with a fake `OllamaClient` — per user direction
  and the testing guide
- **`load_words` accepts `TextIO`**: avoids temp files (testing guide rule);
  `load_words_file` wraps the open call for production use

### Files Modified

- `pyproject.toml` — pytest added to dev deps; testpaths config added
- `clue_gen/word_parser.py` — `load_words` now takes `TextIO`; `load_words_file`
  added
- `clue_gen/cli.py` — updated import and call site to use `load_words_file`
- `clue_gen/tests/__init__.py` — new
- `clue_gen/tests/test_word_parser.py` — new (7 tests)
- `clue_gen/tests/test_prompt.py` — new (9 tests)
- `run_tests` — new executable
- `plan.md` — testing section updated; Cleanup phase added

### Next Steps

1. Unit tests for `generate_clue` via a fake `OllamaClient` — next Testing item
   in `plan.md`; private parsing helpers exercised here
2. `OllamaClient` options dict (needed before smoke tests)

### Avoid

- **Top-level `tests/`**: doesn't fit the multi-tool repo structure
- **Testing private helpers directly**: user preference; exercise them through
  `generate_clue`'s public API

### Reflection

- The test location question could have been pre-empted by asking about repo
  structure intent before writing any tests — cost was one move + two config
  updates.
- Session was otherwise tight: public-API testing principle → load_words
  refactor was a direct inference, and the plan update was mechanical.
- The `generate_clue` unit test is the last substantive testing gap; it's also
  the highest-value one since it exercises the JSON extraction helpers and the
  brainstorm → validate pipeline in one shot.

---

## 2026-05-17 — Hook refactor: PostToolUse → Stop; git init

### Accomplished

- Diagnosed why the mypy PostToolUse hook was silently failing: the command
  ended with `|| true`, so mypy always exited 0 and output was discarded
- Refactored all three hooks (ruff, prettier, mypy) from PostToolUse to Stop, so
  they run once after all edits in a turn have landed
- Extracted each hook into a named script under `~/.claude/hooks/` for
  readability and testability
- mypy hook blocks Claude's stop turn on errors via
  `{"continue": false, "stopReason": ...}`, feeding errors back into context
- Initialized git repo and made initial commit (10 files, `.gitignore` added)
- Verified the mypy hook end-to-end: intentional type error surfaced as a system
  reminder on the next stop

### Decisions

- **Stop over PostToolUse for linters/formatters**: PostToolUse fires per-edit
  and can produce false positives mid-multi-file change. Stop fires once after
  all edits land. Also: the Stop hook naturally blocks the turn on errors
  without needing `additionalContext` JSON plumbing.
- **`{"continue": false, "stopReason": ...}` output from mypy**: this is the
  mechanism that feeds mypy errors back to Claude. Simpler than the
  `additionalContext` approach tried first on PostToolUse.
- **Script files over inline commands**: inline JSON hook commands can't be
  commented, and are difficult to pipe-test. Scripts in `~/.claude/hooks/` are
  readable, self-documenting, and testable with `echo '{}' | ./script.sh`.
- **`mypy --strict .`**: checks the whole directory, not just edited files — the
  Stop hook has no info on what changed, and inter-module issues require a
  full-package check.
- **Explicit PATH for prettier**: hook scripts run with a minimal environment
  that may not include Homebrew's bin directory. Added
  `export PATH="/opt/homebrew/bin:$PATH"` at the top of prettier-format.sh
  rather than hardcoding the full binary path.

### Files Modified

- `/Users/Shared/code/dotfiles/claude/settings.json` — hooks restructured:
  PostToolUse removed, Stop section added with three scripts
- `~/.claude/hooks/mypy-check.sh` — new
- `~/.claude/hooks/ruff-format.sh` — new
- `~/.claude/hooks/prettier-format.sh` — new
- `clue_gen/generator.py` — intentional type error added and reverted
- `.gitignore` — new (excluded `__pycache__/`, `.pyc`, `.venv/`, etc.)

### Next Steps

1. The inter-module mypy gap was demonstrated in theory but not fully tested
   after the hook was fixed — worth a quick test: edit a callee signature to be
   internally consistent but break a caller, confirm mypy catches it
2. Mark the mypy tooling task done in `plan.md`
3. Phase 3: `--candidates N` flag, brainstorm prompt design, validation turn

### Avoid

- **`|| true` at end of hook commands**: silently discards all output; errors
  never surface
- **`additionalContext` JSON from PostToolUse**: more complex than the Stop
  hook's `continue: false` approach; abandoned
- **Inline hook commands in settings.json**: unreadable and untest able; use
  script files instead

### Reflection

- Several round-trips were spent on the wrong layer: debugging why PostToolUse
  output wasn't visible before realising Stop is the right event. Recognizing
  "formatters and linters should run at turn end, not per-edit" earlier would
  have skipped straight to the Stop hook approach.
- The update-config skill was invoked but ended up doing nothing useful — the
  work was manual reads and edits. Skip it for settings.json changes that are
  well-understood.
- The inter-module test was never completed: the hook was fixed, but the session
  pivoted to hook refactoring before confirming the gap. Leave it as a next-step
  rather than claiming it's done.

---

## 2026-05-17 — Phase 3 start: --model flag, smoke-test model, pipeline hardening

### Accomplished

- Researched current Ollama model landscape; replaced `gemma3:4b` smoke-test
  suggestion with `qwen2.5:0.5b` (398 MB, ~205 ms median latency, 30M+ pulls)
- Updated `plan.md`: corrected smoke-test model, added two-layer test strategy
  note to Testing section, added task for optional `options` dict on
  `OllamaClient`/`chat()` for integration test use
- Added `QWEN25_0B5 = 'qwen2.5:0.5b'` to `Model` enum in `client.py`
- Added `--model` CLI flag to `cli.py`; wired through to `OllamaClient`
- Suppressed `httpx` INFO log noise (POST lines) by raising its logger to
  WARNING
- Hardened validation loop: `GenerationError` from malformed validator response
  now warns and skips the candidate rather than fataling; non-string `answer`
  field gets the same treatment
- Added inline comments explaining why each validation failure is a warning
  (signal loss) rather than a hard error (correctness failure)

### Decisions

- **`qwen2.5:0.5b` over `gemma3:4b`**: 6× smaller, ~30× faster in benchmarks;
  same-family models offer no advantage for pipeline smoke tests
- **Two-layer test strategy**: unit tests mock at HTTP/Python level (no Ollama);
  integration smoke tests use real Ollama + `qwen2.5:0.5b` with constrained
  options (`num_ctx=512`, `num_predict=30`, `temperature=0`) — options deferred
  to the Testing phase via a new plan task
- **Validation failure = warn, not fatal**: the validator evaluates clue
  quality; a malformed validator response is the validator's failure, not the
  clue's — fall through to the existing candidate fallback
- **httpx logger silenced at WARNING**: the INFO lines come from outside our
  codebase and add no signal for normal use

### Files Modified

- `plan.md` — smoke-test model corrected; two-layer strategy note; new options
  task
- `clue_gen/client.py` — `QWEN25_0B5` added to `Model` enum
- `clue_gen/cli.py` — `--model` flag; `httpx` logger silenced
- `clue_gen/generator.py` — validation loop hardened; inline docs added

### Next Steps

1. Add `--candidates N` flag (next Phase 3 task)
2. Design brainstorm turns (difficulty encoding, style mix)
3. Design validation turn (structured verdict per clue)
4. Add `options` dict to `OllamaClient`/`chat()` before writing integration
   tests

### Avoid

- **`gemma3:4b` as smoke-test model**: too large/slow; `qwen2.5:0.5b` is the
  right choice
- **Fataling on validator schema violations**: validator output is model output
  at a system boundary — validate it, warn, and degrade gracefully

### Reflection

- The research agent returned dense, well-organized findings; the key insight
  (two-layer strategy) was in the output but required synthesis to apply
  correctly to the plan — worth reading research results carefully before
  deciding what to change
- The smoke-test run surfaced two sequential bugs (`GenerationError` fatal, then
  `AttributeError` on non-string field); running the smoke test after each fix
  rather than batching would have caught them in one shot each
- Session stayed well-focused: research → plan update → code → smoke test →
  docs. No unnecessary detours.

---

## 2026-05-17 — Phase 2 implementation

### Accomplished

- Phase 2 fully implemented: CLI, word parser, multi-turn `OllamaClient`,
  two-stage brainstorm + validation pipeline, JSON output to stdout
- Per-word progress logging added (INFO level) so results stream during a run
- Smoke test input file (`smoke_test.txt`) created with 5 easy + 4 challenging
  words, with commentary explaining why each challenging word is hard
- Style guide updated: named return types rule (frozen dataclass over bare
  tuple), and `~/.claude` symlink warning made more specific

### Decisions

- **Model at construction time**: `OllamaClient(model=...)` — model is a
  property of the client, not each call; cleaner and consistent with how the
  tool is actually used (one model per run)
- **Validation prompt excludes the answer word**: the validator acts as a blind
  solver, generates candidate answers, and evaluates clue quality for each —
  rationale is to prevent the LLM from rationalizing a clue it knows the answer
  to
- **`ClueResult` frozen dataclass**: replaces `dict[str, Any]` — concrete types,
  named fields, easy to extend in Phase 3; serialized via `dataclasses.asdict()`
  in `cli.py`
- **`Message = ChatCompletionMessageParam`**: alias to SDK type rather than a
  custom TypedDict — avoids type divergence and the `type: ignore` it caused
- **`ChatResult` frozen dataclass**: preferred over `NamedTuple` — no positional
  access confusion; NamedTuple acceptable only when tuple unpacking at call
  sites is genuinely useful (added to style guide)
- **`logging` module**: replaces `print(..., file=sys.stderr)`; `_log_fatal()`
  helper consolidates `log.error` + `sys.exit(1)` in one place

### Files modified

- `clue_gen/cli.py` — full rewrite: argparse, logging, split into named helpers
- `clue_gen/client.py` — `ChatResult` dataclass, `Message` alias, model moved to
  constructor
- `clue_gen/generator.py` — new: `ClueResult`, two-stage pipeline, JSON
  extraction helpers
- `clue_gen/prompt.py` — new: `Difficulty` enum, placeholder
  `brainstorm_messages` and `validation_messages`
- `clue_gen/word_parser.py` — new (renamed from `words.py`): `load_words`
- `plan.md` — Phase 2 tasks marked done; Phase 3 updated; Testing section added
- `smoke_test.txt` — new: 9-word smoke test input
- `/Users/Shared/code/dotfiles/claude/CLAUDE.md` — two style guide additions

### Next steps

1. Run `ollama serve` then `clue-gen --words smoke_test.txt` to verify
   end-to-end wiring
2. Pull a small fast model (e.g. `gemma3:4b`) for rapid iteration
3. Add `--model` CLI flag (first Phase 3 task)

### Avoid

- **Custom `Message` TypedDict**: diverges from SDK types and forces
  `type: ignore`; use the SDK alias instead
- **`NamedTuple` for structured returns**: positional access is confusing; use
  `@dataclass(frozen=True)`
- **Sequential `Edit` calls when formatter strips imports**: if adding an import
  and using it in the same file, use a single `Write` — the formatter runs after
  every edit and removes unused imports

### Reflection

- Multiple round-trips fighting the formatter (add import → formatter strips it
  → re-add). A `Write` whenever multiple related changes land in one file would
  have been faster — worth internalizing as a rule.
- The leftover `model=model` bug in `generator.py` (from moving model to the
  constructor) slipped through unnoticed. Running `mypy` after each structural
  change would catch these immediately.
- The symlink miss on `CLAUDE.md` happened again despite the prior session's
  handoff warning. The style guide update naming `~/.claude` explicitly should
  finally close this.

---

## 2026-05-16 — Phase 1 Python skeleton + style guide

### Accomplished

- Created full Phase 1 Python skeleton: `pyproject.toml`,
  `clue_gen/__init__.py`, `clue_gen/client.py`, `clue_gen/cli.py`
- Smoke test passed with `gemma4:26b`; `gemma4:31b` still pulling
- Updated `plan.md`: flat layout (replacing `src/`), progress markers
- Extended `CLAUDE.md` with 6 global style rules + 1 Python rule derived from
  code review feedback this session

### Decisions

- **Flat layout over `src/`**: no benefit for an internal tool never published
  to PyPI; flat is simpler
- **hatchling build backend**: zero config for flat layout; simpler than
  setuptools
- **`OllamaClient` class with instance state**: module-level global can't be
  overridden in tests without reaching into module internals; class constructor
  makes the dependency explicit
- **`Model` as `StrEnum`**: documents the bounded set, enables IDE support,
  catches typos at the call site
- **`gemma4:26b` as default**: fits in RAM more reliably; already pulled and
  smoke-tested
- **Raise `ValueError` on empty model response**: returning `''` would silently
  pass a broken response to the caller
- **`httpx.ConnectError` caught in `cli.py`**: raw exception isn't obvious;
  replaced with an actionable message pointing to `ollama serve`

### Files modified

- `plan.md`
- `pyproject.toml` (new)
- `clue_gen/__init__.py` (new)
- `clue_gen/client.py` (new)
- `clue_gen/cli.py` (new)
- `/Users/Shared/code/dotfiles/claude/CLAUDE.md`

### Next steps

1. Confirm `gemma4:31b` pull completes
2. Phase 2: `--words FILE` and `--difficulty` flags, word list parsing, prompt
   design, JSON output to stdout

### Avoid

- **`src/` layout**: decided against; flat is simpler for an internal tool
- **Module-level `openai.OpenAI` client**: replaced with `OllamaClient` class;
  module globals can't be overridden without reaching into module internals

### Reflection

- Code review discussion was token-heavy but produced lasting value (style guide
  entries) — a reasonable tradeoff for a design session
- Several corrections (class over global, raise over sentinel) were already
  implied by the existing style guide; checking it before writing first-draft
  code would have caught them earlier
- The symlink round-trip on `CLAUDE.md` is now documented in `CLAUDE.md` itself;
  future sessions will resolve the path upfront

---

## 2026-05-16 — Environment setup and model selection

### Accomplished

- Completed all Phase 1 environment setup except Python skeleton (next session)
- Resolved Ollama permissions: removed ACLs, settled on world-readable
  `/Users/Shared/ollama` with owner-only write — simpler and sufficient
- Researched current model landscape (two web research passes); updated
  recommendations from stale training data (Gemma 2, Qwen 2.5) to current
  generation (Gemma 4, Qwen 3)
- Selected `gemma4:31b` (dense) and `gemma4:26b` (MoE) as candidate models for
  clue quality comparison; both currently downloading
- Updated `plan.md` throughout to reflect actual decisions

### Decisions

- **Permissions**: no ACLs on `/Users/Shared/ollama`; `rwxr-xr-x`
  (world-readable) is sufficient — only `ishermandom` can write
- **`OLLAMA_MODELS`**: set only in `ishermandom`'s `~/.zprofile`;
  `claude-sandbox` connects via HTTP and doesn't need it
- **Models**: `gemma4:31b` and `gemma4:26b` — both current-gen Gemma 4; model
  locked in after clue quality comparison. Model name will be a configurable
  parameter (`--model` flag)
- **JSON compliance**: deprioritized in model selection — at 27B+ scale it's a
  solved prompt-engineering problem, not a model differentiator. Focus
  evaluation on clue quality (wordplay, misdirection, difficulty calibration)
- **Package manager**: `pip + venv` over `uv`
- **Two-model JSON pipeline**: rejected — unnecessary complexity; prompt the
  primary model directly

### Files modified

- `plan.md` — updated technology choices, setup commands, and Phase 1 task list
  throughout
- `memory/project_acrostic_clue_gen.md` — updated stack and status

### Next steps

1. Wait for `gemma4:31b` and `gemma4:26b` downloads to complete
2. Create Python skeleton: `pyproject.toml` (`src/` layout, deps declared),
   `src/clue_gen/__init__.py`
3. Create venv and `pip install -e '.[dev]'`
4. Smoke-test: send a minimal prompt to `http://localhost:11434/v1`, confirm a
   response from each model

### Avoid

- **ACLs on `/Users/Shared/ollama`**: unnecessary; settled on world-readable
  unix permissions
- **Older model versions** (Gemma 3, Qwen 2.5): current-gen equivalents exist
  with the same memory footprint — no reason to reach back
- **`brew services start ollama`**: server must only run during active dev
  sessions

### Reflection

- Two separate web research agent calls (general models, then DeepSeek
  specifically) could have been one broader query — batching research questions
  saves a round trip
- The key framing insight — focus model selection on clue quality, not JSON —
  came fairly late; establishing evaluation criteria upfront would have shaped
  the model discussion more efficiently
- Prior handoff entries had stale decisions (gemma2:27b, ACL-based permissions)
  that needed correcting this session; keeping memory current mid-session
  reduces correction overhead later

---

## 2026-05-16 — Ollama installation planning

### Accomplished

- Evaluated local vs. global Ollama installation options relative to the
  two-account sandbox setup
- Settled on Homebrew system-wide install + shared model weights directory
- Updated `plan.md` technology choices and Phase 1 tasks to reflect decisions
- Updated project memory with Ollama setup decisions

### Decisions

- **Homebrew install**: `brew install ollama` run as `ishermandom`; binary lands
  at `/opt/homebrew/bin/ollama`, accessible to all users
- **claude-sandbox PATH**: `/opt/homebrew/bin` must be added explicitly to
  `claude-sandbox`'s `~/.zshrc` — Homebrew shell integration doesn't run
  automatically for non-Homebrew users
- **Shared model weights**: `OLLAMA_MODELS=/Users/Shared/ollama/models` in both
  accounts' shell configs; avoids duplicating the ~16 GB download
- **Permissions**: `chmod +a` ACLs grant `claude-sandbox` read/write on
  `/Users/Shared/ollama/` — do not use `chmod 777`
- **No autolaunch**: `brew services start ollama` is explicitly prohibited;
  server is always started manually with `ollama serve`

### Files modified

- `plan.md` — updated technology choices section and Phase 1 tasks
- `memory/project_acrostic_clue_gen.md` — added Ollama setup decisions

### Next steps

Phase 1 of `plan.md` (updated tasks):

1. `ishermandom`: `brew install ollama`
2. Create `/Users/Shared/ollama/models`; set ACLs for `claude-sandbox`
   read/write
3. Both accounts: add `OLLAMA_MODELS=/Users/Shared/ollama/models` to `~/.zshrc`
4. `claude-sandbox`: add `/opt/homebrew/bin` to PATH in `~/.zshrc`
5. `ollama serve` then `ollama pull gemma2:27b` (~16 GB)
6. Create Python project: `pyproject.toml`, `src/clue_gen/` package
7. Pin deps: `openai`, `ruff`, `mypy`
8. Smoke-test: send a minimal prompt to `http://localhost:11434/v1`

### Avoid

- **`brew services start ollama`**: autolaunch is explicitly unwanted; user will
  start Ollama manually per session
- **`~/bin` user-local install**: considered and superseded by Homebrew; doesn't
  serve the "run from either account" requirement

### Reflection

- The multi-account requirement changed the install recommendation but only
  surfaced mid-discussion. Identifying "which accounts need to run this?" up
  front would have reached the right answer in one pass.
- Session was pure discussion — no code, no file reads beyond plan.md. Token use
  was efficient.
- `OLLAMA_MODELS` shared weights was the highest-value concrete output; without
  it the next session would likely have discovered a 32 GB disk hit the hard
  way.

---

## 2026-05-16 — Account setup doc + prettier hook

### Accomplished

- Conducted interactive threat-model exercise; identified protected, partially
  mitigated, and known-gap threat categories for the two-account setup
- Created `~/.claude/docs/account-setup.md` documenting the sandbox rationale,
  constraints, threat model, and symlink structure for `~/.claude/`
- Added prettier `PostToolUse` hook to global `settings.json` (via dotfiles
  symlink); live-proved it fires and reformats `.md` tables on edit
- Added memory entry pointing to the account-setup doc

### Decisions

- **prettier over mdformat/dprint**: Node dependency already present; largest
  community mindshare; no config file needed (defaults acceptable)
- **Absolute binary path** (`/opt/homebrew/bin/prettier`) in hook: Homebrew
  install, and hook environment may not inherit PATH reliably
- **Hook added inside existing `Write|Edit` entry** rather than a new matcher,
  keeping the hooks array compact
- **No `.prettierrc`**: user confirmed defaults (`proseWrap: always`,
  `printWidth: 80`) are fine

### Files modified

- `/Users/Shared/code/dotfiles/claude/docs/account-setup.md` — created
- `/Users/Shared/code/dotfiles/claude/settings.json` — added prettier hook
- `memory/MEMORY.md` — added account-setup reference entry
- `memory/reference_account_setup.md` — created

### Next steps

Phase 1 of `plan.md` (unchanged from prior session):

1. Install Ollama binary to `~/bin`; add `~/bin` to PATH in `~/.zshrc`
2. `ollama serve &` then `ollama pull gemma2:27b` (~16 GB download)
3. Create Python project: `pyproject.toml`, `src/clue_gen/` package
4. Pin deps: `openai`, `ruff`, `mypy`
5. Smoke-test: send a minimal prompt to `http://localhost:11434/v1`, confirm a
   response

### Avoid

- **Writing to `~/.claude/*` directly**: several entries are symlinks into the
  dotfiles repo. The Edit tool refuses to write through symlinks. Always resolve
  with `readlink` first and edit the real target path under
  `/Users/Shared/code/dotfiles/claude/`.

### Reflection

- Interactive `AskUserQuestion` multiple-choice kept the threat-model exercise
  focused and efficient — good pattern for eliciting structured preferences.
- The symlink issue on `settings.json` cost two extra tool calls (failed edit →
  readlink → re-edit); a `readlink` check upfront on any `~/.claude/` path would
  have avoided it.
- Attempted to create a `.prettierrc` without asking first; user declined
  (defaults are fine). For config files, ask before creating.

---

## 2026-05-16 — Spec and plan

### Accomplished

- Brainstormed and fully defined the spec for an acrostic crossword clue
  generator via interactive Q&A
- Wrote `spec.md` (requirements) and `plan.md` (implementation plan)
- Clarified spec/plan scope boundary; moved implementation details (model
  choice, tooling, setup commands) out of spec and into plan

### Decisions

- **Clue style**: open mix — definitions, wordplay, fill-in-the-blank, light
  cryptic, limited trivia. Primary criterion: enjoyable to solve while remaining
  solvable. No single style dominates.
- **Difficulty**: `--difficulty {Mon..Sat}`, NYT day scale, default `Thu`
- **No source context**: clues generated from answer word alone; quote and
  author are not passed to the model
- **LLM**: `gemma2:27b` via Ollama — chosen for M4 MacBook Air 32 GB (model
  needs ~16 GB; fits comfortably). OpenAI-compatible local API.
- **Interface**: CLI, Python, JSON to stdout, `--words FILE`, `--candidates N`
  (default 1)
- **Open question**: multi-candidate output format for N > 1 (flat strings vs.
  annotated objects) — deferred to implementation

### Files modified

- `spec.md` — created (requirements, quality criteria, I/O format)
- `plan.md` — created (technology choices, setup commands, phased tasks)
- `.claude/handoff.md` — created (this file)

### Next steps

Phase 1 of `plan.md`:

1. Install Ollama binary to `~/bin`; add `~/bin` to PATH in `~/.zshrc`
2. `ollama serve &` then `ollama pull gemma2:27b` (~16 GB download)
3. Create Python project: `pyproject.toml`, `src/clue_gen/` package
4. Pin deps: `openai`, `ruff`, `mypy`
5. Smoke-test: send a minimal prompt to `http://localhost:11434/v1`, confirm a
   response

### Avoid

Nothing tried and abandoned yet.

### Reflection

- Tokens were well-spent: the interactive Q&A via `AskUserQuestion` kept the
  brainstorm focused and avoided long back-and-forth text rounds.
- The spec/plan refactor took two rounds (write → user flags bleed → edit);
  could have been one if the boundary had been defined up front before writing.
- Session stayed lean — no code exploration, no unnecessary reads. Good template
  for a pure design session.
