# Tasks — cloud clue-generation pipeline

Status key: `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` dropped

Each pipeline run consumes shared plan quota, so every run below is followed by
a checkpoint: ask the user for the observed quota impact before starting the
next run.

## Phase 1 — Model pinning ✓

**Goal:** every pipeline run uses Fable 5 unless explicitly overridden.

- [x] Change the `--model` default in `pipeline.py` from the CLI account default
      to Fable 5 (`claude-fable-5`); keep the flag overridable

---

## Phase 2 — Smoke tests ✓

**Goal:** validate the pipeline end to end on tiny runs and get an early
estimate of quota consumption per word.

- [x] Clear `out/` before the first run #clean-slate
  - Rationale: it holds only the aborted 3-word run's generation output; leaving
    it would trigger verify-recovery for those words and contaminate the 1-word
    quota estimate.
- [x] 1-word smoke test: `run --limit 1 --batch-size 1`; user reviews
      `out/accepted.jsonl` and the batch summary. Depends on #clean-slate
- [x] Ask the user for the observed quota impact of the 1-word run
  - Note: 11% of session quota total, but the measurement also covers the Phase
    1 edits and `out/` cleanup — not a clean per-run number. Future measured
    runs get their own turn, separate from file edits.
- [x] 3-word smoke test: `run --limit 3 --batch-size 3`, only if the 1-word run
      looked good
  - Note: 11/12 clues accepted, 1 revise (NIL hidden-word fodder padding); no
    mech failures, no retries.
