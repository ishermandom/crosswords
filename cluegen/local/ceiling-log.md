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

**What changed:** v1 scaffold initially produced no drafts — the drafting
turn, with thinking on, exhausted the 8k context window in reasoning before
emitting content, and the extract turn then invented a clue with nothing to
select from. Fixes: `num_ctx` 8192 → 16384 in the shared harness; drafting
turn runs `think=False`. Post-fix timing: angle turn ~260 s (~5k thinking
tokens), drafts 8 s, extract 3 s — turn 1 is ~95% of wall time.

**Measurements (DUCK, hard, gemma4:26b-qat):** 4 drafts across genuinely
distinct senses — "Avoid a low blow?" (selected), "Zero at the crease?"
(cricket duck), "A heavy-duty canvas?" (duck cloth), "Make a quick exit?".

**Interpretation (in-session read vs CLUE_SPEC Part A):** angle variety is a
real strength already. Craft is rough: the selected clue's `?` is not
clearly earned (straightish verb definition), the trap rationale is stated
backwards (claims the answer is the waterfowl), and one draft in four fails
the substitution test (DUCK ≠ "make a quick exit"; DUCK OUT does). Roughly:
sense-finding good, editorial discipline weak — consistent with the cloud
pipeline's division of labor, where the verify pass catches exactly these.

**Next:** breadth first — 5 more iteration words at this fixed config
(DRAFT/IRIS/TEE hard, MARK/TWELVE medium), then v2 prompts targeting
?-honesty, trap articulation, and substitution rigor; separately test
`think=False` on the angle turn as the dominant speed lever.

---

## 2026-07-01 — v1 baseline (in-session grades) and fast-angles adoption

**What changed:** angle turn now runs think=False by default for iteration
(`--fast-angles`): 19 s/word vs 272 s, with angle breadth preserved (DUCK
A/B: same senses found, labels slightly noisier). Probe imports its lib
relative to the file — PYTHONPATH carries the main repo root, which was
silently loading the main checkout's harness (and writing logs there).

**Measurements (v1, gemma4:26b-qat, in-session grades vs CLUE_SPEC A):**

| Word (target) | Clue | Grade |
| --- | --- | --- |
| IRIS (hard) | Messenger from the clouds? | accept |
| TEE (hard) | Something to use with a cup? | borderline (trap: TEA fits at 3 letters; "use with" loose) |
| DUCK (hard) | An easy target? | revise (idiom fragment: SITTING duck) |
| MARK (medium) | One who is often under scrutiny? | revise (right angle, vague surface) |
| TWELVE (medium) | Standard in a courtroom? | revise (? apologizes for loose phrasing) |
| DRAFT (hard) | One who might be called to service? | reject (clues the draftee, not DRAFT) |

≈1.5/6 accept vs the cloud bank's ~90%. Angle discovery is consistently
strong; the losses are all editorial discipline, in three recurring shapes:
referent mismatch ("One who…" for a non-person answer), idiom fragments
(clue works only for a longer phrase containing the answer), and
substitution tests asserted but never performed. Trap rationales are
routinely confused or backwards.

**Quota decision:** deferring the first cloud-verify checkpoint until v2
stabilizes; when it runs, the same capped run will grade both the archived
v1 outputs and v2's, so the curve's origin is measured by the same judge at
no extra checkpoint cost.

**Next:** v2 prompts targeting exactly the three failure shapes — a
referent/idiom-fragment rule in the drafting turn, and an operational
substitution test in the editor turn (write the sentence, perform the
substitution, then judge). Structure unchanged for comparability.

---

## 2026-07-01 — v2: referent rules + performed substitution test

**Measurements (same 6 words/difficulties, in-session grades):** ≈3.5/6
accept vs v1's ≈1.5/6. MARK "One of the four Gospels" (trap: Luke — 4
letters, genuinely deadly), TWELVE "Standard chromatic scale count?", DUCK
"Dip out of sight" all accept; TEE "A small support for a long drive?"
borderline-accept; DRAFT "A sudden chill from an open window?" revise
(referent fixed, ? unearned on a straight definition); IRIS "Colorful
garden visitor?" reject (a planted flower is not a visitor — accuracy).

