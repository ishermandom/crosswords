# Autonomous window ledger — 2026-07-03

Protocol: ceiling-log.md (2026-07-03 "Autonomous iteration window"). One section
per idea: pre-registration first (hypothesis, target, guards), outcome entries
appended after each run, newest last. The status board holds only the current
status; the narrative lives in the sections.

## Status board

| #   | idea                         | status             |
| --- | ---------------------------- | ------------------ |
| 1   | battery harness              | BUILT              |
| 2   | window-start baseline        | DONE               |
| 3   | fresh labels, kill side      | DONE               |
| 4   | reject-bank wiring           | ADOPTED            |
| 5   | re-judge the 4 recall losses | DONE               |
| 6   | padding: deletion-test       | SUPERSEDED (by 10) |
| 7   | fun gradient                 | PARKED             |
| 8   | caffeinate detached runs     | ADOPTED            |
| 9   | confirm v3                   | REJECTED           |
| 10  | multi-turn confirm           | ADOPTED-IN-BATTERY |
| 11  | screen non-pinning removal   | QUEUED             |

## Idea 1 — battery harness (BUILT)

Infrastructure, no model verdict at stake. One command → keeps/kills table over
tuning (32) + holdout (17), per-call replay cache. Found: reject bank ⊂ tuning
set (no independent signal).

## Idea 2 — window-start baseline (DONE)

Full battery on the current cascade (post-redesign screen + confirm v2), K=1.
All later rung-2 reads compare here.

**Batch A (tuning + losses):** accepts held 4/11 (discount GASP per user: 4/10),
revises killed 18/21. Stage attribution — screen kills accepts CENTURY
"Batsman's milestone", MURMUR "Low hum of a restless crowd" (+GASP, discounted);
confirm kills WYE "Forked path?", DAISY "Petal-puller's target?", CHECK
"Threaten the king", AMBER "Prehistoric time capsule?". False banks: LARRY "Not
quite Lawrence?", ZED "That last character, overseas" (padding, expected), ZERO
"A shutout's tally". Losses set: FOURTEEN "Score minus six" recovered by the
redesign (banks); FIFTY dies screen-bad, NIL screen-fixable, NINE confirm-bad —
3 live false kills. Model time ~27 min; wall 141.6 min (see idea 8).

**Batch B (holdout + rejects + funcal):** holdout accepts held 2/7 (recall
collapse replicates on never-tuned data; screen kills GRANT "Academic
windfall?", CHECK "Curb an impulse", STOCK "Simmering base for a stew"; confirm
kills DAISY "Sun-watcher?", ROBIN "Boy Wonder?"), revises killed 8/10 (false
banks: SCORE "Leave a notch", ROBIN "Sidekick to a Dark Knight?"). Rejects
killed 17/18 — 14 die at screen (screen is a strong true-reject gate); false
bank THOUSAND "M-shaped Roman numeral's value". Full-battery v2 agreement ≈
57/81.

## Idea 3 — fresh labels, kill side (DONE)

Fable-label the 22 unlabeled chunk-1 kills (`fresh_label_input.jsonl`, version
fresh-kill). Purpose: recall-loss audit — every Fable-accept among them is a
cascade recall loss with stage attribution. DIAGNOSTIC set (tuning allowed).
Caveat: numbers-slanted (chunk 1). The 24 fresh-bank entries stay UNLABELED
until end-of-window → fully sealed precision test.

**Outcome:** 4A/18RV/0RJ, $0.704 ($9.30 left). 18 true kills → reject bank. 4
recall losses: FIFTY "The denomination on a red bill" (screen kill; Fable
prize-fact), NIL "Nothing on the scoreboard" (confirm; elegance), NINE "A full
lineup on a baseball field?" (confirm; aha), FOURTEEN "Score minus six"
(confirm; aha). All four were killed by the PRE-redesign cascade — see idea 5.

## Idea 4 — reject-bank wiring (ADOPTED)

Code-only: `reject_bank_append.py`, checkpoint results → reject_bank (Fable
revise/reject on unbanked candidates, dedupe, disjoint-from-bank invariant,
banked hits print as purge candidates). First live run appended the 18 confirmed
kills; bank 14 → 32. Battery gains a `rejects` set (the 18 non-tuning-subset
entries) as an independent precision guard.

## Idea 5 — re-judge the 4 recall losses (DONE)

Run the 4 Fable-accepted kills through today's cascade via the battery `losses`
set. Hypothesis: some were fixed by the redesign (chunk 1 predates it). Outcome
(baseline batch A): FOURTEEN recovered; FIFTY (screen-bad), NIL
(screen-fixable), NINE (confirm-bad) stayed live false-kill targets, each with a
Fable basis to aim at (prize-fact, elegance, aha).

