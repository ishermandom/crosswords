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

**#5 (2026-07-04):** UMBRELLA "Canopy on a stick that a sudden gust turns inside
out" (gentune fun accept, Fable-generated) is a soft label — the user reads it
as low-efficiency, so per the #1 rule its row discounts in all scorecards: a
kill there is not a false kill, and it counts as a borderline recovery for the
register fix (tally: 6 solid + 1 borderline), not a clean one. Also not clean
evidence against the 26B in the parity read.

**#6 (2026-07-05, NYT-corpus-grounded batch):** the user fetched primary sources
(`/Users/Shared/data/nyt_style/`, Kaggle corpus at
`/Users/Shared/data/kaggle-nyt/`); rulings and the resulting eval-label edits
(all rows carry `calibrated: 2026-07-05`):

- **Implicit units are fine when the noun is quantity-valued** (lifespan,
  jackpot, age, speed limit — attested: SEVENTY as "Stalin's age", "Common
  highway speed limit"). SEVENTY "The lifespan Scripture allots" and MILLION
  "The jackpot Regis dangled" flip revise → accept.
- **The '?' means wordplay, specifically** — not "almost a good clue", and not a
  repair for a false equivalence with no wordplay in it. TOUCHDOWN "Six points?"
  STAYS revise (NYT bar: corpus has zero bare six-points equations; the NYT
  writes "Six-pt. plays"). Design implication: the ?-carve-out in the multi-turn
  confirm over-licenses — it should license pun/misdirection, not bare metonymy.
  Fold into judge tuning.
- **Archaic senses are lame per obscurity** — BRAND "Sword, in old verse" accept
  → revise ("believable but feels random").
- **Unmarked hyperbole fails accuracy** — ALARM "crime scene" accept → revise
  ("a question mark is automatic if your clue stretches the truth or can't be
  taken as fact" — constructor guide). **Economy demotions**: THERMOSTAT "Wall
  dial nudged upward..." and SCARECROW "Straw-stuffed sentry standing watch..."
  accept → revise.
- Foreign-word rule refinement (for the judges, labels unchanged): foreign
  vocabulary is fine when signposted AND well-known to a typical English speaker
  (MERCI "Thanks, in Paris" grade); the sense-ownership turn's binary
  English-only test would wrongly kill those. GIFT/BRAND foreign rejects stay —
  false-friend homographs are nowhere near the bar (and are essentially
  unattested in 28 years of NYT corpus).

### Calibrated re-score (2026-07-05, all from cache, 0 model calls)

Totals across both sets — 44 accepts, 48 revise/rejects after calibration (tags
`expbase_{v2c,mtc,mt26c}_*`):

| config      | accepts held | kills |
| ----------- | ------------ | ----- |
| v2 baseline | 18/44        | 45/48 |
| mt 31B      | 19/44        | 42/48 |
| mt 26B      | 7/44         | 45/48 |

The calibration collapses the 31B candidate's lead over v2 to parity (+1 accept,
−3 kills): its five new kill misses are exactly the demoted rows (ALARM,
THERMOSTAT, SCARECROW, BRAND + the standing TOUCHDOWN/MIRAGE), i.e.
economy/hyperbole/obscurity flaws — the dimensions the multi-turn confirm
deliberately soft-pedals (padding advisory, register advisory). The v2 screen's
flatness/padding gating, which false-kills FOG-grade accepts, is ALSO what
correctly kills these. Lesson: economy and hyperbole need a calibrated gate, not
advisory status and not the screen's blanket prosecution — the FOG/RUST vs
THERMOSTAT/ALARM line is the threshold to learn. 26B verdict unchanged: still
clearly below on accepts.

**#7 (2026-07-05, suspects batch):** rulings that draw the economy threshold:

- RUST stays accept — "slowly" being inherent to rust's eating is part of what
  makes the clue work: the answer is not in the clue, so inherent-property words
  are load-bearing hints, and the deletion-test padding standard does not
  transfer mechanically from rows like IGLOO's "frozen snow" (where the defined
  word IS present in spirit). "Abandoned" isn't required either — an in-use
  tractor can rust.
- CANOE stays accept — "glassy lake at dawn" is legitimate scene-setting; not
  comparable to THERMOSTAT's demotion (explicit taste ruling).
- SOCKS stays accept ("a keeper") — hyperbole mapping to a true phenomenon sits
  on the FOG side of the accuracy line.
- HAMMOCK stays accept but SOFT (`soft: true` in the row) — borderline on
  economy, "a bit charming as a scene"; discount in scorecard readings.
- UMBRELLA accept → revise on economy — supersedes calibration #5's soft-label
  treatment.
- TOUCHDOWN accept's clue text amended to drop the unearned '?' ("Reason to
  spike the ball") — NOTE: this re-keys that clue's replay cache, so genhold
  scorecards need ~11 fresh calls (screen + confirms across the three configs)
  next time genhold runs; genhold numbers above predate the text edit and are
  stale for that one row.

Gentune re-scored free after the UMBRELLA flip (30 accepts / 34 revise-rejects;
tags `expbase_{v2c2,mtc2,mt26c2}_gentune`): v2 13/30 + 31/34, mt-31B 12/30 +
30/34, mt-26B 5/30 + 31/34. The v2-vs-31B parity and the 26B gap both hold.

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

