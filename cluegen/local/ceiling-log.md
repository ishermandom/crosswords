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

6 unseen words, full cascade, one retry, 10.5 min wall clock (caffeinated —
same workload shape that "took 75 min" pre-diagnosis; sleep confirmed as the
J4 culprit). Banked 1/6.

| word  | attempt 1              | verdict            | attempt 2               | verdict | my grade of best        |
| ----- | ---------------------- | ------------------ | ----------------------- | ------- | ----------------------- |
| SCORE | "Make a mark?"         | screen ok, confirm fixable (? unearned) | "Film's background music" | fixable (flat) | borderline; a2 fine easy |
| DAISY | "Petal-puller's target?" | BANKED           | —                       | —       | genuinely good          |
| GRANT | "Allow or bestow?"     | fixable (? unearned) | "Provide or permit?"  | fixable | fair drop; trivial fix would salvage |
| CHECK | "Bill at a bistro"     | screen ok, confirm fixable (flat) | "Diner's final tally" | fixable (flat) | a1 arguably bankable easy |
| GASP  | "A sudden intake in horror" | fixable       | "Sharp intake at a shock?" | fixable | fair drops, both weak |
| AMBER | "Baltic treasure"      | screen ok, confirm fixable | "Ancient resinous gem" | fixable | a1 a real recall loss — good metonymy |

**Interpretation.** Precision holds (the one bank is the batch's one lively
clue). The drops split: ~2 recall losses (AMBER a1 clearly; SCORE/CHECK a1 as
easy fills), the rest genuinely dictionary-flat. The binding constraint is now
**setter liveliness**, not judge recall — most drafts are accurate but flat,
and the judge's "lacks liveliness" complaint is usually correct. Secondary bug:
the retry turn ignores the judge's stated fix (GRANT's retry kept the unearned
`?` the judge had named).

**Next iteration (one variable at a time):**

1. v8 setter — liveliness pressure in the drafts and edit turns; make the
   retry directive (apply the judge's named fix verbatim). Rerun same 6 words.
2. Then multi-candidate (judge setter's top 2) if bank rate still low.

## v8 setter (liveliness pressure) — same 6 words (2026-07-01)

Banked 1/6 again, but the failure mode moved. Surfaces are no longer
dictionary-flat: AMBER "Sunlight captured in stone?", DAISY "Morning's eye?",
GASP "Sharp intake after a jump scare?", and the bank: CHECK "Threaten the
king" (chess angle — vivid, economical, no `?` needed; screen and confirm both
bankable at first attempt).

Drop reasons shifted from "lacks liveliness" to `?` discipline and looseness:
GASP a1 and SCORE a2 are straight secondary-sense definitions wearing an
unearned `?` — exactly the shape the new mechanical tidy (user suggestion)
converts to a free strip-and-re-judge. AMBER a2 "Ancient resin's golden glow"
clues the glow, not the resin — confirm's `bad` is correct (referent
mismatch). DAISY a1 "Morning's eye?" flirts with the day's-eye etymology but
neither setter nor judge articulated it.

Calibration note (user exchange): my "clear recall loss" grade on batch 1's
AMBER "Baltic treasure" assumed Baltic→amber is common solver knowledge; the
user didn't have it. Trivia-dependent metonymy grades softer than I credited —
in-session grades have error bars too, and the confirm's doubt-rule looks
better calibrated on that example than I did.

**Next:** same 6 words with the tidy active (isolates the tidy as the
variable). Then multi-candidate if bank rate still lags.

## Tidy-active batch + the variance insight (2026-07-01)

Same 6 words, tidy active. Banked 1/6: DAISY "Subject of a petal-plucking
game?" (attempt 2, both stages). **Tidy verdict: fired 4×, converted 0.** In
every case the stripped clue re-judged as still-fixable — the `?` complaint
usually rides on an underlying flatness or looseness, so removing the mark
exposes rather than cures it. The tidy stays (it costs nothing and will
occasionally rescue a clean case), but it is not the recall lever.