## Idea 6 — padding: deletion-test confirm (SUPERSEDED by idea 10)

Hypothesis: "name any padding" invites a gestalt read (smooth surface → "None");
Fable's economy standard is per-word deletion (ZED: "'That' is padding — 'Last
character, overseas' is tighter"). Patch `variants/padding_v1.py`:
delete-each-word test, plain-article carve-out, invented EVEREST example.

**Rung-0/1:** ZED dies at confirm — first stage ever to catch it — but the
plain-article carve-out FAILED: NINE "A full lineup on a baseball field?"
killed. GROSS "Stomach-turning total?" also flipped (unstable across all patches
— K=3 candidate). Padding-v2 wording drafted conceptually, then superseded:
economy became its own turn in idea 10's decomposition, and the adopted config
kills ZED via its substitution turn with economy advisory.

## Idea 7 — fun gradient (PARKED)

Hypothesis: the screen extends the stock-association kill to surfaces whose
vividness is one precise cultural moment — GASP "Reaction to a jump scare" went
8/8 screen-fixable citing "recognition of a common experience". With N=1 labeled
GASP, tuning on it = memorization, so Fable generated graded pairs ($0.32,
`fun_calibration_verdicts.jsonl`, battery set `funcal`): evoked lived moment
(SNOOZE "Button smacked at 6:00, 6:09, and 6:18") vs props/frames ("Alarm clock
button"). Patch `variants/fun_v1.py` written but PARKED unrun: the decision
probe (funcal at v2 baseline) showed the screen banks 4/5 vivid accepts (only
LATTE "Order handed over with an unrequested foam heart" dies at screen) and
kills 5/5 flat revises — the screen's fun line is fine; SNOOZE/KARAOKE die at
the CONFIRM (precision literalism, idea 10's territory).

## Idea 8 — caffeinate detached runs (ADOPTED)

Batch A's 6 uniform ~1000s stalls = macOS maintenance sleep (pmset log matches
call-for-call; 45 s dark-wakes every ~17 min; full wake on user HID exactly when
confirms ran clean). Fix: every detached driver wraps in `caffeinate -is`.
Recipe updated in compute_lease.py docstring + shared detached-runs memory.
Reconfirmed 2026-07-04: an in-session non-caffeinate rerun stalled to 29 min for
40 s of model time — even "quick" model runs go detached+caffeinate.

## Idea 9 — confirm v3: ?-license + clean substitution (REJECTED)

Hypothesis: v2 prosecutes marked metaphor/metonymy as substitution failure
(DAISY/AMBER analyses acknowledge the ? then kill the stretch; CHECK's
substitution doubled "the king" into wreckage and called it a referent shift).
Patch `variants/confirm_v3.py`: ? licenses the stretch it marks (invented CAVE
example; EELS counterweight stays); substitute where the answer stands alone.

**Rung-0:** 5/5 targets flip bankable (WYE, DAISY "Petal-puller's target?",
CHECK "Threaten the king", AMBER, NINE "A full lineup on a baseball field?").

**Rung-1/2:** rubber stamp. v2 killed DUSK/THIRD/SIXTEEN; v3 banks all (kills
1/6, and that one is the cached screen's); holdout revises 8/10 → 6/10; rejects
17 → 16. Cache ablation: v3 still NAMES the flaws then banks anyway — the
license text broke flaw→verdict coupling globally (DUSK/SIXTEEN carry no ?).
Keeper: the clean-substitution procedure (the CHECK "threaten the king the black
king" fix). Wording-level v4 parked in favor of idea 10.

## Idea 10 — multi-turn confirm, code-side verdict (ADOPTED-IN-BATTERY)

**Pre-registration (user-directed, 2026-07-04):** short focused turns, one check
each — (1) substitution `{shift, shift_is_the_marked_stretch}`, (2) literal
truth `{failing_qualifiers}`, (3) economy `{padding_words}` (articles excluded),
(4) sense ownership `{is_english_sense}` — fresh conversation per turn, VERDICT
COMPUTED BY CODE from the fields. Structurally eliminates the two observed
failure modes: flaw-named-but-banked (v3) and posture bleed across checks (v2↔v3
whiplash); ?-license becomes a code rule on turn-1 fields. Probe: 14-row
discrimination set — flips WYE, DAISY "Petal-puller's target?", CHECK "Threaten
the king", AMBER, NINE "A full lineup...", KARAOKE, ROBIN "Boy Wonder?", DAISY
"Sun-watcher?" must bank; guards DUSK, THIRD, SIXTEEN, THREE "A hat trick's
tally?", TEN "A strike in bowling?", FELIX "Favored by fortune?" must die. If it
threads the needle, the same decomposition is a candidate for the screen
(taste/craft split).

**Built (2026-07-04, while fine-tune held the machine):** battery gains a
`CONFIRM_STAGE` hook — a patch installs
`pipeline_local.CONFIRM_STAGE(judge_turn, word, clue)`;
`judge_turn(stage, system, protocol, schema)` runs one cached single-shot turn
(per-turn schema explicit in `_call_key`; single-turn keys unchanged, so the
whole existing cache still hits). Variant `variants/confirm_multiturn_v1.py`: 4
fresh-conversation turns, verdict + ?-license + article carve-out all code-side.
12 canned-field verdict checks pass; stock path replays byte-identical.

**Rung-0 (CHECK flip + DUSK guard):** try 1 — both die via
`substitution: referent` on one-line analyses; the turn committed the enum
without performing the substitution. DUSK's truth turn passed the
two-good-answers reading — ratified by user calibration #3 (non-pinning is a
feature). Try 2 (structural): schema requires `sentence_with_answer` +
`sentence_with_clue` before the shift fields, so the judgment conditions on
visible evidence. Result: CHECK banks with a clean evidenced pair; DUSK dies
fixable (`part_of_speech`, noun vs adverbial clause). Both agree with Fable.
Fixed en route: battery `--patch` exec needed its own namespace (deferred
functions from a patch crashed on name lookup).

**Rung-1 (14-row set, 60 calls, 24.9 min):** flips 6/8 — WYE, DAISY
"Petal-puller's target?", CHECK "Threaten the king", AMBER, ROBIN "Boy Wonder?",
DAISY "Sun-watcher?" bank; NINE dies on economy ('full' flagged as padding),
KARAOKE on a substitution article-frame artifact + economy flagging its vignette
clause. Guards 4/6 by verdict, and label triage reassigns both misses: THREE "A
hat trick's tally?" = flat fact + unearned ? + phantom trap (SCREEN territory —
the screen banked it; feeds idea 11 and the trap gap); TEN "A strike in
bowling?" = real confirm miss (marked-stretch too generous; Fable: "a strike
isn't TEN itself"). False banks DAISY "Subject of a petal-plucking game?" and
ROBIN "Sidekick to a Dark Knight?" are Fable "same-angle duplicate" —
independence, structurally invisible per-clue (v2 false-banked ROBIN-dup too);
discounted per calibration #4. Guard kills evidenced: THIRD economy, SIXTEEN
register + 'Sweet', FELIX referent.

**Try 3 (REVERTED):** economy redundancy rule + article-frame tolerance + "event
is not its score" license bound. Net worse — wording whack-a-mole, stop rule
invoked after 3 tries. THREE dies (fluke mechanism: `economy: tally`) but TEN
still banks; THIRD + FELIX regress to bankable (license rewording flipped their
marked-stretch judgment calls — jitter, not signal); NINE/KARAOKE still die, now
as `bad` (common root: the substitution turn builds broken frames — NINE's pair
reads "a full lineup on a baseball field on the field").

**Rung-2 batch A (tuning + losses, 24 calls, 12.8 min):** verdict-gated economy
first gave revises 21/21 but killed four Fable accepts on their FLAVOR words
(GROSS "Stomach-turning"+"total" — the whole clue flagged; THIRTEEN "often" —
deleting it makes the clue falser; POTS "that might be thrown" — the pun itself;
NINE "full") — the isolated economy turn is blind to taste by design and
prosecutes the words that earn the basis. Code-side fix, pre-registered and
re-scored FREE from cached fields (0 calls): padding demoted to advisory
(`advisories` in the log, never gates). Result vs baseline on tuning: accepts
8/10 vs 4/10 (every screen-passed accept banks; remaining misses CENTURY/MURMUR
are screen kills — idea 11), revises 18/21 = baseline (THIRD the sole
regression; LARRY/ZERO were v2 false banks too), losses NINE recovered /
FOURTEEN lost (substitution register technicality on an unmarked arithmetic
clue). ZED/SIXTEEN keep substitution kills — idea 6's ZED goal holds without
economy gating.

**Rung-2 batch B (holdout + rejects + funcal, 36 calls, 18.1 min):** holdout
accepts 3/7 (screen kills GRANT "Academic windfall?"/CHECK "Curb an
impulse"/STOCK — idea 11; confirm gains DAISY "Sun-watcher?" + ROBIN "Boy
Wonder?" vs v2, loses GRANT "Concede a point?" to frame WRECKAGE: "I will
concede a point your request"), revises 6/10 raw → 6/8 with the calibration-#4
dup discounts (false banks SCORE — v2 shared — and TABLE "Place to settle a
debate?", new). Rejects 16/18 (v2's THOUSAND false bank now dies; THREE/TEN the
known ?-taste banks). Funcal accepts 1/5: OREO banks, but SNOOZE (bad!) /
KARAOKE / GLITTER die at the substitution turn on the same definite-description
frame family as GRANT-concede — 4 Fable fun/aha accepts, one mechanism.

**Try 4 (REJECTED):** frame repair ("rebuild an ungrammatical frame — a broken
frame is your error, not the clue's flaw"). Won GRANT "Concede a
point?"/FOURTEEN/NINE but globally softened shift-reporting: guards ZED and
FELIX un-killed, POTS and OREO regressed, and the funcal vignette family it
targeted didn't move. Reverted.

**ADOPTED config:** sentence-pair substitution (try 2) + truth with non-pinning
removed (user calibration #3) + economy advisory + sense; verdict

- ?-license in code. Full-battery vs window-start baseline: tuning accepts 8/10
  vs 4/10, revises 18/21 = baseline; holdout accepts 3/7 vs 2/7, revises 6/8
  (disc.) vs 7/8; rejects 16/18 vs 17/18 (swap: THOUSAND killed, THREE/TEN
  banked); losses NINE recovered; funcal 1/5 (OREO). Known residual:
  definite-description vignettes die at substitution (SNOOZE/KARAOKE/GLITTER +
  GRANT-concede) — attack AFTER `#eval-expansion` gives that family real sample
  size. Production wiring deferred to end-of-window consolidation (needs a
  difficulty source — the screen already assigns one).

## User calibrations

**#1 (2026-07-03):** GASP "Reaction to a jump scare" is borderline — acceptable
judged either way. Its row discounts in all scorecards (a screen kill there is
not a false kill). General rule: single borderline rows the user flags are soft
labels — don't tune toward them, don't count them as defects.

**#2 (2026-07-03):** NIL "Nothing on the scoreboard" leans PASS — the virtue is
slight misdirection: "Nothing" reads first as absence and resolves to the posted
score, with no immediate collapse to the dull paraphrase. NIL stays a live
recall-loss target, the user's lean agreeing with Fable's accept.

**#3 (2026-07-04):** Non-pinning is NOT a flaw — a true clue that also fits
other answers is a strong clue: it forces cross-checking against crossing
answers. "When shadows stretch" fitting DAWN as well as DUSK is a feature.
Supersedes the idea-9 remark that v2's DUSK kill was legitimate on non-pinning
grounds. Consequence: "leaves several answers fitting equally well is a flaw"
language sits in BOTH production prompts (screen `_JUDGE_SYSTEM` and confirm
`_CONFIRM_SYSTEM`) — a candidate cause of the screen-recall family (CENTURY,
NIL, FIFTY are all under-determined-but-true surfaces). Queued as idea 11.

**#4 (2026-07-04):** Same-angle duplicates banked for one word are intentionally
FINE in the local run — the cloud judge's independence check controlled for
laziness in the cloud setter, and the local structure has no analogous need
(reevaluate at cleanup: `#angle-distinct` in tasks.md). Scoring consequence:
holdout rows whose Fable revise reason is "same-angle duplicate" — DAISY
"Subject of a petal-plucking game?" and ROBIN "Sidekick to a Dark Knight?" — are
discounted in ALL scorecards (a local bank there is not a false bank).
Requirements-alignment audit queued as `#judge-alignment`.

## Machine coordination

**Overnight 2026-07-03→04:** machine handed to the fine-tune thread ("12B
overnight re-run at 5e-5"); resumed on lease release 08:37, per the user's green
light.

**Handoff 2026-07-04 13:26:** rung-2 batch A killed at launch (zero confirm
calls made — the replay cache makes the re-run free) to yield to the fine-tune
thread ("morning analyses", lease to 16:11). They finished in ~20 min; batch A
re-ran 13:47. User will sort out the git branch divergence soon to ease
cross-thread scheduling; their thread runs MAIN's lease script and cannot see
this branch's waiter notes — coordinate via the user meanwhile. Standing user
direction (15:0x): yield to the fine-tune thread after the current batch;
released 15:2x after try 4.

## Expanded-set baseline (2026-07-04 afternoon, in progress)

**v2 on the expanded set — the fruit the user predicted.** Slot 1 (gentune, 93
calls, 31.8 min): accepts held 15/32, revises/rejects killed 31/32 (sole false
bank SEVENTY "The lifespan Scripture allots"). Slot 2 (genhold, 40 calls, 15.3
min): accepts held 5/14, kills 14/14. Combined: accepts 20/46 (43%), kills 45/46
(98%) — near-perfect precision, and a recall crisis that is worse than the
81-row sets showed and now well-shaped: the killed accepts concentrate in
prize-fact (SEVENTY "Years in the Psalmist's allotted lifespan", EIGHTY "Days
Phileas Fogg allotted...", HONEY, OCTOPUS, PIANO, VIOLIN, BILLION, MILLION,
BAMBOO, HUMMINGBIRD), elegance (THAW, CANOE, ORCHARD, GIFT, SPIDER, LIGHTHOUSE,
WRAPS, HAMMER, CACTUS), and fun (SOCKS, YAWN, RAT, ALARM, TOUCHDOWN "Reason to
spike the ball?", HAMMOCK). Screen kills outnumber confirm kills ~2:1 — the
screen systematically under-rates vivid straight definitions and prize facts;
what was anecdote (CENTURY, MURMUR, FIFTY, LATTE) is now a measured family with
N≈16.

**Slot 3a** (gentune under the ADOPTED multi-turn candidate, screens cached) was
running at compact time — its delta vs slot 1 isolates the confirm redesign on
~24 fresh rows; early rows showed both EIGHTY clues dying at the substitution
turn (watch: prize-fact "Days Phileas Fogg allotted..." is a flip target the
candidate may ALSO miss — if so, the prize-fact family is a screen+confirm
double miss). **Next: slot 3b** = same patch on genhold (~15 min warm). Then the
per-bucket v2-vs-candidate comparison read from the four expbase_* logs (free,
no model calls) → decide the screen-side attack (idea 11 non-pinning removal is
one hypothesis; the prize-fact/elegance under-rating may need its own
calibration idea, now testable at N≈16 with genhold guards).

## Machine protocol (one-off for the 2026-07-04 evening handoff)

After slot 3a: CEDE the machine to the fine-tune thread (auto-release armed in
session background). For THIS handoff only (user direction — not a standing
rule): re-acquire only after the lease measures free at T0, T15, and T30 — three
checks, 15 min apart, all free (the fine-tune thread runs main's lease script
and cannot see waiter notes). A background scan implementing exactly this is
armed and will notify when clear; if the session restarts, re-arm the same scan
before touching the lease. Once this handoff is done, cross-thread scheduling
goes back to coordinating through the user until the lease-script fork
reunifies.

## Remaining queue

**Expanded-set baseline — PREPPED, machine use WAITS FOR USER GO (2026-07-04
~16:00).** Sets built and committed (gentune 64 / genhold 28, $1.80). When
cleared, run from `cluegen/scratch/` one lease slot at a time, releasing between
slots:

1. screens (~30 min): `battery.py --sets gentune,genhold --tag expbase_v2`
2. v2 confirms ride the same run (packed confirm, 1 call per screen-bankable)
3. candidate confirms (~60 min, split if needed): same sets with
   `--patch variants/confirm_multiturn_v1.py --tag expbase_mt` (screens replay
   from cache)

Read: v2 vs adopted candidate per bucket — bucket-level gaps are the
lower-hanging-fruit signal the expansion exists to surface.

Budget after expansion generation: $7.18 of $10. Reordered 2026-07-04 (user
priority): FIRST `#eval-expansion` — grow the labeled set to ~100 via one-off
Fable generation (design in tasks.md; two detached calls,
~$1-1.5 each; group 1 launched 15:5x). Then re-read v2 vs the
idea-10 candidate on the expanded set before further tuning. Then idea 11 —
drop non-pinning prosecution from the screen (variant of `_JUDGE_SYSTEM`; flip
targets = the screen-killed Fable-accepts; guards = rejects-set precision,
which the screen currently carries at 14/18 kills); screen-recall families
(diagnose from cached analyses — free: CENTURY "Batsman's milestone", MURMUR
"Low hum of a restless crowd", NIL "Nothing on the scoreboard", FIFTY "The
denomination on a red bill" (dies screen-bad!), LATTE, GRANT "Academic
windfall?", CHECK "Curb an impulse", STOCK "Simmering base for a stew"); K=3
stability on GROSS + adopted-stack flips; sealed fresh-bank labeling at
end-of-window (24 clues, `fresh_label_input.jsonl` version fresh-bank — still
unlabeled, still sealed); judge-temperature decision; #taste-31b. Budget:
$8.98
of $10 remains (minus expansion generation, cost pending).
