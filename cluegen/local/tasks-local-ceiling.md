# Local ceiling tasks

Status key: `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` dropped ·
`[?]` uncertain/speculative

---

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
- [ ] **Expand the eval set to ~100 examples** #eval-expansion — user priority
      (2026-07-04): the window's judge tuning steers by ~15 contested rows;
      lower-hanging fruit should surface at scale. One-off Fable generation of
      graded, labeled examples (verdict + basis + one-line reason), anchored in
      the window's discovered failure taxonomy: definite-description vignettes
      (SNOOZE family), ?-license earned vs apology, flavor words vs padding (ZED
      vs THIRTEEN), count-metonymy fairness (NINE vs TEN), non-pinning-is- fine
      rows, flat gloss vs prize-fact gradient, foreign/idiom sense. Pair
      structure (accept + near-miss revise per word) as in funcal; exclude all
      words in words.in, the eval sets, and the bank. Keep every existing
      real-world set unchanged; add as new battery set(s) with a
      generated-tune/generated-holdout split. Run as two detached Fable calls
      (~45 rows each) with watchers — the 10-min Bash cap killed a big single
      call once already.
- [x] **26B substitution turn: prompt-engineer the referent/register split**
      #judge-26b-referent — RESOLVED 2026-07-06, outcome: the referent flaw is
      fully fixed but the tier is still not viable. Under the adopted v2e
      protocol (which redesigned exactly what this task proposed), the 26B holds
      37/42 accepts (was 7/43) — the user's promptability bet was right — but
      the same protocol swings it lenient: 32/50 kills (banks a third of
      revise/rejects). High-recall/low-precision has no slot in the current
      judge path, so not promising for now — but parked, not closed (user
      2026-07-06): only one protocol variant has been tried on the 26B, and its
      speed (~5 s/call vs ~32 s) keeps the prize large. Follow-up:
      #judge-26b-backburner. Data: `mt26_screenoff_*` logs; ledger 26B sections.
- [ ] **26B judge tier, second look** #judge-26b-backburner — backburner, no
      urgency. The v2e protocol cured the referent flaw but left the 26B lenient
      (32/50 kills). Unexplored: strictness-targeted prompt iteration for the
      26B (the 31B got seven rungs; the 26B got zero), a recall-side pre-filter
      role, or a 26B-screens/31B-confirms cascade under the single-flow
      protocol. Revisit when judge-path cost matters or the current stack
      stabilizes.