**The real finding is run-to-run variance.** Three runs, same words, same
prompts (runs 2 and 3 identical code): CHECK banked in run 2, dropped in
run 3; DAISY banked in runs 1 and 3, dropped in run 2. Per-word bank
probability looks like ~20–35% per run at temp 1.0, and "1/6 per batch" is
sampling noise, not a ceiling. Zero-marginal-cost implication: repeated
passes with `--skip-banked` (added) accumulate coverage — best-of-N at the
run level, judge untouched, precision preserved.

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
Banked: ZED "That last character, overseas" (pass 1, attempt 1). Everything
else dropped — 22 word-runs, 1 bank (≈5% vs the fresh set's 23%).

**Why the gap (analysis only — held-out failures do not feed prompt work):**

- **Category difficulty.** Three of eight are number words. The local setter's
  fallback for numbers is arithmetic ("Twice six", "One less than twenty?") —
  flat by nature, and the judge correctly reads it as flat.
- **Craft-under-pressure, not angle discovery.** Same-word comparison against
  the cloud bank: the local setter FOUND Fable's angles — Lent for FORTY
  (Fable: "Keep yen for Lent's duration in days"), the 19th hole for NINETEEN
  (Fable: "Hole number where the drinks are?"), baker's dozen for DOZEN — but
  fumbled execution: "The 19th hole's destination?" clues the clubhouse, not
  the number. Fable lands the referent on the same angle; the 26B doesn't.
- **Plausible recall losses worth auditing:** "A score doubled?" (FORTY),
  "Baker's count?" (DOZEN), "Runner-up's rank?" (SECOND), "Royal residence or
  tennis arena" (COURT). These go into the checkpoint 2 payload so Fable
  measures the local judge's error in BOTH directions on unseen words.

**Reading:** the fresh-set 23%/word-run was partly category luck (vivid
concrete nouns). The local ceiling is category-dependent: strong on
polysemous/concrete words, weak on numbers — exactly the words where the
cloud bank is already deepest, which is a happy complementarity.

**Next:** harvest never-extracted KEEP drafts from all pipeline logs through
the cascade (production under the bank-shape goal + measures whether draft
pools are underexploited), then propose checkpoint 2.

## KEEP-pool harvest: 1/7 (2026-07-02)

`scratch/harvest_keeps.py` re-judged every never-extracted KEEP draft in the
pipeline logs (7 clean candidates after filtering setter chatter). Banked:
CHECK "Curb an impulse". Reading: draft pools are only mildly underexploited
(~14% of runner-up KEEPs bank), so full reruns' fresh-brainstorm cost is
earning its keep — but the harvest is nearly free and runs as a standard
post-batch sweep under the bank-shape goal.

Bank: 30 records; 8 locally-judged pipeline banks across 8 distinct words'
clues (DAISY ×2, CHECK ×2, GRANT, GASP, AMBER, ZED).

**Checkpoint 2 payload finalized:** 8 pipeline-banked + 4 earmarked
judge-rejections = 12 clues. Estimate ~$0.80 at checkpoint-1 unit cost
($2.65/40 clues); cap $1.50. Awaiting user go.

## Checkpoint 2: local judge validated on the metric of record (2026-07-02)

Two verify calls, $0.778 total (cap was $1.50). Results log:
`scratch/logs/checkpoint_2026-07-02T00-16-33.jsonl`.

**Pipeline-banked clues: 7 accept / 1 revise / 0 reject.** The revise is
DAISY's second clue — Fable flags it as a paraphrase of the first DAISY
clue's angle, not a craft failure. As clue text, effectively 8/8. The local
cascade's "bankable" maps to Fable-accept at ~0.9 precision on words the
prompts never saw.

**Rejection audit: 2 accept / 2 revise.** FORTY "A score doubled?" and COURT
"Royal residence or tennis arena" were genuine recall losses — both now
banked verbatim as Fable-accepted. On DOZEN "Baker's count?" the local judge
beat my in-session grade (a baker's count is THIRTEEN — inaccurate
definition); SECOND's trap "doesn't function". The conservative doubt-rule
earns its keep in both directions.

**Lessons recorded:** (a) depth-goal clues per word should eventually be
angle-distinct, not just text-distinct — deferred to a later pass by user
direction, don't over-invest now; (b) in-session grades have error bars in
both directions (Baltic treasure: too generous on trivia metonymy; Baker's
count: missed an inaccuracy).

Bank: 32 records (8 local-cascade banks with Fable verdicts tagged in
provenance, 2 audit rescues).

**Next direction (user, 2026-07-02): throughput.** Target an order of
magnitude better than ~7–8 min per banked clue; anatomize the cost and
attack the 23%/5% per-run bank rates. Brainstorm with the user before
experiments.
