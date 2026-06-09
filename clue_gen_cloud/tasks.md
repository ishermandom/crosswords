# Tasks — cloud clue-generation pipeline

Status key: `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` dropped

Each pipeline run consumes shared plan quota, so every run below is followed by
a checkpoint: ask the user for the observed quota impact before starting the
next run.

## Phase 1 — Model pinning

**Goal:** every pipeline run uses Fable 5 unless explicitly overridden.

- [ ] Change the `--model` default in `pipeline.py` from the CLI account default
      to Fable 5 (`claude-fable-5`); keep the flag overridable

---

## Phase 2 — Smoke tests

**Goal:** validate the pipeline end to end on tiny runs and get an early
estimate of quota consumption per word.

- [ ] Clear `out/` before the first run #clean-slate
  - Rationale: it holds only the aborted 3-word run's generation output; leaving
    it would trigger verify-recovery for those words and contaminate the 1-word
    quota estimate.
- [ ] 1-word smoke test: `run --limit 1 --batch-size 1`; user reviews
      `out/accepted.jsonl` and the batch summary. Depends on #clean-slate
- [ ] Ask the user for the observed quota impact of the 1-word run
- [ ] 3-word smoke test: `run --limit 3 --batch-size 3`, only if the 1-word run
      looked good
- [ ] Ask the user for the observed quota impact of the 3-word run

---

## Phase 3 — Batch-size calibration

**Goal:** convert batch size from a guessed quality knob into a measured one:
pick the largest batch size whose judge accept rate has not degraded.

Run the three slices ONE AT A TIME, pausing after each to ask the user for the
observed quota impact before starting the next.

- [ ] Slice 1: `run --limit 20 --batch-size 6`; then quota checkpoint
- [ ] Slice 2: `run --limit 20 --batch-size 12`; then quota checkpoint
- [ ] Slice 3: `run --limit 20 --batch-size 20`; then quota checkpoint
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
