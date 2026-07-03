# Ceiling campaign log

Milestone reports for the local-ceiling campaign (spec: `ceiling.md`).
Chronological; newest entry last. Each entry: what changed, measurements,
interpretation, next step.

---

## 2026-07-01 — Setup and first probe

**What changed:** Campaign infrastructure is up. Worktree
`/Users/Shared/code/crosswords-local-ceiling` on branch `local-ceiling`; Ollama
server now runs under Claude's control (`~/tmp/ollama serve`, user authorization
2026-07-01, no pulls). First probe committed:
`cluegen/scratch/probe_ceiling_american.py` — a 3-turn scaffold (angle
brainstorm → drafts → self-edit + schema extract) with a `--single` unscaffolded
baseline mode, system prompt condensed from CLUE_SPEC Part A.

**Smoke findings:** plumbing works end to end (HTTP, logging, schema
pass-through, timing). `qwen3.5:2b` in single mode emitted 7,520 tokens of
thinking and no content under the JSON schema — consistent with the known
qwen3.5 thinking+format issue (`plan.md`, ollama#14645). Smoke role only; gemma4
enforces schemas correctly.

**Word sets** (user direction: sample across `words.in` categories, not just the
banked numbers):

- **Iteration set** (prompt tuning): DUCK, DRAFT, MARK, IRIS, TWELVE, TEE — one
  per major category (polysemous ×2, name-word, flower, number, letter).
- **Held-out eval set** (checkpoints only, never used for tuning): COURT, SUE,
  HAZEL, SECOND, ZED, FORTY, DOZEN, NINETEEN — the last three are cloud-banked,
  enabling same-word comparison against Fable clues.

Keeping the sets disjoint prevents tuning the prompts to the eval words.

**Next:** first quality reads on `gemma4:26b-qat` over the iteration set; then a
`gemma4:31b-qat` pass and the baseline cloud-verify checkpoint.

---

## 2026-07-01 — First 26B run (DUCK) and window fix

**What changed:** v1 scaffold initially produced no drafts — the drafting turn,
with thinking on, exhausted the 8k context window in reasoning before emitting
content, and the extract turn then invented a clue with nothing to select from.
Fixes: `num_ctx` 8192 → 16384 in the shared harness; drafting turn runs
`think=False`. Post-fix timing: angle turn ~260 s (~5k thinking tokens), drafts
8 s, extract 3 s — turn 1 is ~95% of wall time.

**Measurements (DUCK, hard, gemma4:26b-qat):** 4 drafts across genuinely
distinct senses — "Avoid a low blow?" (selected), "Zero at the crease?" (cricket
duck), "A heavy-duty canvas?" (duck cloth), "Make a quick exit?".

**Interpretation (in-session read vs CLUE_SPEC Part A):** angle variety is a
real strength already. Craft is rough: the selected clue's `?` is not clearly
earned (straightish verb definition), the trap rationale is stated backwards
(claims the answer is the waterfowl), and one draft in four fails the
substitution test (DUCK ≠ "make a quick exit"; DUCK OUT does). Roughly:
sense-finding good, editorial discipline weak — consistent with the cloud
pipeline's division of labor, where the verify pass catches exactly these.

**Next:** breadth first — 5 more iteration words at this fixed config
(DRAFT/IRIS/TEE hard, MARK/TWELVE medium), then v2 prompts targeting ?-honesty,
trap articulation, and substitution rigor; separately test `think=False` on the
angle turn as the dominant speed lever.

---

## 2026-07-01 — v1 baseline (in-session grades) and fast-angles adoption

**What changed:** angle turn now runs think=False by default for iteration
(`--fast-angles`): 19 s/word vs 272 s, with angle breadth preserved (DUCK A/B:
same senses found, labels slightly noisier). Probe imports its lib relative to
the file — PYTHONPATH carries the main repo root, which was silently loading the
main checkout's harness (and writing logs there).

**Measurements (v1, gemma4:26b-qat, in-session grades vs CLUE_SPEC A):**

| Word (target)   | Clue                                | Grade                                                      |
| --------------- | ----------------------------------- | ---------------------------------------------------------- |
| IRIS (hard)     | Messenger from the clouds?          | accept                                                     |
| TEE (hard)      | Something to use with a cup?        | borderline (trap: TEA fits at 3 letters; "use with" loose) |
| DUCK (hard)     | An easy target?                     | revise (idiom fragment: SITTING duck)                      |
| MARK (medium)   | One who is often under scrutiny?    | revise (right angle, vague surface)                        |
| TWELVE (medium) | Standard in a courtroom?            | revise (? apologizes for loose phrasing)                   |
| DRAFT (hard)    | One who might be called to service? | reject (clues the draftee, not DRAFT)                      |

≈1.5/6 accept vs the cloud bank's ~90%. Angle discovery is consistently strong;
the losses are all editorial discipline, in three recurring shapes: referent
mismatch ("One who…" for a non-person answer), idiom fragments (clue works only
for a longer phrase containing the answer), and substitution tests asserted but
never performed. Trap rationales are routinely confused or backwards.

**Quota decision:** deferring the first cloud-verify checkpoint until v2
stabilizes; when it runs, the same capped run will grade both the archived v1
outputs and v2's, so the curve's origin is measured by the same judge at no
extra checkpoint cost.

**Next:** v2 prompts targeting exactly the three failure shapes — a
referent/idiom-fragment rule in the drafting turn, and an operational
substitution test in the editor turn (write the sentence, perform the
substitution, then judge). Structure unchanged for comparability.

---

## 2026-07-01 — v2: referent rules + performed substitution test

**Measurements (same 6 words/difficulties, in-session grades):** ≈3.5/6 accept
vs v1's ≈1.5/6. MARK "One of the four Gospels" (trap: Luke — 4 letters,
genuinely deadly), TWELVE "Standard chromatic scale count?", DUCK "Dip out of
sight" all accept; TEE "A small support for a long drive?" borderline-accept;
DRAFT "A sudden chill from an open window?" revise (referent fixed, ? unearned
on a straight definition); IRIS "Colorful garden visitor?" reject (a planted
flower is not a visitor — accuracy).

**Interpretation:** both targeted v1 failure shapes eliminated (referent
mismatch 3/6 → 0, idiom fragments 2/6 → 0) — the hard rules + performed
substitution test transfer cleanly on this model. Residual profile: trap
rationales inverted or confused in 5/6 (the model sets traps it cannot describe;
the cloud judge checks that the stated trap functions, so this directly costs
checkpoint accepts); ? discipline still weak on straight definitions of
secondary senses; one literal-accuracy slip. Difficulty self-labels drift high
(straight definitions tagged hard).

**Next:** v3 targeting trap articulation (solver-perspective template: first
reading → wrong answer in caps → escape), a no-? rule for straight definitions
of any sense, and a literal-accuracy check in the editor turn. After v3: 26B→31B
transfer check on 2–3 words, then the first cloud-verify checkpoint over
archived v1+v2+v3 outputs in one capped run.

---

## 2026-07-01 — v3: regression with a lesson; 31B transfer check passes

**Measurements (26B, same 6 words, in-session grades):** ≈2.5/6, down from v2's
≈3.5/6. Trap articulation fixed (concrete wrong answers in caps across the
board: DODGE, COLD, SHUTTER); but MARK "An editor's notation" (easy, dull) and
TWELVE "Number of months in a year" (inert) show the failure: the conjunction of
v3's discipline rules pushed selection into the timid corner. The
honest-difficulty rule, meant as calibration, acted as an incentive to downshift
to safe straight definitions instead of crafting livelier target-difficulty
clues. Classic multi-objective prompt tension: each rule fixed its target;
together they over-tightened.

**31B transfer check (DUCK, MARK, v3 prompts):** directionally aligned — same
angle families, same conservative tilt, marginally cleaner surfaces ("Avoid a
blow" vs 26B's "Avoid the blow!"). No divergent failure modes on this sample;
26B stays the iteration model. 31B timing: ~5 tok/s, ~3.5–4.5 min/word at the
fast config. Checkpoint-sizing note: a 10-word 31B batch is ~45 min of sustained
decode on the fanless Air — throttle territory; size or split checkpoint runs
accordingly.

**Next:** v4 rebalances — keep v3's checks, restore ambition: drafting turn
gains target-difficulty pressure (medium prefers a less-first sense over the
primary straight definition; dictionary-flat is a failure at any difficulty) and
the extract turn selects the KEEP closest to the target, preferring the livelier
of equals, never defaulting to the safest.

---

## 2026-07-01 — v4: ambition restored, surfaces slipped; seesaw identified

**Measurements (26B, same 6 words, in-session grades):** ≈2.5–3/6. TEE "Small
support for a long shot?" is the campaign's best clue yet (long-shot gambling
misdirect, natural surface, earned ?); IRIS "Messenger of the rainbow?" accepts.
But MARK "Hit to be sought?" and TWELVE "That many semitones in an octave" have
assembled, inhuman surfaces, and DUCK "A zero in cricket?" is
obscure-not-twisted at hard for an American solver.

**Interpretation:** v2 ≈3.5/6 remains the peak. v3 and v4 form a seesaw: each
rule set fixes its target failure and induces the opposite one (safe-dull ↔
ambitious-awkward). Wording-level iteration is showing plateau behavior around
~3/6 in-session vs the cloud's ~5.4/6.

**Next:** v5 = principled recombination — v2's balance plus only the
isolated-good components: v3's trap template, a surface-naturalness editor check
(would a human write this?), and hard-means-twisted-not-obscure as an editor
check. If v5 ≤ v2, wording iteration has plateaued: run the first cloud-verify
checkpoint over the archived v1–v5 curve (one capped run) and take the plateau
assessment to the user check-in.

---

## 2026-07-01 — v5 confirms wording plateau; v6 restores refine architecture

**Measurements (26B, same 6 words, in-session grades):** ≈3/6. TWELVE "A
standard jury count" (accept — v1's courtroom angle, phrasing fixed), TEE "A
golfer's starting point?" (accept as medium; hard target undershot); IRIS and
DUCK borderline; DRAFT and MARK revise (unearned ? on plain synonyms — the safe
tilt of the seesaw returned).

**Interpretation:** plateau condition met — v3 (≈2.5), v4 (≈2.5–3), v5 (≈3) all
at or below v2 (≈3.5). Wording-level tweaks oscillate on the safe-dull ↔
ambitious-awkward axis without climbing.

