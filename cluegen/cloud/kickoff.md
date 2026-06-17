# KICKOFF.md — Instructions for Claude Code

> **Status (2026-06-09):** preserved as documentation of the original brainstorm
> — the prompts that were run and the initial plan. The live work queue is now
> `tasks.md`. One STATE & RESUMABILITY bullet was corrected to match the
> implementation (see below); everything else is as written.

Paste Message 1 into Claude Code from the project directory. After reviewing the
smoke test, paste Message 2.

Expected directory layout before you start:

    cluebank/
      CLUE_SPEC.md          # clue-writing spec (provided)
      words.in              # one answer word per line (provided)
      prompts/
        generate.md         # generation prompt template (provided)
        verify.md           # judge prompt template (provided)

---

## MESSAGE 1 — build the pipeline and smoke-test it

Build a batch clue-generation pipeline in this directory. Read CLUE_SPEC.md,
prompts/generate.md, and prompts/verify.md first — they define the data
contract. Do not modify the prompt files or the spec; they are data, and all
prompt text must stay in those files, not in code.

Write `pipeline.py` (plus anything it needs) with this architecture:

ORCHESTRATION

- Run model: a single pipeline run LOOPS over words.in, processing one batch of
  --batch-size words (default 12) per iteration — two LLM calls per batch —
  until words.in is exhausted, --limit total words have been processed this run,
  or a rate limit stops it. --batch-size controls per-call load (quality knob);
  --limit controls per-run budget (cost knob). They are independent.
- Clue mix: --american-per-word (default 2) and --cryptic-per-word (default 2)
  flags. The driver renders these into the {{CLUE_MIX}} template variable as a
  sentence, e.g. "2 American-style (one medium, one hard) and 2 cryptic-style"
  for the defaults; for other counts, split difficulty tags roughly evenly
  between medium and hard.
- For each batch, two SEPARATE fresh-context LLM calls via the `claude` CLI in
  non-interactive mode (`claude -p`), invoked as a subprocess:
  1. GENERATE: prompt = CLUE_SPEC.md + prompts/generate.md with {{WORDS}},
     {{CLUE_MIX}}, and {{CATEGORY_NOTE}} substituted ({{CATEGORY_NOTE}} from
     --category-note-file if given, else empty).
  2. VERIFY: prompt = CLUE_SPEC.md + prompts/verify.md with {{CLUES_JSONL}}
     replaced by the generation output that SURVIVED mechanical checks.
- You (the orchestrator) must never write clues or verdicts yourself —
  everything goes through the subprocess calls, so each batch gets a clean
  context.

MECHANICAL CHECKS (pure code, between the two LLM calls — no tokens)

- JSON parses; required schema fields present; style ∈ {american, cryptic};
  difficulty ∈ {easy, medium, hard}.
- Enumeration matches the answer's word lengths (cryptic clues).
- anagram_fodder, when present, is an exact letter multiset match for the answer
  (case-insensitive, ignoring spaces/punctuation).
- hidden_string, when present, contains the answer as a contiguous substring
  (case-insensitive, ignoring spaces/punctuation) AND appears verbatim in the
  clue text.
- Answer leakage, two tiers: HARD-FAIL: clue text contains the answer word
  itself or a trivial inflection (answer+s/es/ed/ing, answer minus trailing e +
  ing). SOFT-FLAG: clue text contains a stem of the answer (answer with common
  suffixes stripped, only when the stem is ≥4 letters — e.g. "south" inside a
  SOUTHWARD clue). Soft-flagged clues are NOT auto-rejected (short stems produce
  false positives, and some root-sharing is deliberate); they pass to the LLM
  verify step with an annotation naming the matched stem, for the judge's
  leakage criterion to rule on.
- Bank-wide uniqueness: clue text not already in accepted output (normalize
  case/whitespace before comparing).
- Failures here are recorded with machine-generated reasons and skip the LLM
  verify step.

STATE & RESUMABILITY

- Append-only JSONL files in out/: raw_generations.jsonl, mech_failures.jsonl,
  verdicts.jsonl, accepted.jsonl, rejected.jsonl.
- On startup, derive each word's state (completed, awaiting retry, pending
  verification) from all of the JSONL files, and skip completed words.
  Accepted + rejected records alone are not enough to decide completion: a word
  can have some clues accepted while a failed clue still awaits its one retry.
  Re-running after any interruption (rate limit, crash) must resume cleanly with
  no duplicate work.
- Every subprocess call wrapped with a timeout and one automatic retry on
  transport-level failure (non-JSON garbage, empty output, nonzero exit).

RETRY POLICY (quality-level)

- Clues with verdict "revise" or mechanical failure: ONE regeneration attempt,
  in a later batch call, with the failure reason appended to the word's entry in
  the prompt. Second failure → rejected.jsonl. Never loop further.
- Per-style skips from the generator are recorded as final (not retried).

OPERATIONS

- --limit flag to cap words processed this run; --dry-run flag that assembles
  and prints the first batch's prompts without calling the CLI.
- Quota pacing — Claude plan usage is shared across this pipeline and my
  interactive work in the same 5-hour session window, so an unthrottled run can
  lock me out of other work. Two independent controls: --limit N (total words
  this run; a budget cap) and --pace MINUTES (minimum wall-clock interval
  between batch starts; default 0 = unthrottled). Document two presets in --help
  text: "overnight" = no limit, no pace (let it run until rate-limited; resume
  next session); "background" = --pace 15 or --limit 60, leaving session
  headroom for interactive use. Note: words.in is pre-sorted by expected value,
  so capped runs automatically consume the highest-value words first.
- Log one summary line per batch: words in, clues generated, mech-check pass
  rate, accept/revise/reject counts, cumulative totals.
- A `stats` subcommand that reports bank totals by style, difficulty, and
  category of failure.

Then SMOKE TEST: run with --limit 3 --batch-size 3. Show me the assembled
generation prompt (--dry-run first), then the real run's accepted.jsonl contents
and the batch summary. Do not proceed past the smoke test.

---

## MESSAGE 2 — full run (after you've reviewed the smoke test)

The smoke test looks good [adjust here if it didn't]. Run the full word list
with default batch size, in [overnight | background] mode [pick one per run:
overnight = unthrottled before sleep; background = --pace 15 while I'm doing
other work]. If you hit plan rate limits, stop gracefully — resumability will
handle the rest; I'll rerun in the next session. When done (or stopped), give me
the `stats` output and the ten lowest-confidence accepted clues for spot review.

---

## OPTIONAL — batch-size calibration (cheap, recommended)

Before the full run: process the first 60 words as three slices of 20 with
--batch-size 6, 12, and 20 respectively, then compare judge accept rates and
mech-check pass rates across the slices (the `stats` subcommand, filtered by
batch). Pick the largest batch size whose accept rate hasn't degraded. Costs one
extra session at most; converts a guessed quality knob into a measured one.
