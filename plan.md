# Acrostic Clue Generator — Implementation Plan

_Scope: how the tool is built — technology choices, project structure, and
phased tasks. Read `spec.md` first for goals, requirements, and open questions._

Status key: `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` dropped

---

## Technology choices

- **LLM**: `gemma4:31b` (dense) and `gemma4:26b` (MoE) via Ollama (locally
  hosted; OpenAI-compatible API at `http://localhost:11434/v1`); model will be
  selected after evaluating clue quality from both
- **LLM client**: `openai` Python package pointed at the local endpoint; no API
  key required
- **Language**: Python with flat layout (`clue_gen/` at project root)
- **Linting / types**: `ruff`, `mypy`

### Ollama installation

Installed system-wide via Homebrew (`brew install ollama` run as `ishermandom`).
Binary lands at `/opt/homebrew/bin/ollama`.

Model weights are shared between accounts at `/Users/Shared/ollama/models`, set
via `OLLAMA_MODELS=/Users/Shared/ollama/models` in each account's shell config.
This avoids duplicating the ~16 GB model download.

**The Ollama server must always be started manually** (`ollama serve`). Never
use `brew services start ollama` or any other autolaunch mechanism — the server
should only run during active development sessions.

### One-time environment setup

```bash
# Run as ishermandom (requires admin)
brew install ollama

# Create shared model directory; leave world-readable (no ACLs needed —
# /Users/Shared/ is a shared space and these are the only two accounts)
mkdir -p /Users/Shared/ollama/models

# In ishermandom's ~/.zprofile (claude-sandbox connects via HTTP, not CLI):
export OLLAMA_MODELS=/Users/Shared/ollama/models

# In claude-sandbox's ~/.zprofile (not set up automatically for non-Homebrew
# users; needed to reach the ollama binary):
export PATH="/opt/homebrew/bin:$PATH"

# Start the server, then pull both candidate models (~38 GB total)
ollama serve &
ollama pull gemma4:31b && ollama pull gemma4:26b
```

---

## Phase 1 — Environment and project skeleton ✓

**Goal**: Runnable project structure with dependencies pinned; Ollama reachable
from Python.

- [x] `ishermandom`: `brew install ollama`
- [x] Create `/Users/Shared/ollama/models`; world-readable, no ACLs needed
- [x] `ishermandom`: add `OLLAMA_MODELS=/Users/Shared/ollama/models` to
      `~/.zprofile`
- [x] `claude-sandbox`: `/opt/homebrew/bin` already in PATH
- [x] Start Ollama server manually (`ollama serve`) and pull both candidate
      models (`gemma4:31b` and `gemma4:26b`) sequentially (~38 GB total)
- [x] Create Python project: `pyproject.toml` with flat layout and a `clue_gen`
      package
- [x] Pin dependencies: `openai`, `ruff`, `mypy`
- [x] Smoke-test Ollama connection: send a minimal prompt, confirm a response
      comes back

## Phase 2 — Core clue generation ✓

**Goal**: End-to-end working tool that reads a word list and emits JSON clues.

### Prompt sequence architecture

Each clue word is processed by a **two-stage pipeline**:

1. **Brainstorm conversation** — a multi-turn dialogue in a single shared
   context. The model is asked to think through angles, associations, and
   candidate clue styles before committing. Implemented as a `messages` list
   that grows with each assistant reply and follow-up user turn.

2. **Validation call** — two independent API calls with fresh contexts (see
   `validation.md` for the full design). A blind solvability call checks whether
   the answer is guessable from the clue alone; a separate answer-aware quality
   call evaluates convention compliance and scores the clue on rubric scales
   calibrated to the target NYT day.

The specific turns (what each message says) are deferred to Phase 3 prompt
tuning. Phase 2 builds the infrastructure: `OllamaClient.chat()` accepts and
returns a full `messages` list; the per-word generation function orchestrates
the two stages with placeholder prompts.

**Output shape** (resolved): `clues` is always a flat list of strings — one
entry when `--candidates 1`, N entries when `--candidates N`.

### Tasks

- [x] Implement CLI entry point with `--words FILE` and `--difficulty` flags
- [x] Parse the word list file (one word/phrase per line, strip blanks and
      comments)
- [x] Extend `OllamaClient` with a `chat(messages)` method that accepts and
      returns a full messages list (enabling multi-turn conversations)
- [x] Implement per-word generation: brainstorm conversation followed by
      independent validation call; placeholder prompts for now
- [x] Parse validation response as JSON; assemble and write final JSON array to
      stdout
- [x] Basic error handling: missing file, Ollama not reachable, malformed JSON
      response

## Phase 3 — Candidates, prompt design, and refinement

**Goal**: `--candidates N` support and prompt quality tuning based on real
output.

