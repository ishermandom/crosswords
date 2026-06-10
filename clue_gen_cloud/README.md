# clue_gen_cloud — batch clue-bank generation via Claude Code

Builds a bank of original crossword clues for automatically generated
acrostic-style puzzles: by default, two American-style and two cryptic-style
clues per answer word, each judged against a shared editorial spec before
acceptance. The aim is a clue bank where a mediocre clue is the costly error — a
smaller good bank beats a larger flawed one.

## How it works

Each batch of words makes two fresh-context LLM calls through the `claude` CLI
in non-interactive mode (`claude -p`), with pure-code checks between them:

1. **Generate** — `CLUE_SPEC.md` + `prompts/generate.md` with the batch's words
   substituted; the model returns one JSONL object per word.
2. **Mechanical checks** (no tokens) — schema, enumeration, anagram letter math,
   hidden-string containment, answer leakage, bank-wide uniqueness. Hard
   failures skip verification; soft flags pass through annotated.
3. **Verify** — `CLUE_SPEC.md` + `prompts/verify.md`: a fresh-context judge
   issues accept/revise/reject verdicts on the surviving clues.

Clues with a "revise" verdict or mechanical failure get exactly one regeneration
attempt in a later batch; a second failure is final. All state lives in
append-only JSONL files under `out/`, so an interrupted run (rate limit, crash)
resumes cleanly — completed words are skipped and interrupted verifications are
re-run verify-only.

The prompt text is data, not code: `CLUE_SPEC.md` and `prompts/` define the full
contract, and `pipeline.py` only assembles and routes them.

## Why `claude -p`

Calls run through the Claude Code CLI rather than the metered API, so they draw
on the Claude plan's session quota instead of per-token billing. That quota is
shared with interactive work in the same session window, which is why runs are
budgeted and paced explicitly (`--limit`, `--pace`) and why each call's token
usage is logged (`[usage]` lines in `out/run.log`) — see the caching/quota
measurement work in [tasks.md](tasks.md).

## Running

```sh
python pipeline.py run --dry-run          # print the first batch's prompts
python pipeline.py run --limit 8 --batch-size 8
python pipeline.py stats                  # bank totals and failure categories
```

Key flags on `run`:

- `--batch-size` — words per batch (per-call load; a quality knob)
- `--limit` — total words this run (a budget cap; independent of batch size)
- `--pace MINUTES` — minimum interval between batch starts, to leave session
  headroom for interactive work (`0` = unthrottled)
- `--american-per-word` / `--cryptic-per-word` — clue mix (default 2 + 2)
- `--model` — pinned to Fable 5 (`claude-fable-5`) by default; overridable
- `--category-note-file` — optional guidance injected into the generation prompt
  for themed word lists

Presets: **overnight** = no limit, no pace (run until the plan rate limit stops
it; re-run next session to resume); **background** = `--pace 15`, leaving
headroom for interactive use. `words.in` is pre-sorted by expected value, so
capped runs consume the highest-value words first.

## Files

- `CLUE_SPEC.md` — the clue-writing spec both prompts share
- `prompts/generate.md`, `prompts/verify.md` — prompt templates
- `words.in` — one answer word per line, highest value first
- `out/` — append-only JSONL state plus `run.log`; `accepted.jsonl` is the
  product
- `kickoff.md` — the original brainstorm, preserved as documentation

## Status

Work queue, per-phase status, and run-by-run quota notes live in
[tasks.md](tasks.md).