**Interpretation:** both targeted v1 failure shapes eliminated (referent
mismatch 3/6 → 0, idiom fragments 2/6 → 0) — the hard rules + performed
substitution test transfer cleanly on this model. Residual profile: trap
rationales inverted or confused in 5/6 (the model sets traps it cannot
describe; the cloud judge checks that the stated trap functions, so this
directly costs checkpoint accepts); ? discipline still weak on straight
definitions of secondary senses; one literal-accuracy slip. Difficulty
self-labels drift high (straight definitions tagged hard).

**Next:** v3 targeting trap articulation (solver-perspective template:
first reading → wrong answer in caps → escape), a no-? rule for straight
definitions of any sense, and a literal-accuracy check in the editor turn.
After v3: 26B→31B transfer check on 2–3 words, then the first cloud-verify
checkpoint over archived v1+v2+v3 outputs in one capped run.

---

## 2026-07-01 — v3: regression with a lesson; 31B transfer check passes

**Measurements (26B, same 6 words, in-session grades):** ≈2.5/6, down from
v2's ≈3.5/6. Trap articulation fixed (concrete wrong answers in caps across
the board: DODGE, COLD, SHUTTER); but MARK "An editor's notation" (easy,
dull) and TWELVE "Number of months in a year" (inert) show the failure:
the conjunction of v3's discipline rules pushed selection into the timid
corner. The honest-difficulty rule, meant as calibration, acted as an
incentive to downshift to safe straight definitions instead of crafting
livelier target-difficulty clues. Classic multi-objective prompt tension:
each rule fixed its target; together they over-tightened.

**31B transfer check (DUCK, MARK, v3 prompts):** directionally aligned —
same angle families, same conservative tilt, marginally cleaner surfaces
("Avoid a blow" vs 26B's "Avoid the blow!"). No divergent failure modes on
this sample; 26B stays the iteration model. 31B timing: ~5 tok/s, ~3.5–4.5
min/word at the fast config. Checkpoint-sizing note: a 10-word 31B batch is
~45 min of sustained decode on the fanless Air — throttle territory; size
or split checkpoint runs accordingly.

**Next:** v4 rebalances — keep v3's checks, restore ambition: drafting turn
gains target-difficulty pressure (medium prefers a less-first sense over
the primary straight definition; dictionary-flat is a failure at any
difficulty) and the extract turn selects the KEEP closest to the target,
preferring the livelier of equals, never defaulting to the safest.

---

## 2026-07-01 — v4: ambition restored, surfaces slipped; seesaw identified

**Measurements (26B, same 6 words, in-session grades):** ≈2.5–3/6. TEE
"Small support for a long shot?" is the campaign's best clue yet (long-shot
gambling misdirect, natural surface, earned ?); IRIS "Messenger of the
rainbow?" accepts. But MARK "Hit to be sought?" and TWELVE "That many
semitones in an octave" have assembled, inhuman surfaces, and DUCK "A zero
in cricket?" is obscure-not-twisted at hard for an American solver.

**Interpretation:** v2 ≈3.5/6 remains the peak. v3 and v4 form a seesaw:
each rule set fixes its target failure and induces the opposite one
(safe-dull ↔ ambitious-awkward). Wording-level iteration is showing
plateau behavior around ~3/6 in-session vs the cloud's ~5.4/6.

**Next:** v5 = principled recombination — v2's balance plus only the
isolated-good components: v3's trap template, a surface-naturalness editor
check (would a human write this?), and hard-means-twisted-not-obscure as an
editor check. If v5 ≤ v2, wording iteration has plateaued: run the first
cloud-verify checkpoint over the archived v1–v5 curve (one capped run) and
take the plateau assessment to the user check-in.
