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
- [ ] Investigate whether the script can take advantage of prompt caching —
      the per-call prompts share large static prefixes (templates, spec), so
      cache hits might significantly cut quota consumption