**Slot 3a result (gentune under the adopted candidate, 116 calls, 61.9 min):
accepts held 8/32 — a big regression vs v2's 15/32 — kills 31/32 (false bank
moved to MIRAGE revise; SEVENTY revise now killed; MOON "Night light?" recovered
via the ?-carve-out).** Turn-level read from the JSONL: every one of the 14
confirm-stage accept kills came from the substitution turn (plus one truth
co-flag), and 8/14 carried the label "unlicensed register shift" — the judge
pins "register" on figurative or playful framing (FOG "Gray breath that swallows
streetlamps whole", CRICKET "Tiny violinist of the summer grass", GARLIC,
PILLOW, UMBRELLA, BRAND "Sword, in old verse", HONEY, KETCHUP), which the
schema's forced shift enum invites. The original 81-row sets had too few
figurative accepts for this to show — exactly the small-set blind spot the
expansion was built to expose.

**Fix applied (code-side, free): register shift is now advisory, never gating**
— `_verdict_from_turns` in the variant routes it to `advisories`; referent stays
bad, other shifts stay fixable. Counterfactual re-score from cached turn fields:
recovers 7/8 register kills (CRICKET keeps a truth flaw), loses 0 revise/reject
kills → gentune becomes accepts 15/32, kills 31/32 — parity with v2 on generated
rows while keeping the candidate's real-world wins (8/10 vs 4/10 tuning accepts)
and the MOON recovery. Offline verdict-rule checks updated and green (scratchpad
`test_confirm_multiturn.py`).

Remaining candidate-vs-v2 gentune deltas after the fix: candidate still kills
SEVENTY (number shift), EIGHTY + RUST + SOCKS + YAWN (referent shift on
personification/metonymy — same family, harsher verdict "bad"), THAW
(part-of-speech). Watch: referent-shift-on-personification may be register's
sibling problem, but referent gating carries the count-metonymy kills — do NOT
soften it without checking which kills depend on it.

**Slot 3b result (genhold under register-advisory candidate, 48 calls, 22.9
min): accepts held 8/14 vs v2's 5/14; kills 13/14 vs 14/14.** The gentune replay
logged the official re-score: 15/32, 31/32, 0 model calls. The lost genhold kill
is TOUCHDOWN revise "Six points?" — verified from turn fields that it did NOT
hinge on the register fix: the substitution turn correctly found a referent
shift (event → its score) but judged it the marked stretch of the '?', so the
code-side ?-license carve-out banked it. Fable's label reason: "the ? cannot
repair a false equivalence." Residual, N=1, and the label itself is debatable
(US convention accepts "Six points" for TOUCHDOWN); the same carve-out delivers
the MOON and TOUCHDOWN-accept recoveries. Verdict: register fix vindicated on
fresh data; ?-license false-equivalence boundary goes on the watch list.

### The 2×2, complete (expanded set, post-fix)

| set     | v2 accepts | cand accepts | v2 kills | cand kills |
| ------- | ---------- | ------------ | -------- | ---------- |
| gentune | 15/32      | 15/32        | 31/32    | 31/32      |
| genhold | 5/14       | 8/14         | 14/14    | 13/14      |

Candidate confirm now holds 23 of the 30 accepts that reach it (genhold 8/8);
the screen kills 16/46 accepts (35%) before confirm ever sees them — the recall
crisis is now almost entirely the screen.

### Screen-kill diagnosis (from cached screen analyses, free read)

Two mechanisms, both mirrors of flaws already fixed on the confirm side:

- **"Dictionary-flat / lacks pivot" downgrades.** The screen treats a missing
  shift/misdirection as a flaw and marks vivid straight definitions and prize
  facts fixable: OCTOPUS "three hearts and blue blood", VIOLIN, PIANO, SPIDER,
  WRAPS, BAMBOO, BILLION, RAT, CANOE. Its analyses literally say "no flaws, but
  it lacks liveliness" → fixable. The screen's basis taxonomy doesn't credit
  prize-fact/elegance/fun as redeeming bases.
- **Padding gating on the words that carry the basis.** CANOE "gliding across a
  glassy lake at dawn", ORCHARD "planted for the picking", LIGHTHOUSE, HAMMER,
  CACTUS, HAMMOCK, PIANO "most of them white" — the exact economy failure the
  confirm side demoted to advisory (idea 10 rung 2); the screen still gates on
  it.
- One accuracy case: HUMMINGBIRD "Only bird that can fly backward" — screen
  prosecutes "Only" as an overclaim; Fable labeled it a prize-fact accept.

### Screen attack options (decision pending — ask the user)

- (a) **Prompt fix**: teach the screen's system prompt to credit
  prize-fact/elegance/fun bases and demote padding to advisory. Invalidates the
  screen cache (new system text → new keys): ~64 fresh 26B calls ≈ 20 min per
  set-pair, plus wording-iteration risk (the confirm side needed a code-side
  rule, not prompt text, to hold a carve-out).