- [x] Ask the user for the observed quota impact of the 3-word run
  - Note: cumulative 24% after the run (25% including Claude's bookkeeping), so
    the run itself cost ~13% — roughly 4.5% of quota per word.

---

## Phase 3 — Batch-size calibration

**Goal:** convert batch size from a guessed quality knob into a measured one:
pick the largest batch size whose judge accept rate has not degraded.

Run the three slices ONE AT A TIME, pausing after each to ask the user for the
observed quota impact before starting the next. Keep `--limit` equal to
`--batch-size` (user decision 2026-06-09: quota is likely to run out before the
experiment concludes, so the original 20-word slices were cut down).

- [x] Slice 1: `run --limit 6 --batch-size 6`; then quota checkpoint
  - Note: 24 clues generated, 22 passed mech, 21 accepted, 1 revise (FOUR's FORE
    homophone flagged as a chestnut duplicating the golf domain of another FOUR
    clue). Cumulative quota 52% after the run, so the slice cost ~27% —
    consistent with ~4.5% per word.
- [x] Slice 2: `run --limit 8 --batch-size 8`; then quota checkpoint
  - Rationale: originally 12 words, but at ~4.5%/word that projects to ~54%
    against ~48% remaining; user chose a smaller slice that fits the window over
    waiting for a quota reset.
  - Note: 32 clues, 32/32 mech pass, 28 accepted, 4 revise (accept rate 87.5% vs
    slice 1's 95.5% — possible quality dip at batch 8, or noise; the revises
    were all editorial-angle catches, not unsound clues).
  - Note: quota 57% → 84%, so ~27% for 8 words ≈ 3.4%/word — a real per-word
    efficiency gain over batch 6's ~4.5%/word.
- [ ] Slice 3: `run --limit 12 --batch-size 12`; then quota checkpoint
  - Note: needs a fresh quota window (~41% projected at 3.4%/word; 16% remained
    after slice 2). 12 was the originally planned batch size.
- [ ] Slice 4: `run --limit 20 --batch-size 20`, ONLY IF slice 3 shows per-word
      quota cost still falling with batch size; if cost per word is roughly
      constant per run, skip this and prefer smaller batches
- [ ] Compare accept and mech-pass rates across slices (`stats` prints a
      by-batch-size table) and pick the batch size for the full run
  - Note: words retried during a later slice are attributed to that slice's
    batch size, so the comparison is approximate; fine for this purpose.

---

## Phase 3b — Caching instrumentation and measurement

**Goal:** make per-call token usage visible (input/output/cache split) and
measure it on the cheapest sufficient run, to decide whether a prompt-caching
redesign can meaningfully cut quota consumption.

### Background

Theoretical assessment (2026-06-10): `claude -p` applies prompt caching
automatically with no user control over breakpoints; the CLI's own system
prompt + tools are byte-identical across back-to-back calls and likely already
cache-hit; CLUE_SPEC sits inside the user message with variables interleaved, so
it likely never caches — only a multi-turn session design (`--resume`) could
cache it. Two unknowns gate any redesign: the input/output split of the fixed
per-batch cost (output is uncacheable), and whether plan quota discounts cache
reads the way dollar billing does (~0.1×). Measure before building.

- [x] Add per-call usage capture to the CLI wrapper: `--output-format json`,
      parse the envelope, log usage (input, output, cache read, cache write) per
      call and per run #usage-instrumentation
  - Note: `[usage]` lines per call plus a run-total line, in stdout and
    out/run.log; also captures `session_id` and `total_cost_usd` (the latter
    directly encodes the cache discount, useful for the quota comparison).
- [x] 1-word instrumented run (`run --limit 1 --batch-size 1`); then quota
      checkpoint. Depends on #usage-instrumentation
  - Rationale: one word is the pessimal input-to-output ratio, so it is the most
    instructive case for caching questions — and the cheapest (~4.5% quota vs
    ~41% for the 12-word slice).
  - Note: batch 5, one retry word, 4/4 clues accepted. Usage — generate:
    input=2069 output=4782 cache_read=15818 cache_write=13776 ($0.452); verify:
    input=2069 output=2351 cache_read=15818 cache_write=14991 ($0.346); run
    total $0.798.
  - Note: quota 60% → 71%, so ~11% including Claude's report turn — high vs the
    ~3.4%/word at batch 8, confirming batching remains the dominant quota lever
    (fixed per-call cost).
  - Note: findings — the CLI's static prefix (15.8K tokens) cache-hits on both
    calls already; dollar cost splits ~45% output / ~45% cache writes (the ~14K
    CLUE_SPEC+template suffix is written at 1.25× every call and never re-read);
    a session-resume design would turn those writes into 0.1× reads, cutting
    ~40% of dollar cost. Cost math matches 5-minute-TTL pricing (write 1.25×),
    so `claude -p` is on the short TTL — relevant to any --pace design.
- [x] Decide the next caching step from the numbers: session-resume (multi-turn)
      redesign, a larger comparison run, or drop the idea
  - Note: key signals — does the batch's second call show cache reads > 0 (CLI
    system prefix already caching); what share of cost is output (uncacheable);
    does the quota delta look discounted relative to usage-derived cost.
  - Note: decision (2026-06-10) — probe → trim → session-resume. Probe the
    preamble composition with cheap haiku micro-calls; implement whichever trims
    verify (scratch cwd, skills/tools/CLAUDE.md exclusions); then build
    session-resume against the post-trim numbers. Caveat: the 5-minute cache TTL
    vs long generate-call durations means session-resume favors small-to-medium
    batches.
  - Note: user correction — the slice quota figures (e.g. 3.4%/word at batch 8)
    already included prefix caching, so batching, trimming, and session-resume
    are overlapping attacks on the same fixed per-call cost, not additive
    levers.
- [x] Preamble probe matrix: haiku micro-calls
      (`claude -p --model claude-haiku-4-5`) comparing prompt composition across
      cwd / env / flag variants; record usage per variant #preamble-probes
  - Note: total prompt tokens (input + cache write + cache read) per variant,
    prompt "Reply with exactly: OK" — project-default 28,277 · scratch-cwd
    27,408 · + `--disable-slash-commands` 25,376 · + `--system-prompt <short>`
    19,304 · + `--disallowedTools "*"` **3,592**. Tool definitions ≈ 15.7K,
    default system prompt ≈ 6K, skills listing ≈ 2K, project context ≈ 0.9K.
  - Note: `--bare` is ruled out — it never reads OAuth (API key only), so it
    would bill the metered API instead of the plan; the targeted flags above
    keep OAuth/plan billing.
  - Note: implication — moving the static content (CLUE_SPEC + fixed task
    instructions) into `--system-prompt` makes the prefix byte-identical across
    fresh calls, so it should cache-read across invocations (as the default
    system prompt does today), likely making session-resume unnecessary.
    Preamble cut ≈ 87%; projected 1-word run cost ~$0.80 → ~$0.45-0.50 (output
    untouched).