- [x] Add `--model` flag so the caller can select the Ollama model at runtime;
      pull `qwen2.5:0.5b` (398 MB) for rapid smoke testing where output quality
      doesn't matter — it's ~30× faster than the prod models
- [x] Research and write a guide: effective prompt engineering for locally
      running LLMs (instruction following, JSON output, context limits,
      differences from hosted models, etc.)
- [ ] Benchmark inference speed: measure end-to-end latency per word and
      tokens/sec for each candidate model; compare against Ollama's expected
      throughput for that model size on this hardware. If actual performance
      falls short, investigate and address the gap — likely causes include
      context size inflating KV-cache memory, the model falling back from GPU to
      CPU, or sampler settings. Goal: know whether the tool is fast enough for
      interactive use before investing in prompt tuning.
- [ ] Decide whether brainstorm and validation calls need separate
      `ModelOptions` (brainstorm: temperature ~0.7; validation: temperature
      ~0.1–0.2); if so, expose per-call overrides on `OllamaClient.chat()`
- [ ] Consider using different models for generation vs. evaluation: the two
      calls have different strengths requirements (creative generation vs.
      structured scoring). One candidate split to try: qwen for brainstorm,
      gemma4 for validation.
  - Note: qwen3.5 family does not support structured output (response_format /
    schema enforcement) when thinking is disabled (`think=false` /
    `reasoning_effort='none'`). The grammar mask is never applied because Ollama
    defers it until the end-of-thinking token, which never arrives. gemma4
    enforces schemas correctly. Tracked upstream:
    https://github.com/ollama/ollama/issues/14645
- [x] Design validation prompt: two-call architecture documented in
      `validation.md`; implement prompts to match that spec
- [ ] Design brainstorm turns: encode difficulty (NYT day description), style
      mix (definitions, wordplay, fill-in-the-blank, light cryptic, trivia)
- [ ] Add `--candidates N` flag (default 1)
- [ ] Handle validation rejection: decide retry behaviour and implement
- [ ] Evaluate clue quality across difficulty levels; iterate on prompt
      engineering
- [ ] Any additional flags or output options that surface during Phase 2 testing

## Tooling ✓

- [x] Add a `mypy` Stop hook to global `settings.json` so type errors surface at
      the end of every turn; ruff and prettier moved to Stop as well

## Testing ✓

**Goal**: Confidence that parsing, prompt construction, and pipeline logic are
correct independently of the model.

Two-layer strategy: unit tests mock at the HTTP or Python level (no Ollama
needed); integration smoke tests use real Ollama + `qwen2.5:0.5b` with
constrained generation (`num_ctx=512`, `num_predict=30`, `temperature=0`).

- [x] Unit tests for `word_parser.load_words`: blank lines, full-line comments,
      inline comments, uppercasing
- [x] Unit tests for `prompt`: correct difficulty descriptions, answer length
      encoding in validation prompt, word absent from validation prompt
- [x] Unit tests for `generate_clue` via a fake `OllamaClient`: verify the
      brainstorm → extract → validate call sequence and that `ClueResult` is
      assembled correctly; JSON extraction helpers (`_strip_fences`,
      `_extract_json_list`, `_extract_json_object`) are exercised here via the
      public API rather than tested directly
- [x] Pre-implementation design decisions required before writing validator unit
      tests (TODOs already stubbed in `test_solvability.py`, `test_quality.py`,
      `test_validator.py`, `test_cli.py`):
  - [x] Public API surface: two clients, `max_answer_rank` parameter with
        default; stubs in `solvability.py`, `quality.py`, `validator.py`
  - [x] Return type data model: `bool` (rank logged for debug; not exposed to
        callers)
  - [x] Day profile ranges: `DAY_PROFILES` and `QUALITY_FLOOR` in `quality.py`
  - [x] CLI subcommand shape: argparse subparsers (`run`, `generate`,
        `solvability`, `quality`) in `cli.py`
- [x] CLI solvability tests written (xfail); awaiting `validate_solvability`
      implementation to pass
- [-] Add an optional `options` dict parameter to `OllamaClient` (or `chat()`),
  passed as `extra_body` to the completions call; integration tests would use
  this to set `num_ctx=512`, `num_predict=30`, `temperature=0`. Dropped: the
  manual smoke test covers the same ground; an automated integration test
  requires Ollama to be running and can't run in CI. Note on the parameters:
  `num_predict` caps output tokens (the main speed lever, but 30 is too short
  for real clues); `num_ctx=512` shrinks the KV cache slightly; `temperature=0`
  gives determinism with no speed effect. Revisit if deterministic smoke runs
  become worth the plumbing.

## Cleanup

Once Phase 3 is complete and the tool is stable, consolidate all clue generator
artifacts under `clue_gen/`:

- [ ] Move `spec.md` → `clue_gen/spec.md`
- [ ] Move `plan.md` → `clue_gen/plan.md`