- (b) **Cascade fix**: stop trusting screen "fixable" as a kill — route
  screen-fixable clues to confirm and let the multi-turn verdict decide; screen
  kills only on "bad". Code-side, screen cache intact, no wording iteration;
  cost is 4 × 31B turns for every screen-fixable clue (all true revises
  included, so battery wall time roughly doubles vs the cascade).
- Idea 11 (non-pinning removal) is orthogonal and untested; the flatness
  mechanism above explains the measured family without it.

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

## In flight: 26B multi-turn measurement (user-approved 2026-07-04 ~22:00)

**Question (supersedes #taste-31b and reframes idea 11): does the multi-turn
protocol at 26B match it at 31B?** If yes, the 26B/31B divide dies and the
architecture becomes one protocol with model size as a quality dial — the user's
proposed design; my analysis agreed (the window's evidence says the wins came
from decomposition + code verdict, not params: v3 failed single-turn ON 31B, and
the screen's cached analyses show correct perception with wrong one-shot
policy).

Mechanics: `battery.py --confirm-model gemma4:26b-qat` (new flag) with the
adopted patch, tags `expbase_mt26_{gentune,genhold}`; screens cached, so the
same 41 screen-survivors reach confirm — a clean protocol-constant comparison.
Driver detached (waits FIFO behind the fine-tune lease, caffeinate wraps only
the model runs, releases when done); watcher reports scorecards.

Pre-registered comparison, confirm stage only (screen survivors):

| axis                   | 31B result | 26B parity bar |
| ---------------------- | ---------- | -------------- |
| accepts held (of 30)   | 23         | >= ~21         |
| survivor kills (of 11) | 9          | >= 8           |

At or above the bar → recommend the single-flow redesign (26B default, 31B as an
escalation dial, e.g. a bank-time pass); clearly below → keep the dial design
but 31B stays the default judge tier. Either way the screen's separate verdict
policy is dead on the expanded-set evidence — the open screen question becomes
cheap early-kill turn ordering, not a second policy (idea 11's non-pinning
removal folds into the single-protocol design rather than a screen-prompt
patch).

### Result (2026-07-04 ~23:40): clearly below the accept bar — 31B stays

Survivor accepts held: **9 of 30 vs the 31B's 23 (bar was >= ~21)**; survivor
kills 10/11 vs the 31B's 9 (it correctly killed TOUCHDOWN "Six points?", which
the 31B banks; it banked MIRAGE's revise, the same miss the 31B makes). Genhold
accepts 2/14, gentune 7/32. UMBRELLA discounts per calibration #5; the verdict
is unchanged with or without it.

Single mechanism, verified from turn fields: **all 21 accept kills carry exactly
one flaw, "substitution: unlicensed referent shift" → bad.** The 26B labels
every figurative framing a referent shift — it cannot hold the distinction the
31B draws between playful framing of the right referent (register, advisory) and
actually pointing at a different thing (referent, bad). It held only accepts
whose definitions are literal (HONEY, KETCHUP, BRAND, SCARECROW) or ?-licensed
(MOON, DENTIST, SPIDER "Web developer?", BAKER, TOUCHDOWN accept). That
shift-classification judgment is what the extra parameters buy; the protocol
alone doesn't confer it — though the user (2026-07-04) suspects a reshaped
prompt could close a single-flaw gap; queued as `#judge-26b-referent` in
tasks.md, blocked on the user clarifying the target.

Speed note that changes production math: 26B calls averaged ~5 s vs ~32 s for
the 31B (10.0 min for the same 116 calls that took 61.9 at 31B). Even so, the
26B has no rescuable judge role: its survivor-kill precision is 10/31 (it kills
21 true accepts), so its kills can't gate; its banks are 9/10 precise but a
pass-through-only stage saves almost nothing.

Design consequence: single flow, one protocol, **31B as the only judge tier**;
26B leaves the judge path entirely (screen policy already dead; 26B multi-turn
now measured worse). Production cost control comes from substitution-first
short-circuit (~1 turn ≈ 30 s per junk clue), not from a smaller model.
Difficulty assignment still needs re-homing out of the screen.

## Remaining queue

`#eval-expansion` DONE through the 2×2 (sets built
$1.80; slots 1-3b above).
Still queued: screen-recall family diagnosis on the ORIGINAL 81-row sets from
cached analyses — free (CENTURY "Batsman's milestone", MURMUR "Low hum of a
restless crowd", NIL "Nothing on the scoreboard", FIFTY "The denomination on a
red bill" (dies screen-bad!), LATTE, GRANT "Academic windfall?", CHECK "Curb
an impulse", STOCK "Simmering base for a stew") — now doubles as evidence for
the single-flow turn-ordering design; K=3 stability on GROSS + adopted-stack
flips; judge-temperature decision; sealed fresh-bank labeling at end-of-window
(24 clues, `fresh_label_input.jsonl` version fresh-bank — still unlabeled,
still sealed); end-of-window production wiring of the adopted confirm
(difficulty source needed — the screen assigns it today; re-home it before any
single-flow redesign lands). #taste-31b superseded by the in-flight 26B
measurement. Budget: $7.18
of $10 remains.