- [~] Implement the verified trims: scratch cwd, `--disable-slash-commands`,
  `--disallowedTools "*"`, and `--system-prompt-file CLUE_SPEC.md`; task
  instructions + variables stay in the user turn. Then a 1-word measured run to
  confirm cost and quality. Depends on #preamble-probes
  - Note: design — the system prompt carries ONLY the spec, shared verbatim by
    both call types so its cache entry is touched on every call (most TTL-robust
    shape). Personas differ by task and stay in the user-turn templates: setter
    in generate.md, editor in verify.md (user decision 2026-06-10); the spec's
    opening is reworded persona-neutral. Carrying the ~700-token task
    instructions uncached costs ~$0.007/call — accepted.
- [x] Haiku caching validation (quota at 96%, too high for a Fable run): two
      back-to-back direct `claude -p` GENERATE calls, one word each, with the
      trimmed flags and `--system-prompt-file CLUE_SPEC.md` — invoked directly,
      NOT via pipeline.py, so nothing touches the out/ clue bank. Goal: confirm
      call 2 cache-reads the system-prompt prefix; quota not measured (haiku is
      not the production model). #haiku-cache-check
  - Note: interpretation caveat — haiku's minimum cacheable prefix is 4096
    tokens vs Fable's 2048; if the spec-side prefix lands under 4096, haiku
    shows write=0/read=0 where Fable would cache. Check call 1's cache_write
    before concluding anything from call 2's cache_read.
  - Note: results (2026-06-10, rerun after the quota cutoff) — the two GENERATE
    calls both showed read=0/write=6783, but follow-up micro-probes pinned the
    cause on the caveat above, not on the design. Identical back-to-back prompts
    fully cache-hit (write 6464 → read 6464, cost $0.0088 → $0.0015), proving
    the prefix is byte-identical across fresh invocations. Differing user turns
    read 0 with the real spec, but with a 2×-spec padded system prompt read
    5795/wrote 3558 — so the CLI does place a cache breakpoint at the
    system-prompt boundary, and the spec-side prefix (~2.9K tokens) is simply
    under haiku's 4096 minimum.
  - Note: implication — on Fable (2048 minimum) the ~2.9K spec prefix should
    cache-read across fresh calls; confirm via cache_read ≈ 2.9K on call 2 of
    the post-trim 1-word measured run. Haiku clue text went to /tmp only; the
    out/ clue bank was not touched.
- [ ] Session-resume (multi-turn) design: likely moot if the system-prompt
      prefix cache-reads across fresh calls (verify on the post-trim measured
      run — cache_read ≈ prefix size on call 2); keep only if the post-trim
      numbers still show meaningful never-read writes
  - Note: if implemented, session-resume would additionally cache the per-turn
    task instructions (~700 tokens/call ≈ $0.007/call) — currently estimated not
    to be worth the architecture, pending post-trim data.

---

## Phase 3c — Project README ✓

**Goal:** give the project a front door — goals, pipeline overview, and how to
run it — so a fresh reader (or session) doesn't need to reverse-engineer
kickoff.md and the code.

- [x] Write README.md: goals and approach (drawing on kickoff.md), the generate
      → mech-check → verify flow, why it runs on `claude -p` (plan quota vs API
      billing), CLI usage and key flags
  - Note: status tracking stays in tasks.md as the single source of truth; the
    README links to it rather than duplicating per-phase status.

---

## Phase 4 — Full run

**Goal:** process the rest of words.in (the kickoff document's somewhat misnamed
"message 2").

- [ ] Full run with the calibrated batch size, in the mode the user picks:
      overnight (no limit, no pace) or background (`--pace 15`)
- [ ] On completion or rate-limit stop: report `stats` output and the ten
      lowest-confidence accepted clues for spot review

---

## Backlog

- [ ] Retried words regenerate a full clue set even when most clues are already
      accepted (dedup discards the duplicates, but the generation quota is
      spent); consider asking only for replacements for the revised clues
- [~] Investigate whether the script can take advantage of prompt caching — the
  per-call prompts share large static prefixes (templates, spec), so cache hits
  might significantly cut quota consumption
  - Note: in progress as Phase 3b — instrumentation first, then a 1-word
    measured run, then a decision on any redesign.