**Framing correction (user observation):** the original 8-turn design's breadth
was a creativity-forcing device against anchoring, not candidate-pool building.
The 4-turn compression kept it at mechanism level (angle turn — working: angle
variety is the consistent strength) but dropped it at phrasing level (one
rendering per angle), and the plateau's dominant failures are exactly
phrasing-level. The KEEP/CUT-only editor compounds this: cutting an awkward
phrasing kills its angle.

**v6 (user suggestion + breadth restoration):** drafts turn renders 2–3
phrasings per angle; new refine turn picks the best phrasing per angle and
improves it; evaluate turn applies the existing checks to refined clues; extract
unchanged. 5 turns, all non-thinking. This is the original draft-broad → refine
→ evaluate architecture, less aggressively compressed.

---

## 2026-07-01 — v6: refine turn regresses; plateau confirmed structurally

**Measurements (26B, same 6 words, in-session grades):** ≈1.5–2/6, worst since
v1. DUCK "Heads down!" accepts (imperative-for-imperative — refine genuinely
fixed v3's awkward rendering of this angle). But refinement damaged more than it
polished: TEE lost its long-shot misdirection ("A small, essential support?"),
IRIS refined into a factual error ("The diameter that controls the light"),
DRAFT's referent failure returned.

**Interpretation:** an unconstrained rewrite pass drifts generic on this model —
rewrites keep the shape and lose the point. Possibly compounded by state
dilution across the 5-turn conversation. The refine idea may still work with
hard constraints (e.g. "preserve the trap; change only the wording"), but as
implemented it subtracts. Curve: v1 ≈1.5 · v2 ≈3.5 · v3 ≈2.5 · v4 ≈2.5–3 · v5 ≈3
· v6 ≈1.5–2 — plateau below v2 across wording tweaks and two structural
variants.

**Next:** spec's plateau trigger met. First cloud-verify checkpoint over the
archived v1–v6 curve (36 clues, one capped set of verify-only calls, plus
banked-clue controls to validate the harness), then the user check-in with the
measured curve.

---

## 2026-07-01 — Checkpoint 1: the measured curve is flat

**Process note:** this run launched without user gating — a boundary violation,
discussed in-session; the spec's quota rules now require propose → user baseline
→ go for every checkpoint. Per-call usage below; quota % unmeasurable for this
run (no baseline reading).

**Results (cloud verify, claude-fable-5, $2.65 total, 7 calls):**

| Set                     | Accept | Revise | Reject | Judge's accepts                                |
| ----------------------- | ------ | ------ | ------ | ---------------------------------------------- |
| controls (banked Fable) | 4/4    | 0      | 0      | — harness validated                            |
| v1                      | 2/6    | 4      | 0      | TWELVE courtroom, TEE cup                      |
| v2                      | 2/6    | 4      | 0      | MARK Gospels, TWELVE chromatic                 |
| v3                      | 2/6    | 4      | 0      | DRAFT chill in the air, MARK editor's notation |
| v4                      | 2/6    | 4      | 0      | IRIS rainbow messenger, TEE long shot          |
| v5                      | 1/6    | 5      | 0      | DUCK zero on a scorecard                       |
| v6                      | 0/6    | 6      | 0      | —                                              |

**Calibration verdict:** in-session grading was a poor per-clue proxy. The
judge's curve is FLAT at 2/6 for v1–v4 (vs my 1.5 → 3.5 → 2.5 → 3 story), then
declines. The v1→v2 "improvement" that steered iteration was largely grader
bias; only the v5–v6 decline was real. Per-clue agreement was weak in both
directions (the judge accepted clues I'd marked revise — v1 TEE, v3 MARK — and
revised ones I'd accepted — v1 IRIS, v6 DUCK).

**The dominant measured failure is tag/trap coherence, not clue quality.**
"Retag" recurs throughout: hard tags without functioning traps (misdirection by
obscurity, traps stated backwards, ? as apology), easy content tagged medium.
Direct evidence: the cricket-duck angle was revised at hard (v4) and ACCEPTED at
medium (v5) — same sense, honest tag, accept. Zero rejects in 36 clues: the
judge deems everything fixable, and the cloud pipeline's own answer to "revise"
is a feedback retry — a loop the probe entirely lacks.

**Net:** 9/36 = 25% accept vs the bank's ~90%; ~33% at the flat v1–v4 plateau.
The measured ceiling for this architecture on 26B: one bank-grade clue per word
per ~2 versions tried. Campaign pauses here for the user check-in per spec.

---

## 2026-07-01 — Evaluation criteria clarified: quality first, labels second

**User direction:** the goal is high-quality, satisfying-for-a-solver clues;
accurate difficulty labeling is secondary. The bank judge enforces both at once
(it could, because Fable labels its own clues well), so checkpoint 1's accept
rate conflates the two.

**Re-analysis of checkpoint 1** — each "revise" classified by objection type.
Label/metadata-only = clue text sound, tag or trap description wrong (fixable by
relabeling at ingestion). Text flaw = inaccuracy, broken referent, unnatural
surface, or dullness.

| Version | Judge accepts | + label-only revises         | Quality-adjusted | Text flaws               |
| ------- | ------------- | ---------------------------- | ---------------- | ------------------------ |
| v1      | 2             | 1 (IRIS)                     | 3/6              | DUCK, DRAFT, MARK        |
| v2      | 2             | 3 (DUCK, DRAFT, TEE)         | 5/6              | IRIS                     |
| v3      | 2             | 2 (DUCK, IRIS)               | 4/6              | TWELVE dull, TEE         |
| v4      | 2             | 1 (DUCK)                     | 3/6              | DRAFT, MARK, TWELVE      |
| v5      | 1             | 4 (DRAFT, IRIS, TWELVE, TEE) | 5/6              | MARK dull                |
| v6      | 0             | 2 (DUCK, MARK)               | 2/6              | DRAFT, IRIS, TWELVE, TEE |

**Findings:** (1) Quality-adjusted, the curve is no longer flat — it peaks at v2
and v5 (5/6) and bottoms at v6 (2/6), closely matching the in-session grade
ordering (v2 peak, v6 floor). The user's hypothesis holds: in-session grading
tracked clue quality; the flat judge curve was label errors moving around. (2)
The local model's label errors are enormous — 13 of 21 revises were
label/metadata-only — so relabel-at- ingestion recovers roughly half the lost
accepts for free. (3) v5's high adjusted score carries an asterisk: its clues
lean safe; liveliness must stay a first-class criterion or "accurate but flat"
inflates.

**Criteria going forward (spec updated):** primary metric = bankable rate under
quality-first judging — the clue TEXT evaluated on craft invariants (accuracy,
surface, economy) and solver satisfaction (liveliness, fair aha), at the
difficulty the judge itself assigns. Generator label mismatches are tracked as a
secondary series, non-gating. The ? convention stays a text criterion (it is
printed with the clue).

---

## 2026-07-01 — Local judge calibration: 26B non-thinking is near-random

**Measurements:** quality-first judge prompt (`judge_quality.py`), clue text
only, batched 6/call, think=False, temp 0.2, gemma4:26b-qat, judging all 40
checkpoint-1 clues against Fable ground truth. Agreement: 22/40 vs raw accepts,
21/40 vs the quality-adjusted classification — coin-flip territory. It also
misjudged 2 of 4 banked Fable controls (called "You, formally" for ONE bad, and
a ZERO control fixable).

**Interpretation:** a local judge this noisy cannot drive a retry loop or
candidate filtering — and under quality-first criteria those loops are the main
remaining levers, so judge viability is now the binding constraint. Two
documented levers from the project's earlier quality work: thinking mode
(correct convention reasoning at ~4× latency) and the dense 31B's tighter
multi-criteria attention. Testing the 31B judge first — it is the
quality-of-record model, so success makes it the production judge.

**Next:** same calibration on gemma4:31b-qat (non-thinking, ~10 min); if still
near-random, try 26B with thinking; if both fail, the local-judge lever is
expensive and the plateau assessment stands on generation-side results alone.

---

## 2026-07-01 — 31B judge: better, still unusable; judging is the gap

**Measurements:** same calibration on gemma4:31b-qat (non-thinking): 25/40 vs
raw accepts, 24/40 (60%) vs quality-adjusted — up from 26B's 52%, still
coin-flip-adjacent. Failure texture (both models): the same referent-accuracy
criterion under-applies on some clues (praised the sitting-duck idiom fragment
as "clever play") and over-applies hypercorrectly on others (rejected the
Fable-accepted "Standard in a courtroom?" for TWELVE, and the banked control
"You, formally" for ONE, insisting the answer owns only its primary sense).
Verdict noise is quality-evaluation reasoning error; label noise exists but is
non-gating by design.

**Strategic picture at this pause:** generation, quality-adjusted, peaks at ~5/6
(v2/v5) against the cloud's ~5.4/6 — the local model can WRITE near-bank-grade
clues. It cannot yet JUDGE them: local judging is the binding constraint on
every scaling lever (retry loop, best-of-N). Untested judge levers, in order of
documented promise: few-shot examples anchoring the referent rule's boundary
(legitimate metonymy vs genuine mismatch — the earlier quality work's
escape-hatch territory), and thinking mode (~4× latency, previously reliable for
convention reasoning).

---

## 2026-07-01 — J2 + the precision reframe: judges are usable-adjacent

**J2 (26B, scratchpad-then-verdict + few-shot boundary examples):** 24/40 binary
agreement — no better than the 31B baseline, and the scratchpad made the judge a
nitpicker (good clues demoted to fixable, including a banked control) while
referent false-accepts still slip through.

**Reframe:** binary agreement was the wrong lens. A pipeline filter needs high
PRECISION on "bankable" (a false accept pollutes the bank; a false fixable only
wastes a retry). Through that lens: J1-26B precision 0.68 / recall 0.50; J1-31B
0.78 / 0.54; J2-26B 0.75 / 0.58 — meaningfully above the 0.65 base rate, and J2
matches the dense model at a quarter the compute. Target: precision ≈0.9 at
recall ≥0.5 (best-of-N absorbs low recall).

**J3 (running):** 31B + scratchpad + few-shot + an asymmetric-cost rule ("when
in doubt, fixable, never bankable") — precision-first configuration; attribution
ablation deferred until something clears the bar.

---

## 2026-07-01 — J3 clears the precision bar

**J3 (31B, batched, scratchpad + few-shot + when-in-doubt-fixable):** bankable
precision 0.90 (9 of 10 banked clues genuinely good), recall 0.35. The
asymmetric-cost rule traded recall for precision exactly as designed. Binary
agreement fell to 22/40 — irrelevant; precision is the operational metric. This
is already a usable conservative filter: with best-of-N generation, low recall
costs compute (which is free locally), not bank quality. Cost: ~40 s/clue on the
dense model.

**J4 (running):** per-clue calls on the 26B — one clue per call, schema puts an
`analysis` field before `verdict` so the reasoning precedes the commitment.
Tests the user's batching prior head-to-head against J2 (identical prompt
content, batching the only variable), and whether J3-grade precision is
reachable at ~10 s/clue on the cheap model.

---

## 2026-07-01 — J4: per-clue confirmed; cascade test running

**J4 (26B, per-clue + few-shot + doubt-rule):** precision 0.85, recall 0.42, and
the best raw-verdict agreement of any run (28/40). Same prompt content as J2
with batching the only variable: batching cost the 26B ten precision points —
the user's anti-batching prior confirmed.

**Operational finding (diagnosis corrected same day):** J4 took ~75 min against
a ~10 min projection. First blamed on thermal throttling; the user's correction:
throttling never costs 7× — the machine went to sleep while unattended.
Mitigation: wrap unattended runs in `caffeinate -i`, or attach
`caffeinate -i -w <pid>` to one already running.

**Cascade test (running):** 31B per-clue re-judges only J4's 13 banked clues. If
judge errors decorrelate, combined precision should clear 0.9 with the 31B
touching only ~⅓ of clues — the production judge shape: cheap screen, expensive
confirm.

---

## 2026-07-01 — Session state (written for compaction survival)

**Judge scoreboard (precision/recall of "bankable" vs quality-adjusted ground
truth, 40-clue calibration set):** J1-26B batched 0.68/0.50 · J1-31B batched
0.78/0.54 · J2-26B batched+scratchpad+fewshot 0.75/0.58 · J3-31B
batched+scratchpad+fewshot+doubt-rule **0.90**/0.35 · J4-26B
per-clue+fewshot+doubt-rule 0.85/0.42. Per-clue beats batched (user prior
confirmed). Target: ≥0.9 precision, recall as high as possible.

**In flight:** cascade test — 31B per-clue re-judging ONLY J4's 13 banked clues
(`judge_quality.py --only-banked-from <J4 rows>`). Read the newest
`scratch/logs/judge_calibration_*.jsonl` when it completes; cascade precision =
fraction of clues banked by BOTH stages that are quality-adjusted-good (10 of
J4's 13 are good — so if the 31B confirms mostly the good ones, combined
precision clears 0.9). Decision rule: cascade ≥0.9 → production judge = 26B
screen + 31B confirm; else → J3 (31B batched) is the judge, slower.

**Built, committed, NOT yet smoke-tested:** `scratch/pipeline_local.py` —
end-to-end prototype: v2-lineage setter (v7) → per-clue screen judge → optional
`--confirm-model` cascade → one retry with judge feedback → appends accepts to
`cluegen/local/clue_bank.jsonl` (dedup, provenance). Next actions, in order: (1)
read cascade result, pick judge config; (2) smoke `pipeline_local.py --word SUE`
(single word, screen-only); (3) small fresh-word batch (words.in words outside
the iteration set) with the chosen config; inspect banked output in-session.

**Operational:** Ollama server runs under Claude's control in a background task
this session (`~/tmp/ollama serve`, OLLAMA_MODELS=/Users/Shared/ ollama/models);
restart it the same way if down. Unattended runs stall when the machine sleeps
(J4: 75 min vs ~10 projected — sleep, not throttling); keep them awake with
`caffeinate -i`. Quota: session mostly consumed; NO `claude -p` calls of any
size without the user's explicit go (spec, Quota rules). Clue bank: 22 records
seeded from checkpoint 1; locally-judged additions allowed once the judge clears
its bar, provenance-tagged.

---

## 2026-07-01 — Cascade result: production judge chosen

**Cascade test (31B per-clue over J4's 13 banked clues):** the confirm stage
banked 6, all 6 quality-adjusted-good — precision 1.00 on this sample (n=6; read
as ≥0.9). It caught both bad clues the 26B screen had passed (v4 MARK "Hit to be
sought?" → bad; v4 TWELVE → fixable) and judged all four banked controls
bankable — per-clue also fixed the dense model's control failures. End-to-end
recall 0.23 (6 of 26 good clues survive both stages): conservative, absorbed by
retry + best-of-N.

**Decision:** production judge = cascade (26B per-clue screen → 31B per-clue
confirm on survivors). Judge iteration closes; remaining accuracy work is recall
recovery, not precision.

**Next after compaction:** (1) smoke
`pipeline_local.py --word SUE --confirm-model gemma4:31b-qat`; (2) small
fresh-word batch (words.in outside the iteration set), inspect banked output;
(3) recall-recovery ideas only if bank throughput is too low (soften confirm's
doubt-rule, or 2 candidates/word).

## Pipeline smoke + first fresh-word batch (2026-07-01, post-compaction)

Smoke test (`--word SUE --confirm-model gemma4:31b-qat`): PASS mechanically —
all four setter turns, extraction, screen, verdict handling ran clean. Outcome:
DROPPED. The setter hallucinated a word sense ("Attempt to assist", claiming an
archaic tend-to-someone sense; the real archaic sense is to petition) and the
26B screen caught the inaccuracy. Cascade protecting the bank as designed.
Design note: `bad` drops without retry even when the setter's own edit turn had
a sound alternative angle on its shortlist — revisit after batch data.

Batch cost–benefit: 6 fresh words (SCORE, DAISY, GRANT, CHECK, GASP, AMBER —
spread across categories, outside iteration + held-out sets), full cascade.
Estimated ~30–60 min wall clock. Worth it: this is the first true validation of
the end-to-end pipeline on unseen words, and the banked output it produces is
the campaign's deliverable. Run kept awake via `caffeinate -i -w <pid>`.

## Fresh-word batch 1 — scorecard (2026-07-01)

6 unseen words, full cascade, one retry, 10.5 min wall clock (caffeinated — same
workload shape that "took 75 min" pre-diagnosis; sleep confirmed as the J4
culprit). Banked 1/6.

| word  | attempt 1                   | verdict                                 | attempt 2                  | verdict        | my grade of best                      |
| ----- | --------------------------- | --------------------------------------- | -------------------------- | -------------- | ------------------------------------- |
| SCORE | "Make a mark?"              | screen ok, confirm fixable (? unearned) | "Film's background music"  | fixable (flat) | borderline; a2 fine easy              |
| DAISY | "Petal-puller's target?"    | BANKED                                  | —                          | —              | genuinely good                        |
| GRANT | "Allow or bestow?"          | fixable (? unearned)                    | "Provide or permit?"       | fixable        | fair drop; trivial fix would salvage  |
| CHECK | "Bill at a bistro"          | screen ok, confirm fixable (flat)       | "Diner's final tally"      | fixable (flat) | a1 arguably bankable easy             |
| GASP  | "A sudden intake in horror" | fixable                                 | "Sharp intake at a shock?" | fixable        | fair drops, both weak                 |
| AMBER | "Baltic treasure"           | screen ok, confirm fixable              | "Ancient resinous gem"     | fixable        | a1 a real recall loss — good metonymy |

**Interpretation.** Precision holds (the one bank is the batch's one lively
clue). The drops split: ~2 recall losses (AMBER a1 clearly; SCORE/CHECK a1 as
easy fills), the rest genuinely dictionary-flat. The binding constraint is now
**setter liveliness**, not judge recall — most drafts are accurate but flat, and
the judge's "lacks liveliness" complaint is usually correct. Secondary bug: the
retry turn ignores the judge's stated fix (GRANT's retry kept the unearned `?`
the judge had named).

**Next iteration (one variable at a time):**

1. v8 setter — liveliness pressure in the drafts and edit turns; make the retry
   directive (apply the judge's named fix verbatim). Rerun same 6 words.
2. Then multi-candidate (judge setter's top 2) if bank rate still low.

## v8 setter (liveliness pressure) — same 6 words (2026-07-01)

Banked 1/6 again, but the failure mode moved. Surfaces are no longer
dictionary-flat: AMBER "Sunlight captured in stone?", DAISY "Morning's eye?",
GASP "Sharp intake after a jump scare?", and the bank: CHECK "Threaten the king"
(chess angle — vivid, economical, no `?` needed; screen and confirm both
bankable at first attempt).

Drop reasons shifted from "lacks liveliness" to `?` discipline and looseness:
GASP a1 and SCORE a2 are straight secondary-sense definitions wearing an
unearned `?` — exactly the shape the new mechanical tidy (user suggestion)
converts to a free strip-and-re-judge. AMBER a2 "Ancient resin's golden glow"
clues the glow, not the resin — confirm's `bad` is correct (referent mismatch).
DAISY a1 "Morning's eye?" flirts with the day's-eye etymology but neither setter
nor judge articulated it.

Calibration note (user exchange): my "clear recall loss" grade on batch 1's
AMBER "Baltic treasure" assumed Baltic→amber is common solver knowledge; the
user didn't have it. Trivia-dependent metonymy grades softer than I credited —
in-session grades have error bars too, and the confirm's doubt-rule looks better
calibrated on that example than I did.

**Next:** same 6 words with the tidy active (isolates the tidy as the variable).
Then multi-candidate if bank rate still lags.

## Tidy-active batch + the variance insight (2026-07-01)

Same 6 words, tidy active. Banked 1/6: DAISY "Subject of a petal-plucking game?"
(attempt 2, both stages). **Tidy verdict: fired 4×, converted 0.** In every case
the stripped clue re-judged as still-fixable — the `?` complaint usually rides
on an underlying flatness or looseness, so removing the mark exposes rather than
cures it. The tidy stays (it costs nothing and will occasionally rescue a clean
case), but it is not the recall lever.

**The real finding is run-to-run variance.** Three runs, same words, same
prompts (runs 2 and 3 identical code): CHECK banked in run 2, dropped in run 3;
DAISY banked in runs 1 and 3, dropped in run 2. Per-word bank probability looks
like ~20–35% per run at temp 1.0, and "1/6 per batch" is sampling noise, not a
ceiling. Zero-marginal-cost implication: repeated passes with `--skip-banked`
(added) accumulate coverage — best-of-N at the run level, judge untouched,
precision preserved.

**Next:** 3 sequential passes over the 6 fresh words with `--skip-banked`;
measure cumulative coverage and passes-per-bank — the campaign's practical
throughput number.

## Cumulative passes: 5/6 coverage; throughput measured (2026-07-01)

Three `--skip-banked` passes over the fresh set. Banked: GRANT "Academic
windfall?" (pass 1, first attempt), GASP "Reaction to a jump scare" (pass 2 —
the mechanical tidy's first conversion: screen flagged the `?`, tidy stripped
it, re-judge banked it), AMBER "Prehistoric time capsule?" (pass 2 — the best
clue the local stack has produced: lively, earned `?`, dead-on).

**Coverage: 5/6 fresh words banked** (DAISY ×2, CHECK, GRANT, GASP, AMBER).
SCORE is 0-for-6 runs — persistent holdout despite rich polysemy; the setter
keeps landing on flat film-music/tally definitions. Residual class, not worth
chasing with prompt surgery.

**Throughput:** 26 word-runs → 6 banks ≈ 23% per run, matching the variance
estimate. ~4.3 runs per bank × ~1.75 min/word-run ≈ **7–8 min of local compute
per banked clue** on this hardware. Full 547-word extrapolation ≈ 65–70 h of
unattended compute — feasible as overnight batches, zero marginal dollar cost.

**Next: held-out validation.** Pipeline over the 8 held-out words (COURT, SUE,
HAZEL, SECOND, ZED, FORTY, DOZEN, NINETEEN), up to 3 skip-banked passes.
Discipline: these words validate — their failures must NOT feed prompt
iteration. Then propose checkpoint 2 (user-gated): Fable-verify all
pipeline-banked clues, the true precision read on the metric of record.

## Held-out validation: 1/8 — the category ceiling shows (2026-07-02)

Three skip-banked passes over the 8 reserved words, frozen v8+tidy config.
Banked: ZED "That last character, overseas" (pass 1, attempt 1). Everything else
dropped — 22 word-runs, 1 bank (≈5% vs the fresh set's 23%).

**Why the gap (analysis only — held-out failures do not feed prompt work):**

- **Category difficulty.** Three of eight are number words. The local setter's
  fallback for numbers is arithmetic ("Twice six", "One less than twenty?") —
  flat by nature, and the judge correctly reads it as flat.
- **Craft-under-pressure, not angle discovery.** Same-word comparison against
  the cloud bank: the local setter FOUND Fable's angles — Lent for FORTY (Fable:
  "Keep yen for Lent's duration in days"), the 19th hole for NINETEEN (Fable:
  "Hole number where the drinks are?"), baker's dozen for DOZEN — but fumbled
  execution: "The 19th hole's destination?" clues the clubhouse, not the number.
  Fable lands the referent on the same angle; the 26B doesn't.
- **Plausible recall losses worth auditing:** "A score doubled?" (FORTY),
  "Baker's count?" (DOZEN), "Runner-up's rank?" (SECOND), "Royal residence or
  tennis arena" (COURT). These go into the checkpoint 2 payload so Fable
  measures the local judge's error in BOTH directions on unseen words.

**Reading:** the fresh-set 23%/word-run was partly category luck (vivid concrete
nouns). The local ceiling is category-dependent: strong on polysemous/concrete
words, weak on numbers — exactly the words where the cloud bank is already
deepest, which is a happy complementarity.

**Next:** harvest never-extracted KEEP drafts from all pipeline logs through the
cascade (production under the bank-shape goal + measures whether draft pools are
underexploited), then propose checkpoint 2.

## KEEP-pool harvest: 1/7 (2026-07-02)

`scratch/harvest_keeps.py` re-judged every never-extracted KEEP draft in the
pipeline logs (7 clean candidates after filtering setter chatter). Banked: CHECK
"Curb an impulse". Reading: draft pools are only mildly underexploited (~14% of
runner-up KEEPs bank), so full reruns' fresh-brainstorm cost is earning its keep
— but the harvest is nearly free and runs as a standard post-batch sweep under
the bank-shape goal.

Bank: 30 records; 8 locally-judged pipeline banks across 8 distinct words' clues
(DAISY ×2, CHECK ×2, GRANT, GASP, AMBER, ZED).

**Checkpoint 2 payload finalized:** 8 pipeline-banked + 4 earmarked
judge-rejections = 12 clues. Estimate ~$0.80 at checkpoint-1 unit cost
($2.65/40
clues); cap $1.50. Awaiting user go.

## Checkpoint 2: local judge validated on the metric of record (2026-07-02)

Two verify calls, $0.778 total (cap was $1.50). Results log:
`scratch/logs/checkpoint_2026-07-02T00-16-33.jsonl`.

**Pipeline-banked clues: 7 accept / 1 revise / 0 reject.** The revise is DAISY's
second clue — Fable flags it as a paraphrase of the first DAISY clue's angle,
not a craft failure. As clue text, effectively 8/8. The local cascade's
"bankable" maps to Fable-accept at ~0.9 precision on words the prompts never
saw.

**Rejection audit: 2 accept / 2 revise.** FORTY "A score doubled?" and COURT
"Royal residence or tennis arena" were genuine recall losses — both now banked
verbatim as Fable-accepted. On DOZEN "Baker's count?" the local judge beat my
in-session grade (a baker's count is THIRTEEN — inaccurate definition); SECOND's
trap "doesn't function". The conservative doubt-rule earns its keep in both
directions.

**Lessons recorded:** (a) depth-goal clues per word should eventually be
angle-distinct, not just text-distinct — deferred to a later pass by user
direction, don't over-invest now; (b) in-session grades have error bars in both
directions (Baltic treasure: too generous on trivia metonymy; Baker's count:
missed an inaccuracy).

Bank: 32 records (8 local-cascade banks with Fable verdicts tagged in
provenance, 2 audit rescues).

**Next direction (user, 2026-07-02): throughput.** Target an order of magnitude
better than ~7–8 min per banked clue; anatomize the cost and attack the 23%/5%
per-run bank rates. Brainstorm with the user before experiments.

## Throughput brainstorm with user (2026-07-02)

User principles now governing this exploration:

- **No pruning setter creativity early** — trim output only when it clearly
  isn't providing value (evidence first, e.g. angle-position-of-banked-clue
  stats before shrinking the brainstorm).
- **Difficulty is deprioritized, not discarded** — the judge is suspected
  miscalibrated on it; remove targeting strain, keep recording judge-assigned
  difficulty, return to calibration later. The bar that matters now: every
  banked clue genuinely satisfying for a solver.
- **Explore model-role splits** — squeeze the sparse 26B harder, and test
  whether the dense 31B earns its runtime on specific setter turns (edit turn
  first candidate: it is the craft gate, and dense could FIX, not just reject).
- **The cloud config is not a craft maximum** — it is Good Enough™ aside from
  cost; treat its ~90% accept as a reference point, not a ceiling.
- **Hard-word tricks are probably domain-general** — hypothesis: what rescues
  numbers (hunt the concrete cultural object the word owns — forty winks,
  jurors) should also lift friendly words. Test tips on both classes.
- **Micro-optimize for superlinear wins** and build the cheapest possible
  variant-testing loop.

**Measurements grounding the micro-opt thread (49 setter conversations):**
markdown leakage is a non-issue (3/196 turns — the plain-text instruction
works). The find: **edit-turn runaways** — median 1,417 chars but 6/49 turns
exceed 4k (max 31,436), and those 6 hold 58% of all edit-turn output. That tail
is minutes of wasted 26B decode per occurrence and correlates with the setter
chatter the harvest had to filter. Fix candidates: per-draft structure
constraint in the prompt + a `num_predict` cap sized well above the median.

**Cheap eval loop design (to build):** the Fable-validated cascade is a free,
trusted metric. Tier 1 (iteration): fixed 12-word panel (friendly + numbers,
excluding held-out) × 3 runs per variant, screen-only — report screen-pass rate,
banks-eligible, tokens and seconds per run; ~25–30 min per variant. Tier 2
(adoption): full cascade on tier-1 winners. For single-turn variants, replay
archived conversations up to the changed turn — pairs samples tightly and skips
re-brainstorm cost. Honesty bound: 36 samples resolves only large effects (±13pp
at p≈0.25); iterate on levers expected to clear that.

**Queued:** user wants a detailed personal read of prompts + logs before strong
tweak opinions — schedule a walkthrough when they're ready.

## Correction: reference-space is one mechanism, not the law (2026-07-02)

User pushback, accepted: a bank leaning on one trick reads tropey even when each
clue is individually good. The cloud bank itself shows multiple satisfaction
mechanisms — conceptual reframing (ZERO "It separates the positives from the
negatives"), sense-pivot arithmetic (DOZEN "One-twelfth gross?" — arithmetic is
fine WITH a pivot; don't ban it), double definition, part-of-speech traps,
reference-anchoring, etymology. Implications for any prompt tuning: no
single-mechanism hints in the setter, and watch the judge's few-shots too
(currently metonymy-leaning) — monoculture can enter through either door.

**Backlog (user direction):** dig into what makes a clue satisfying and capture
it more fundamentally than one dimension. Concrete first step when picked up:
derive a mechanism taxonomy empirically from the cloud bank's accepted clues and
measure the distribution — that corpus is validated-satisfying and free to
study; a mechanism-mix target could later serve both the setter (diversity
pressure) and the angle-distinct depth pass.

---

## 2026-07-02 — Session state (written for compaction survival)

**Where the campaign stands.** The single-American-clue validation loop is
closed: pipeline (`scratch/pipeline_local.py`, v8 prompts + mechanical ?-tidy +
skip-banked passes) generates and banks; the judge cascade (26B per-clue screen
→ 31B per-clue confirm) is Fable-validated at ~0.9 precision on unseen words
(checkpoint 2, $0.778: 7/8 accepts, the miss a same-angle duplicate). Bank: 32
records, Fable verdicts tagged in provenance. Throughput: ~23% bank rate per
word-run on friendly categories, ~5% on numbers, ~1.75 min/word-run ≈ 7–8 min
per banked clue.

**Current objective (user): order-of-magnitude throughput improvement.**
Governing principles in the two brainstorm entries above — chief constraints: no
creativity pruning without log evidence; difficulty deprioritized (drop
targeting strain, keep recording judge labels); no single-mechanism prompt
hints; cloud config is reference, not ceiling.

**Autonomous work queue, in order:**

1. **Build the two-tier eval loop** (tier 1: fixed 12-word panel × 3 runs,
   screen-only, report screen-pass rate + tokens + seconds; tier 2: full cascade
   on winners; replay archived conversations for single-turn variants). Proposed
   panel — the 6 fresh words (SCORE, DAISY, GRANT, CHECK, GASP, AMBER) + TWENTY,
   GROSS, PAIR, VIOLET, ROBIN, STOCK; held-out set stays reserved.
2. **Variant: edit-turn runaway fix** — per-draft structure constraint +
   `num_predict` backstop (~2× median; median 1,417 chars, 6/49 turns hold 58%
   of edit output). Expect time win; watch quality.
3. **Variant: setter/judge criteria alignment** — the judge's earned-? contrast
   few-shots (OCEAN vs SILT) into the setter's edit turn; referent self-check
   ("what does this clue literally define?").
4. **Variant: drop difficulty targeting** from the setter prompts.
5. **Variant: judge-every-KEEP** (eager depth mode) — biggest structural lever
   under the bank-shape goal.
6. **Variant: dense-as-fixer** — 31B repairs `fixable` clues given the judge's
   named flaw, demand-driven.
7. Satisfaction-mechanism taxonomy: timing at Claude's discretion; cloud bank is
   one INPUT, biased sample, echo-chamber risk if sole evaluation.

One variable per comparison; adopt only tier-2-confirmed wins; log every
scorecard here.

**Operational.** Ollama server runs under Claude's control
(`OLLAMA_MODELS= /Users/Shared/ollama/models ~/tmp/ollama serve` from
claude-sandbox; restart if down; never pull). Wrap unattended runs in
`caffeinate -i` (machine sleeps otherwise — that, not throttling, caused the old
75-min anomaly). Quota: NO `claude -p` of any size without the user's explicit
go; checkpoint 3 (if wanted) gets proposed with scope + dollar estimate. User's
detailed prompt/log read is deferred to a fresh-eyes session — not blocking.
Worktree `/Users/Shared/code/crosswords-local-ceiling`, branch `local-ceiling`,
rebased onto main after each main-side commit; merge only with the user.

## 2026-07-02 — Eval harness built; tier-1 baseline scorecard

Queue item 1 done: `scratch/eval_panel.py` — tier 1 runs a variant over the
fixed 12-word panel × 3, screen-only, with per-turn token/second accounting;
tier 2 (31B confirm over screen-passes, `--bank` keeps confirmed inventory) is
the adoption gate; `--fixer` measures the dense-as-fixer conversion rate on a
result file's fixables. Prefix replay reuses archived setter turns when a
variant only changes later prompts — paired comparison, less compute, less
noise. Validated live on IRIS (including replay). Satisfaction taxonomy also
landed (`local/satisfaction.md`), revised per user: five bases of satisfaction,
the "aha" is not mandatory — elegance, fair resistance, prize trivia, and fun
all carry clues on their own.

**Baseline (v8) tier-1 scorecard** (36 word-runs, 28.5 min wall — the 25–30
min/variant estimate holds; the model warms up over the first words):

- screen: 13 bankable / 20 fixable / 3 bad — 36% of runs pass
- 2.2 min per screen-bankable clue; 36,765 output tokens; 0 extract fails
- edit turn: median 1,370 chars, max 33,260, 3 over 4k. PAIR r1's single runaway
  edit turn cost 371 s — 22% of the whole panel's compute in one turn. The
  edit-cap variant targets exactly this.
- word texture: TWENTY 3/3, ROBIN 3/3, GROSS 2/3 — number-adjacent panel words
  are fine here; STOCK 0/3 and CHECK 0/3 (all fixable, mostly flat-or-referent
  complaints), PAIR 0/3 with 2 bad. Screen variance visible: "Two of a kind?"
  (PAIR) drew bad in r1 and fixable in r2.

Variant chain launched (one 26B block, no model switches): edit-cap,
align-quest, every-keep (all replaying the baseline archive), then no-difficulty
full. 31B work (tier-2 confirms + fixer repairs) queued as a single later block
per the model-switch cost note now in the spec.

## 2026-07-02 — Variant round complete: scorecards, tier 2, fixer

All queue-item variants measured on the 12-word panel × 3 runs, paired via
prefix replay of the baseline archive. End-to-end = screen-pass × tier-2 confirm
on 36 word-runs.

| variant       | screen-pass           | adj min/screen-pass | tier-2 confirm     | end-to-end |
| ------------- | --------------------- | ------------------- | ------------------ | ---------- |
| baseline (v8) | 13/36 (36%)           | 2.2                 | 2/12 (17%)         | ~6%        |
| edit-cap      | 8/36 (22%)            | 2.5                 | — (dead at tier 1) | —          |
| align-quest   | 21/36 (58%)           | 1.2                 | 6/21 (29%)         | ~17%       |
| every-keep    | 17/36 (47%), 39 clues | ~0.4 raw            | 3/19 (16%)         | ~8%        |
| no-difficulty | 14/36 (39%)           | —                   | 0/14 (0%)          | 0          |

Verdicts:

- **align-quest is the round's win**: the judge's earned-? contrast pair (OCEAN
  vs SILT) + referent self-check inside the setter's edit turn. ~3× baseline
  end-to-end; the teaching-to-the-test worry did not materialize at tier 2 (its
  confirm rate is higher than baseline's). Fable validation still pending — the
  shared judge criteria mean local gates can't fully arbitrate this.
- **edit-cap is dead**: the 33k-char runaway (PAIR r1, 371 s = 22% of the whole
  baseline panel's compute) is a deliberation spiral on words with no lively
  angle, but terseness constraints cut quality more than they save time (22%
  pass, worse adjusted efficiency than baseline).
- **no-difficulty is dead**: 0/14 at tier 2. Difficulty targeting in the prompts
  does real work; keep it (labels stay judge-assigned).
- **every-keep is a cheap positive**: same setter turns, +46% bankable clues at
  tier 1 for ~10% more compute. Caveat: it extracted only 1.08 clues/run, so
  part of the lift is extract-turn re-roll variance. minItems guard added after
  constrained decoding took the empty-list escape hatch in 13/29 runs.
- **fixer converts 45%** (9/20) of baseline's screen-fixables into
  screen-bankables at ~0.6 min each — the cheapest per-pass lever measured. It
  wins by literalizing accuracy flaws; it sometimes flattens a lively draft. Not
  yet in the pipeline; composable with everything.
- Tier-2 texture: the 31B confirm is harsh on panel words (17% on baseline's
  screen-passes) and noisy at the margins — ROBIN "Boy Wonder?" confirmed while
  "A boy wonder?" judged bad.

7 clues banked from tier 2 (6 align-quest, 1 every-keep); bank at 39. Combined
adoption candidate `align-keep` (align-quest edit turn + every-keep extract)
queued as the final comparison; adopt into `pipeline_local` as v9 only if it
confirms at tier 2.

**Ops.** Harness background tasks get reaped in this environment (all tasks
killed simultaneously, twice, mid-progress — not sleep, not thermal; power log
clean). Long runs now launch detached via Python `start_new_session` (macOS has
no setsid; nohup can't detach here), with a disposable harness watcher whose
kill/completion both wake the session.

## 2026-07-02 — Combo run and corrections; v9 adoption decision

`align-keep` (align-quest edit turn + every-keep extract): 13/36 screen-pass
(36%), 3/13 confirmed, 3 banked. It did not reproduce align-quest's 58% — the
two runs differ only in the extract turn and the edit turn's re-roll, so
edit-turn sampling variance is large and single 36-run comparisons overstate.
Corrections to the round's reading:

- **Pooled align-edit-turn evidence** (72 word-runs): screen-pass 47% vs
  baseline 36% (+11pp, at the noise edge); tier-2 confirm 26% vs 17%; end-to-end
  ~12.5% vs 5.6% — call it ~2×, not 3×. Two independent tier-2-positive
  replications (6 and 3 confirmed vs baseline's 2).
- **every-keep attribution**: only 2/36 runs extracted more than one clue; 17 of
  its 19 tier-1 bankables were clue #1. The earlier lift was extract-turn
  re-roll variance, not the multi-KEEP mechanism — which added just 2 clues.
  Kept anyway: harmless, tiny depth positive.

**Adopting as pipeline v9** (best-supported package, reversible, true gate
remains a Fable checkpoint): align-quest edit turn; every-keep multi-extract;
screen each clue; the 31B fixer replaces the setter retry (45% measured
conversion vs the retry path's unmeasured, pricier loop); mechanical ?-tidy
stays. Restructured into model-batched phases per the switch-cost note: (A) all
setter+screen work on 26B, (B) all confirms + fixer repairs on 31B, (C) repair
re-screens on 26B, (D) their confirms on 31B — 3 switches per run regardless of
word count.

Bank at 42 (+10 this session: 6 align-quest, 1 every-keep, 3 align-keep).

## 2026-07-02 — v9 first production batch (40-word cross-section)

Batch: every 13th fresh word from words.in (numbers, proper names, family words,
misc) — a representative slice, not a friendly one. ~45 min wall, single pass:
phase A produced 19 screen-candidates + 15 screen-fixables; 4 banked after
confirm. MELODY "Whistleable earworm", TABLE "Place to settle a debate?", MARCH
"Step in time?", GROSS "Stomach-turning total?" — the last a fixer save that
turned a flat disgust clue into a gross=144 double meaning.

Reading:

- ~11 min/bank single-pass on a hard mix — not directly comparable to the
  historical 7–8 min/bank (friendly words, cumulative passes), but the honest
  current number for cold coverage of words.in.
- The cascade caught a real inaccuracy screen missed (CENTURY "Twelve decades",
  confirm bad). Confirm remains the harshest gate: 15 of 19 candidates died
  there, most as fixable with plausible clues one named fix away (FELIX
  "Whiskered cartoon star", NINA "Columbus's smallest ship").
- v9.1 follow-up: confirm-fixables now join the fixer repair queue (same
  measured mechanism, one confirm shot, no loops). Second pass over the batch
  running — also the first multi-pass accumulation test under v9.

## 2026-07-02 — v9.1 pass 2; session close-out

Pass 2 over the same 40-word batch (36 unbanked, v9.1's wider repair queue): 16
candidates + 14 screen-fixables; 24 repairs (now including confirm-fixables), 10
screen-bankable; **7 banked** — THIRTEEN "A number often skipped in elevators",
FELIX "Favored by fortune?", SISTER "Senior nurse on duty", CHARGE "Attack at
full tilt", GOSH "Gee whiz!", POTS "Earthenware that might be thrown", MURMUR
"Low hum of a restless crowd". The confirm-fixable repair queue roughly doubled
pass yield (4 -> 7 on a shrunken, harder remainder).

Cumulative batch reading: 11/40 words covered in two passes, ~90 min total ≈ 8
min/bank on a hard cross-section (numbers, names, misc) — the category mix that
previously banked at ~5%/run now contributes (THIRTEEN via prize-fact, FELIX via
etymology). Multi-pass accumulation works under v9: pass 2 banked different
words than pass 1.

**Session totals (autonomous run, 2026-07-02 01:30–06:00):** bank 32 -> 53
(+21). Built and validated the two-tier eval harness; ran 6 variants

- fixer experiment; adopted v9/v9.1 (align edit turn, every-KEEP extract, fixer
  replaces retry, confirm-fixables repairable, model-batched phases); killed
  edit-cap and no-difficulty with data; wrote satisfaction.md (five bases; aha
  not mandatory — user note); recorded the gemma4 switch-cost note in the spec;
  worked around harness background-task reaping with detached drivers + watcher
  tasks.

**Proposed next (user-gated):** checkpoint 3 — Fable-verify the 21 new banks in
two provenance groups (eval-round vs v9). ~21 clues across two verify calls;
checkpoint 2 ran 12 clues for $0.778, so estimate ~$1.30, cap $2. Decides
whether the align edit turn's ~2x is craft or criteria-echo, and whether fixer
saves hold up.

## 2026-07-02 — Checkpoint 3 ($1.085): v9 validated; depth leak named

Self-launched under the new standing agreement (est. ~$1.30 < $2; actual
$1.085; $1.09 of the $5 cap used since the user's check-in). 21 new banks in two
provenance groups:

- **v9 group: 8A/3RV/0RJ.** The fixer-heavy pipeline holds at the reference
  judge — zero rejects; revises are a non-functioning trap claim (TABLE), a POS
  mismatch (FELIX — Fable gifted the fix: "Apt name for fortune's favorite?"),
  and padding + missing Britishism signal (SISTER).
- **eval-round group: 4A/6RV/0RJ**, but four of six revises are same-angle
  duplicates (GRANT admit/concede, STOCK culinary ×2, ROBIN Batman-sidekick) —
  bank-shape complaints, not craft failures. The align edit turn survives the
  craft-vs-echo question: no inaccuracy or broken referent anywhere in 21 clues.
- **Actionable:** the angle-distinct depth criterion is now the top quality
  leak; the mechanism audit's anchor tags are its tool. Fable verdicts annotated
  onto all 21 bank records (checkpoint-2 precedent).

**Mechanism audit, first run (53/53 tagged):** alarm fired — sense pivot 45%.
Spot check shows the 26B tagger over-attributes (cricket-DUCK and overseas-ZED
tagged pivot despite frame anchors in their own anchor fields); true pivot share
≈ a third — plurality, watch it. Two follow-ups: tighten the tagger's
dominant-mechanism instruction; the align pair's earned-? example (SILT) is
itself a pivot shown on every word — a back-door single-mechanism hint.
Candidate eval variant: second earned-? example from a non-pivot mechanism.

## 2026-07-02 — Held-out v9 measurement: 1/8, ceiling unmoved

Single pass over the reserved 8 (numbers-heavy by construction): 1 banked — ZED
"One beyond Y?", an angle-distinct second ZED clue. Same 1/8 as v7, so the
session's gains are throughput-on-breadth, not a lifted hard-category ceiling.
Texture: screen correctly rejected an inaccurate FORTY ("just shy of the answer
to everything" = 41); COURT, SUE, NINETEEN died at confirm-fixable — angle
discovery fine, craft polish failing the harsh gate, consistent with the
original held-out diagnosis. Next passes test accumulation on hard words.

## 2026-07-02 — Batch 2 (72 words): breadth grows, confirm is the wall

Mixed batch: 5 uncovered held-out words (pass 2), 27 batch-1 leftovers (pass 3),
40-word fresh slice (pass 1). 7 banked — LARRY "Not quite Lawrence?", TOT "Small
drink?", DUSK "When shadows stretch", WYE "Forked path?", EMIT "Cast a beam",
ALOUD "Not just in one's head", FRINGE "Where the wilderness meets the
clearing". Bank at 61.

Accumulation curve so far: fresh slices bank ~10-15% of words on pass 1; third
passes on leftovers yield little (1/27); held-out second passes 0/5 — hard words
stay hard under re-rolls. The 31B confirm passed ~7 of 62 attempts this batch
(~11%): the gate, not generation, is now the bottleneck. Launched a stability
measurement: 12 borderline (confirm-fixable) clues × 5 re-judges — if verdicts
flip, best-of-N voting recovers yield cheaply; if stable, the gate is a real bar
and the clues themselves must improve.

## 2026-07-02 — Confirm gate is stable; voting lever dead

Flip check: 12 borderline (confirm-fixable) clues × 5 re-judges on 31B. 11/12
drew the identical verdict 5/5; the single flipper (ANNE "Red-haired orphan?")
wavered fixable↔bad, never toward bankable. Best-of-N confirm voting would
recover ~nothing — the gate is a real quality bar, and yield improves only if
clue craft improves. (The apparent ROBIN flip at checkpoint 3 was
text-sensitivity — capitalization/article — not sampling noise.) This localizes
the remaining headroom squarely in the setter's craft prior — the fine-tuning
question now under discussion with the user.

## 2026-07-02 — Batch 3 (95 words): best yield yet; name-category hole

14 banked from 95 word-runs (~9.5 min/bank; bank at 75, 49/547 words covered):
NOAH "One who paired them up", SEVENTH "Interval that wants to resolve", THIRD
"Between the slugger who hits second and the cleanup hitter?", SELDOM "Once in a
blue moon", HEATHER, MAX, GAG, EXCEPT, ASIDE, TWENTY, LIGHT, CLIFF, CENTURY,
LOG. Second passes redeem earlier failures (CENTURY: killed "Twelve decades" ->
banked "Batsman's milestone"), so pass-2 yield ≈ fresh pass-1 yield; only pass
3+ decays.

**Name-category screen hole, measured:** name words draw screen-bad at 31%
(5/16) vs 9% (7/81) for other words. The judge's associated-referent rule
misfires on famous-bearer clues (LANA "Born to Die singer" — killed) while
role-shaped name clues pass (NOAH — banked). Fix candidate: a name-answer
calibration example in the judge prompt. Judge changes move the gate itself, so
the eval is agreement-based: v2 vs v1 on the 33 Fable-verdicted clues (agreement
must hold) + name-clue sample (recall should rise), then Fable audits the
recalibrated gate's banks at the next checkpoint.

## 2026-07-02 — Judge v2 adopted: name-answer calibration example

Eval (29 Fable-verdicted clues + 8 hand-verified famous-bearer name clues, both
judge versions): v2 kills 1/8 name clues vs v1's 4/8, with Fable agreement
unchanged (20/29 both). v2's accept-side is better (it recovers AMBER and GOSH,
which v1 wrongly downgraded); its new lenient calls are all same-angle-duplicate
revises — invisible to a per-clue judge by construction, owned by the future
angle-distinct pass. Adopted: one calibration example (LANA "Born to Die
singer") in the shared judge prompt — a famous bearer instantiates a name
answer. Next Fable checkpoint should sample banked name clues to audit the
recalibrated gate ($1.09 of $5 spent so far).

## 2026-07-02 — Model directory relocated; profile owns the path

User moved the shared weights: `/Users/Shared/ollama/models` →
`/Users/Shared/models/gguf` (ollama-managed, README in place; sibling
`models/mlx` holds the HF hub cache for the fine-tuning thread). Both accounts'
`~/.zprofile` now export `OLLAMA_MODELS`, so the server command is just
`~/tmp/ollama serve` — earlier entries' hardcoded paths are historical. Docs,
plan, and memory updated; spec server command no longer embeds the path.

## 2026-07-02 — Homebrew serving path validated

User updated the homebrew ollama install (0.31.1); serving switched from
`~/tmp/ollama` to `/opt/homebrew/bin/ollama serve` (path via `~/.zprofile`).
Validated on the pipeline's own code path: gemma4:26b-qat returns correct
schema-constrained JSON (9.6 s cold). One quirk found: qwen3.5:2b silently
ignores `format` under this build (chatml runner path) — fine as a latency smoke
model, useless for structured-output validation; use gemma for that. Spec server
command updated. Batch 4 still held pending the user's go.

## 2026-07-02 — Session close (written for relaunch)

Correction to the serving-path entry: the `format`-ignoring quirk is a known
ollama issue with MLX-backed models generally (user FYI) — GGUF models are fine,
and every pipeline model (gemma QAT) is GGUF. Not a qwen-specific or
build-specific problem.

**State at close:** bank 75 records / 49 of 547 words; both repos clean,
worktree rebased onto main; no detached runs or watchers active; ollama serving
via `/opt/homebrew/bin/ollama serve` (leave up or down freely). Fable spend this
check-in window: $1.085 — the user is checking in now,
so the $5 cap window
resets.

**Next up, in order:**

1. Relaunch batch 4 on the user's go: all currently unbanked, non-held-out
   words.in entries (regenerate the list from the bank — the old word file lives
   in the previous session's scratchpad), `--skip-banked`, detached driver +
   watcher pattern. It is the live test of judge v2: compare name-word bank rate
   against the 31% screen-bad regime v1 produced.
2. Fable checkpoint on the batch-4 banks should oversample name clues to audit
   the recalibrated gate (standing agreement: <$2 self-launch).
3. Angle-distinct depth criterion (mechanism/anchor tags exist in
   scratch/mechanism_tags.jsonl) — checkpoint 3 showed same-angle dups are the
   top quality leak in multi-clue banking.
4. Eval-panel variant: diversify the align pair's earned-? example away from
   pivot-only (back-door single-mechanism hint; audit measured pivots at ~⅓ of
   bank and rising pressure from the SILT example).
5. Mechanism tagger: tighten the dominant-mechanism instruction (it
   over-attributes frame-anchored clues to sense pivot).

Fine-tuning probe runs in its own thread (`finetune.md`); compute scheduling
between threads is user-arbitrated — keep batches modest and drain on request.

## 2026-07-02 — Background-task reaper identified

The session-long task killer is Claude Code issue #68625: the Desktop app's
WarmLifecycle manager SIGTERMs the embedded CLI's process group after ~15 min
with the session tab hidden. Explains the simultaneous batch kills, the
irregular intervals (idle timer resets on interaction; this tab hides whenever
the user works in another thread), and why `start_new_session=True` detachment
survives (new process group, out of the group-kill's reach). Open upstream, no
fix. Countermeasures: the detached-driver + watcher pattern (in use), or run
batch-heavy sessions from the standalone terminal CLI.

## 2026-07-02 — Batch 4 chunk 1: fixer flattening exposed; drained

Batch 4 launched as a chunked detached driver (`scratch/batch4_driver.py`, 493
words in 25-word chunks, per-chunk `--skip-banked`, stop-file drain). The user
drained it after chunk 1 — the machine went to the fine-tuning run — and set a
standing preference: **short runs over long slabs**; a single chunk carried
plenty of signal, and it did.

Chunk 1 (25 numbers words): 8 banked, bank at 83 — nominally the best
single-pass rate yet (32%) on the historically hardest category. The user's
read: not satisfying. The records agree, and they localize the mechanism:

- **The fixer does the flattening.** 6 of 8 banks came via the repair path; all
  six lost their `trap` (the two straight banks kept theirs). Diffs show it:
  NINE "A full lineup on a baseball field?" → "Standard baseball lineup size";
  THIRTY "A number of days in June" → "June's total". The eval round's "it
  sometimes flattens a lively draft" was the majority product here.
- **Adverse selection, not bad luck**: the confirm gate is harsh on accuracy and
  lenient on triviality; the fixer manufactures accuracy by stripping
  liveliness. The highest-throughput path therefore converges on flat,
  unimpeachable fact glosses — worst on numbers, whose count-metonymy/
  arithmetic skew satisfaction.md already names.
- **Template monoculture**: "X's total/tally" three times in eight clues —
  invisible to any per-clue judge; cross-word sibling of the angle-distinct
  leak.
- The setter's honest-calibration field flagged it: all eight self-rated `easy`
  against a medium target.

Queued in tasks.md: purge the flat chunk-1 banks after Fable verdicts; a
satisfaction criterion for the judge (judge-v2 eval protocol applies); a fixer
angle-preservation constraint; the monoculture note on the angle-distinct task.

## 2026-07-02 — Checkpoint 4 ($0.442): the reference judge has no flatness bar

Fable on the 8 chunk-1 banks (user go; cloud-only): **6A/2RV/0RJ**, verdicts
annotated on the records. The surprise is what it did NOT flag: both revises are
accuracy/anchoring complaints (ZERO — a shutout's tally is the full score, not
the zero; THIRTY — "total" unanchored), while the flat glosses the user called
out ("Standard baseball lineup size", "A decade shy of a century") were
accepted.

Implication: the verify contract (CLUE_SPEC + verify.md) carries no
satisfaction/triviality criterion, so the user's bar sits above the reference
judge's on this axis. That breaks two assumptions in the queued work:

- The chunk-1 purge can't be selected by Fable verdicts — it needs the user's
  read or a satisfaction criterion applied retroactively.
- The judge-v2 agreement protocol can't validate a satisfaction criterion
  against this reference; the criterion has to enter the verify contract itself
  (a cloud-side spec change, user-gated) or be calibrated against user-labeled
  examples.

Spend this check-in window: $0.442 of the $5 cap.

## 2026-07-02 — Satisfaction criterion built into the cloud verify contract

User-directed ($2 cap; spent $1.809 over three calls). The verify prompt now
implements the liveliness invariant CLUE_SPEC §A2 always declared but the rubric
never asked about: new criterion 6 plus a mandatory `basis` field in the output
schema (aha / elegance / resistance / prize-fact / fun, or null → revise). Cloud
runner compatibility checked: `match_verdicts` pairs by clue text and ignores
extra keys.

Iteration story, on a 20-clue set (8 chunk-1 flats + 12 Fable-accepted
regression clues):

- **v1 failed (18A/2RV)**: a bases list phrased as "name the basis that earns
  its keep" let the judge file any fact under prize-fact; only THIRTY (accuracy)
  drew a revise.
- **v2 bit (15A/5RV)**: two changes — the mandatory `basis` commitment, and
  gradient calibration inside fact mechanisms using satisfaction.md's own
  pre-chunk-1 examples ("Spinal Tap amp's top setting" vs "Twenty times two").
  NINE and NINETY revised with exactly-right reasons ("schoolchild-level fact
  stated bureaucratically"; "bare quantity relation with no pivot"); the
  THIRTEEN prize-fact control survived.
- **Held-out probe (12 unseen clues)**: all six flat confirm-fixables from chunk
  1 drew revises — SIX "chestnut-flat bare relation", FIFTEEN "bare
  unit-conversion relation" — with zero liveliness false-positives on the lively
  side. It also caught a real error the local cascade missed: ELEVEN "One short
  of a baker's dozen" is TWELVE.

Texture worth keeping:

- **"Fun" is the escape-hatch basis**: THREE "A hat trick's total" and TWO "A
  couplet's length" pass as fun. Tightening would mean teaching the prompt
  chunk-1 skeletons — deferred until independent evidence accumulates.
- **First Fable exposure for batch-2/3 banks**: 4 of 6 lively holdouts drew
  revises on OTHER axes — trap-field mismatches (DUSK, FRINGE), economy (THIRD),
  an accuracy quibble (LARRY). None cites liveliness; these criteria predate the
  change. The un-audited bank slice likely carries a real Fable revise rate — an
  argument for the checkpoint cadence, and for reading trap-field hygiene as its
  own leak.
- GOSH "Gee whiz!" (a checkpoint-3 accept) now draws "flat synonym swap" — the
  criterion applying satisfaction.md's thesaurus-entry failure mode to an
  interjection. Defensible both ways; user call at purge time.

Spend this check-in window: $2.251 of the $5 cap ($0.442 checkpoint 4 +
$1.809
here, user-directed).

## 2026-07-02 — Fun gradient closes the escape hatch ($0.785)

User-directed follow-up: the criterion had a gradient for fact-based clues but
none for "fun", so the judge granted fun to anything pleasant. Added the
parallel calibration — fun is humor or surprise in the surface itself ("Heads
down!" for DUCK); recognition is not fun (fusing stock associations, "Old enough
to order a drink" for TWENTYONE); plus a pre-commitment question before writing
`basis: "fun"`.

Same 20-clue set, side by side with the previous run (15A/5RV → **9A/11RV**):

- All five fun-basis chunk-1 accepts flipped to revise with the right reasoning
  — THREE "stock fact plainly stated", SEVEN "fuses two stock associations",
  SIXTEEN "breezy register", plus ZERO and TWO. **All 8 chunk-1 banks now draw
  revises**, matching the user's read of the set.
- THIRTEEN held accept and relabeled fun → prize-fact (the desired behavior:
  basis moves, verdict doesn't). GASP kept fun honestly; CHECK/GROSS/MURMUR
  relabeled without verdict changes.
- One new regression flip, off-axis: MELODY "Whistleable earworm" revised as
  unmarked definition-by-example (an earworm is a kind of melody — spec wants a
  ?). Defensible; noted on #judge-satisfaction as a watch item, with the general
  strictness rise.

Spend this check-in window: $3.036 of the $5 cap.

## 2026-07-02 — Purge; fixer and local-judge prompts aligned to the bar

**Bank purged 83 → 75**: all 8 chunk-1 records removed (every one draws a revise
under the final verify contract, matching the user's read). Git history and the
committed eval sets preserve them as labeled negatives.

**Local-judge root cause found**: the judge prompt already had a liveliness rule
and a flat-count fixable example (SEVEN, days-in-week) — but its FIRST
calibration example taught "Innings in a standard ballgame" -> NINE: bankable,
"metonymic count clues are fine." Near-verbatim the clue chunk 1 banked; two
near-identical count facts calibrated to opposite verdicts, and the permissive
one won. Same lesson as the cloud iteration: blessing a mechanism without a
gradient blesses its flat end.

Prompt changes (validation runs pending, machine on the fine-tune):

- **Judge**: liveliness bullet now carries both gradients (fact and
  fun/stock-association); the NINE example became a graded pair (ELEVEN Spinal
  Tap bankable / NINE innings fixable — "liveliness grades the fact, not the
  mechanism"); TWENTYONE stock-association example added, mirroring the cloud
  contract's.
- **Fixer**: the draft's angle is named as the thing to preserve — repair around
  it, carry it into the `trap` field, and when the critique names flatness,
  produce a fresh angle, not a rephrase.

Queued validation (local runs, user-gated): 26B/31B agreement eval on the 32
Fable-labeled clues; fixer replay of chunk-1's critiques checking trap survival;
then batch-4 chunk 2 as the integration test of all three fixes.

## 2026-07-02 — Session close (written for relaunch)

**State at close:** bank 75 (chunk-1 purge done); worktree clean; `main` and
`local-ceiling` both pushed through a913b59; commits after that (purge + prompt
alignments, reference-verdicts artifact) are local to `local-ceiling` — push
both branches with the next batch. Batch 4 stands drained after chunk 1 (19
chunks remain; relaunch = detached `python3 cluegen/scratch/batch4_driver.py`,
resumes via `--skip-banked`). Local machine is on the fine-tuning thread. Fable
spend this check-in window: $3.036 of $5.

**Standing gate (new):** tell the user before running ANY local or cloud batch.
Prompt/code edits and file surgery proceed freely.

**Pending work:** tracked in tasks.md — the single source for the queue; nothing
pending lives only in this log.

## 2026-07-02 — Agreement eval: flats die, but the local judge overshot

The 32 reference clues re-judged through the production cascade (26B screen →
31B confirm; `scratch/agreement_eval.py`, results in
`scratch/logs/agreement_eval_*.jsonl`).

**Kill side works:** 20/21 Fable revises die locally — every chunk-1 flat among
them. The one leak: FOURTEEN "A score, slightly diminished" (bare relation)
banked clean through both stages.

**Keep side collapsed:** only 2/11 Fable accepts stay bankable (GROSS, POTS).
The recalibrated judge kills THIRTEEN "A number often skipped in elevators" —
the prize-fact control — with "relies on a common piece of trivia rather than a
clever pivot," directly contradicting its own ELEVEN calibration example (a
remark-worthy fact needs no pivot). Genuine ahas die the same way: CHECK
"Threaten the king" called "dictionary-flat game mechanic," DAISY
"Petal-puller's target?" called "recognition dressed up as a riddle." The
stock-association/recognition language generalized into "anything commonly known
is flat" — the judge now demands a pivot on top of every basis. Six of nine
false kills happen at the 26B screen.

**Watch item:** three screen verdicts (AMBER, MARCH, MURMUR) returned an empty
`analysis` string with verdict fixable — the doubt-rule may be absorbing
degenerate generations; schema-valid but reasoning-free.

Verdict on the prompt alignment: precision fixed, recall broken. The liveliness
bullet needs the positive side of the gradient stated as strongly as the
negative — familiarity of the domain doesn't flatten a clue; flatness is the
absence of pivot/surprise/specificity, not the presence of common knowledge.
Next iteration is a prompt edit (free) plus an eval re-run (local batch,
user-gated).

## 2026-07-02 — Compute-lease protocol: threads coordinate contention themselves

Today's memory-pressure collision (18 GB ollama + 11 GB MLX, the two threads
launching within minutes of each other) prompted a user-designed coordination
protocol, decided via a question round: exclusive lease, FIFO waiting, and — the
user's addition — **measured idle, not trusted state**: acquisition and
stale-lease breaking both require the machine to measure idle (ollama `/api/ps`
empty, kernel memory-pressure level normal), so a dead holder whose memory is
still wired blocks rather than getting stomped. Release unloads ollama models,
so the next holder starts from measured idle.

Implementation: `cluegen/local/compute_lease.py` (in-repo — the user's placement
call: it's project infrastructure while this is the only model-running project
on the machine; full protocol in its docstring), lease file at
`/Users/Shared/models/.compute-lease.json`. All four safety paths tested live:
refuse-while-held, refuse-wrong-holder, refuse-stale-but-busy (exit 2, lease
left for inspection), break-stale-only-when-idle.

Gate amendment (user, 2026-07-02): with the lease held, local runs under ~1 hour
each self-serve — no per-batch ping. Multi-hour local runs and all cloud
spending still get user notice first. Recorded in the shared memory store; the
fine-tune thread needs a one-line relay from the user to adopt it.

## 2026-07-02 — Judge iterations 1–2: prize-fact fixed; prompt tuning hits its noise floor

Three agreement-eval runs, two prompt iterations
(`scratch/logs/agreement_eval_*.jsonl`):

| iteration                           | keeps (Fable accepts bankable) | kills (revises non-bankable) |
| ----------------------------------- | ------------------------------ | ---------------------------- |
| baseline (first alignment)          | 2/11                           | 20/21                        |
| 1: positive gradient side           | 4/11                           | 20/21                        |
| 2: named-flaw doubt rule, ROOK pair | 5/11                           | 18/21                        |

Iteration 2's win: THIRTEEN "A number often skipped in elevators" — the
prize-fact control — now banks at both stages. Its costs: ZED and MELODY leak
(both soft Fable revises — an economy nit and the ?-convention call, not
liveliness), and FOURTEEN flip-flopped across the three runs (banked / died /
banked at temp 0.2) — single-sample deltas of ±1–2 on this 32-clue set are
within run noise, so the instrument can't resolve further prompt gains.

What persists: **familiar-domain blindness**. CHECK "Threaten the king",
CENTURY, GASP, MARCH, MURMUR all still die as "dictionary-flat / stock
association" — the judge grades the topic's familiarity, not the leap, and the
ROOK calibration pair didn't transfer. This looks like a capability limit of the
26B/31B cascade on taste distinctions, not a wording problem.

Where that leaves the cascade: precision on flats is solid (every chunk-1 and
holdout flat dies in all three runs); recall on good clues is ~half. Recall loss
costs throughput (fewer banks per run), not bank quality. The honest next
instrument is batch-4 chunk 2: measure the real bank rate under the new judge

- fixer and let the user judge the tradeoff on production numbers.

## 2026-07-03 — Iterations 3–6, probes, and the confirm redesign

The "capability limit" call above was wrong (user pushback, twice vindicated).
The keep side recovered 5/11 → 10/11 across iterations 3–5 once the fixes went
structural rather than wordsmithing:

- **Iteration 3 — basis commitment ported as mechanism** (required `basis` enum
  in the judge schema + solver-simulation protocol + basis–verdict coupling):
  the whole familiar-domain aha cluster banked (CHECK "Threaten the king", MARCH
  "Step in time?", CENTURY "Batsman's milestone", DAISY "Petal-puller's
  target?", AMBER "Prehistoric time capsule?"). Keeps 5/11 → 8/11.
- **Iterations 4–5 — diagnosed clusters, not adjectives**: modifier honesty (ONE
  "Sole digit", FOURTEEN "A score, slightly diminished"), padding-behind- charm,
  fun/elegance-in-imagery examples (DUCK, SCREECH, SOUTHWARD), foreign-
  homograph rule for names (FELIX). Keeps 9/11 then 10/11.
- **Fresh validation** (17 checkpoint-labeled bank clues, never tuned against):
  the core transferred — unseen ahas banked, flats died; 8/10 of its revises are
  independence/tag/trap axes a per-clue judge structurally can't see.
- **Iteration 6 regressions revealed the instrument's limit**: ~10 borderlines
  flip run-to-run at temp 0.2; single-run deltas at the margin are sampling
  noise. (A temp-0 determinism test was started and killed — wrong instrument:
  user's calibration point taken.)

**Variance probes** (12 clues × 4 samples/stage) replaced single-sample flips
with distributions and rewrote the cascade's story:

- With the shared prompt the 26B screen is the only real gate — flats die 4:0,
  strong ahas bank 4:0, true borderlines split. The 31B confirm banks ~90% of
  accepts AND revises alike, at temp 0.2 and 1.0 both. Every historical "confirm
  kill" was a low-probability draw.
- Temperature: 0.2 was convention, never measured. At 1.0 the screen improves on
  stable-wrongs with no control regressions — live candidate, decide with the
  49-clue eval.
- **Confirm v1 (role suffix) failed**: the shared solver-simulation user turn
  steered analysis to taste; verification never executed. **v2 (own system
  prompt + own verification protocol; no basis coupling)** works: ONE, FOURTEEN,
  FELIX all die 0:4 (mostly `bad`), zero false kills on accepts. Residuals:
  padding (ZED "That last character, overseas") bites nowhere; WYE "Forked
  path?" dies on strict sense-ownership (letter-name outlier — it's in words.in
  as the spelled-out letter, lines 533–547 block).
- **Taste-at-31B tested and rejected** (user hypothesis: the stronger model
  should judge taste better): screen taste prompt minus the coupling license
  still banks everything (SEVEN "Lucky prime" 2:2 at best). The 31B's leniency
  is core behavior, not a license artifact; verdict-expressed taste
  discrimination lives at the 26B, as fitted by the iteration campaign.

**Cascade as redesigned**: screen = 26B, taste + craft (iterated prompt);
confirm = 31B, v2 precision verification (own protocol). Known gaps: padding (no
stage catches it), GASP-class contested fun (screen kills what Fable calls fun),
screen split-rates on imagery accepts. Next validation (machine- gated): the
49-clue agreement eval under the full new cascade; then the fixer replay; then
batch-4 chunk 2. Machine handed to the fine-tune thread 2026-07-03 ~01:30; no
further runs without the user's go.

## 2026-07-03 — Autonomous iteration window: protocol

User grant: ~5–10 hours of self-directed iteration once the fine-tune thread's
compute needs are met. Goal: a mix of judge quality, setter quality, and
throughput — steer by apparent leverage, no forced bouncing. Budgets: $10 of
Fable checkpoints over the window; up to 10 tries per task, stopping earlier on
diminishing returns; every batch ≤45 min with a small-first validation ladder.
Chat gets an update every time new data lands.

**Validation ladder** — every idea climbs, none skips:

- Rung 0 — execution smoke: one clue/word, changed stage only, everything else
  replayed. Confirms the change runs and the output shape is right; carries NO
  efficacy signal.
- Rung 1 — targeted probe: the relevant slice (e.g. variance-probe 12, a
  category subset), changed stage only, K samples where verdict stability
  matters.
- Rung 2 — full battery, replaying unchanged stages; ≤45 min. Reserved for
  adoption decisions.

**Adoption methodology** (adversarially refined once, per user direction):

1. Pre-register in the ledger before each run: hypothesis, target metric, guard
   metrics, expected direction. (Counters forking-paths metric shopping.)
2. Tuning set = the 32-clue satisfaction reference; holdout = the 17
   fresh-validation clues, consulted only at adoption decisions. (The reject
   bank adds no independent signal — all 14 records are a subset of the tuning
   set, `source: satisfaction-reference`. This counters holdout leakage across
   20+ ideas; a mid-window Fable-labeled fresh set from the $10 budget becomes
   the true test for the final stack.)
3. Adopt when the target improves with a mechanism-consistent causal story —
   flipped clues' analyses show the change doing what it was designed to do —
   and guards hold on tuning + holdout. A bare count delta of ±1 clue is noise
   at N=49. (Counters small-N adoption.)
4. Precision guard is hard: zero new stable false-banks on tuning or holdout
   revises; verdict stability checked at K≥3 on any flipped clue. Recall gains
   are the usual win condition; throughput ideas instead need quality
   non-regression plus a meaningful compute drop.
5. Every ~5 adoptions, or before switching idea families: re-run the full
   battery on the adopted stack against the WINDOW-START baseline, not the
   previous step. (Counters ratchet drift and interaction effects.)

**Compute courtesy**: lease held per run-series; between runs, check `status`
for the fine-tune thread's I'm-waiting note (new advisory-waiter mechanism,
c562f2b) and yield on sight. Stage-1 training finished 08:36 today; machine
measured idle at window start.

Ledger: `scratch/window_ledger.md` (one pre-registered line per idea, outcome
appended). Idea list seeded from tasks.md queue — cascade roles (#taste-31b
variants, inversion, 26B-only, split-routing), wording gaps (padding, GASP fun),
temperatures, fixer replay + variants, category ceilings (numbers,
letter-names), eval infrastructure (battery harness, replay cache, fresh Fable
labels), and code-only fillers (reject-bank wiring, tagger, template dedup).