- [~] **Setter-side tuning** #setter-tuning — the front after idea 13 (user
  pivot 2026-07-06). DESIGN SETTLED 2026-07-06: `setter.md` governs (goal,
  autonomous-operation rules, ten standing principles, hypotheses H1a/H1b/
  H2/H3/H4) — written through two user design rounds; don't re-derive its
  decisions. Satisfaction replaced difficulty as the target (difficulty was a
  proxy; the modifier-dial idea from calibration #9 survives inside principle 4
  and H-ladder work). H1 LADDER RUN 2026-07-06 (ledger "H1a sanity check" + "H1
  rungs 1–2" sections): H1a as written failed (taxonomy seeding relabels,
  doesn't generate); winning shape is the three-turn funnel — vivid material →
  select → re-cast (`scratch/h1a_probe.py`, arms basis/mechanism/material/
  vivid/cast/develop/diverse/senses). 31B liveliness audit of top-2 finals, 13
  words: 10/13 words ≥1 unflagged; head-to-head on bank-shared words 5/7 vs old
  funnel's 2/7. H3 validated early (re-cast turn fixes adverbs via simile
  shapes); width fixed by sense-inventory-first (FRANK frankfurter + franking
  surfaced). CONVERSION residual fixed same day: conventions block in the draft
  turn fixes number-word conversion on 26B; 31B revalidation transfers the
  prompts unchanged and solves FRANK by width ("Ancestor of the French"). Parked
  gap: neither model uses the shortening convention ("briefly") even when
  modeled. Tonight's stack: `senses` material → `conventions` pick → re-cast
  (ledger "Conversion rung"). Adoption ladder rungs 1–2 DONE 2026-07-06 (ledger
  "Rungs 1–2 results"): substitution audit 4/26 flagged (caught CHASE
  embedded-object clues the layer-3 grade missed); full protocol on the 13
  dual-pass survivors: 10 bankable / 3 fixable (economy-only trims) / 0 bad —
  8/9 words directly bankable, adverbs and fresh senses included. H4/send-cap
  analysis + rung 3 chunk 1 DONE same night (ledger "Rung 3 chunk 1"): 8 fresh
  words → 5/16 finals survived audits, 4 bankable + 1 fixable at full protocol;
  word-level 5/8 usable vs 9/13 on tuning words. Taste round 1 GRADED 2026-07-07
  (ledger "Taste round 1 results", `scratch/taste_round_1_results.jsonl`): the
  judge's flatness kills are vindicated; Claude was the lenient grader. Judge's
  real leaks are substance — accuracy (banked an inaccurate MELODY clue) and
  obscurity (banked the NIL name-image-likeness sense the user doesn't know).
  User calibrations now in setter.md principle 2. Repair loop VALIDATED for
  economy flaws only (5/9 converted across two rounds; production repair
  declines non-economy flaws — filter now in `repair_probe.py`).
  OVERNIGHT+MORNING 2026-07-07 (user directive: ranking + breadth; ledger
  "Overnight results" through "Repair round 2 + H4"): calibrated stack FROZEN
  after the A/B tied at 5/16; 51 words × K=2-3 samples → 25/51 words (49%) hold
  a full-protocol-bankable clue; capture list `scratch/h1_capture.jsonl` = 40
  bankables with provenance (NOT merged into clue_bank.jsonl). ADOPTED:
  fresh-context 26B ranker (84% of oracle at top-2, doubles unranked baseline;
  31B ranker never uniquely better). SUPPORTED: H4 early stop at M=1 (~27%
  judge-time saving, ~zero coverage cost, breadth mode). Kinship diagnosis:
  monosemy defeats sense-width → `frames` arm (per-item frame discipline, try 2)
  widens material (UNCLE: Sam/Ben/Fester/McDuck; TWIN: digital twin) — but AUDIT
  VERDICT (ledger "Frames-arm audit verdict"): 10/12 flagged, zero coverage
  gain; frame-REFERENCE clue shapes rate flat. Kinship PARKED — binding
  constraint is conversion shape (frames → clues with a leap); revisit on any
  judge design round or draft-turn leap-shaping work. Queue: repair prompt
  strict-'?' rule DONE (in `repair_probe.py`); assemble the judge design-round
  brief; the 20 uncovered words (fork — deeper sampling K>3 vs material levers
  vs accepting them as the current ceiling: UNDECIDED); H1b at equal compute;
  production wiring deferred to first consumer. Open question: judge
  design-round timing is the user's call — brief items: accuracy leak (MELODY
  staircase banked), obscurity calibration (NIL sense banked), number-agreement
  leniency (plural VIOLET passed), name-word convention ("Sinatra's first name"
  → other_object), '?'-licensed stretches killed at substitution (UNCLE "Taps
  out?" aha), missing "for short" signal not required (repaired NIL banked
  without it); the liveliness turn STANDS as calibrated. Note: `rank_pool.py`
  hardcodes its pool path (h1_pool.jsonl) — the frames run needed a swap dance;
  add a path argument next time it's touched. The user launches stretches with a
  /goal prompt that points at setter.md/ceiling.md/ledger/tasks.md. Note: bank
  audit DONE 2026-07-06 (flag-and-report, nothing deleted): 23/75 rows flagged,
  22 flat-gloss + 1 unearned '?', zero substitution/truth/economy-unanimous
  flags in the 10-row full-protocol probe. Read: about a third of what the old
  pipeline banked is flat-but-correct — the shortage is charm at generation, not
  judge strictness. Some flags are judge taste, not defects (MELODY "Whistleable
  earworm", SELDOM "Once in a blue moon", ZED "That last character, overseas",
  COURT double definition). Full list: `scratch/logs/bank_liveliness_audit.log`;
  ledger "Bank audit" section.
- [ ] **Align local vs cloud judge requirements** #judge-alignment — both judges
      should enforce the same requirement set, each via methodology fitting the
      model's strength (user direction 2026-07-04). DEPRIORITIZED behind
      #setter-tuning (user pivot 2026-07-06). Audit findings (window session,
      2026-07-04): (a) answer/root/cognate leakage — cloud has mechanical
      `has_answer_leak` + stem soft-flags + a judge check with the etymology
      exception; local has only setter self-check. The mechanical half is pure
      code to copy local-side (copy, not import — prototyping independence); the
      judgment half needs a home in the cascade. (b) The local setter emits a
      required `trap` field no local judge reads — verify it (cloud check #7:
      trap proportionate to difficulty) or stop emitting it — note this
      dovetails with #setter-tuning's difficulty thread. (c) Non-pinning
      prosecution is a local-only invention absent from CLUE_SPEC — removal
      COMPLETE for the confirm side (ideas 10/12: judges test truth, not
      uniqueness); the screen retires with idea 13. (d) Cross-clue independence:
      intentionally out of local scope — see #angle-distinct.
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
