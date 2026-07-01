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
