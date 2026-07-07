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
| 12  | confirm v2e: turns + panel   | ADOPTED-IN-BATTERY |
| 13  | single-flow consolidation    | ADOPTED-IN-BATTERY |

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

## Idea 12 — confirm v2e: calibrated turns + economy panel (ADOPTED)

`variants/confirm_multiturn_v2.py`, user-approved batch train 2026-07-05
("proceed with the next few batches"). All four turns redesigned per
calibrations #6/#7; verdict stays code-side. Mechanisms: (1) substitution asks
what the definition POINTS AT (answer, through metaphor/role/implicit-unit, vs a
named other object) — replaces the shift enum and the ?-carve-out entirely; (2)
truth gains the hyperbole rule (figurative claims judged by factual core;
unmarked no-core exaggeration fails); (3) economy becomes a calibrated gate
(inherent-property hints and charming scenes earn keep; restatement and dead
tails are bloat; gates only on committed `is_bloated` + quoting evidence); (4)
sense splits usability (signposted well-known foreign OK — MERCI grade) from
common knowledge (archaic = obscure = fixable). Offline verdict-rule checks
green (`test_confirm_multiturn_v2.py`).

Pre-registered rung 1 (gentune probe, 18 words, ~23 confirm rows, ~92 fresh 31B
calls ≈ 50 min), targets vs mt-31B c2 behavior:

- **Accept recoveries** (now false-killed): SEVENTY both rows, EIGHTY "Days
  Phileas Fogg allotted...", RUST, SOCKS, YAWN, THAW, CRICKET.
- **New kills** (now false-banked): SCARECROW-sentry + UMBRELLA (economy),
  BRAND-sword (obscurity), MIRAGE-revise "hot desert heat" (economy).
- **Guards**: FOG, GARLIC, TOASTER, ESCALATOR, MOON, MIRAGE-accept stay banked;
  VIOLIN-bow, SCARECROW-foil, EIGHTY-wager, GIFT-Munich, BRAND-Amsterdam stay
  killed.

Genhold consulted only at adoption (expect there: TOUCHDOWN-spike recovery,
TOUCHDOWN-"Six points?" kill, ALARM/THERMOSTAT kills, BAKER/EMBER/MAPLE/ IGLOO
holds). Stop rule: 6 wording tries with opposite-direction overshoots ends the
attempt (user raised from the ~3 idea-10 used, 2026-07-05; each try still
requires a turn-field diagnosis before the next).

**Rung 1 result** (92 calls, 54 min): accepts 12/16, kills 17/20. Hits: all six
figurative/personification recoveries (RUST, SOCKS, YAWN, THAW, CRICKET,
SEVENTY-Psalmist) + MOON banked WITHOUT the carve-out + BRAND-sword killed on
obscurity + MIRAGE-revise killed on economy + every wrong-object and
foreign-sense guard held. Misses, diagnosed from turn fields: SEVENTY-lifespan
died to a junk truth flag (`['The']` — bare article); EIGHTY-days died
grammar_mismatch (plural counted noun); EIGHTY-wager BANKED (guard broken — the
turn reasoned "the value of the wager IS eighty", missing that the wager's value
is £20,000); UMBRELLA + SCARECROW-sentry banked (economy turn praised their
tails as "inherent identifying properties" — the MOLD example taught
inherent-property too broadly).

**Rung 2 (try 2):** four fixes — (a) code: truth flags get the same
quote-validation as economy evidence (kills the junk-article flag, free); (b)
substitution rule text: plural counted nouns are not grammar mismatches ("Keys
on a grand piano" shape); (c) substitution value test: a quantity equation is
fair only when the named quantity's own value IS the number — a bet/prize/event
whose value is something else is other_object; (d) economy: "surplus fact" named
as a bloat shape — once the definition is complete, one more literal fact is
bloat unless it is genuine charm (STOOL fail example, BONFIRE poetry pass
example). Only substitution + economy turns re-key (~46 fresh calls ≈ 25 min).
Targets: the five rung-1 misses. Guards: all rung-1 hits — especially RUST's
"slowly" (must stay earning under the surplus-fact language) and the six
recoveries (substitution re-runs under the new text).

**Rung 2 result** (46 calls, 31 min): kills PERFECT 20/20 — EIGHTY-wager killed
by the value test, UMBRELLA and SCARECROW-sentry killed by the surplus-fact
shape, every kill guard held. But accepts 10/16 — the classic opposite-direction
overshoot (try 1 economy under-fired; try 2 over-fires). SEVENTY-lifespan
recovered (junk-flag code fix worked); regressions, all economy, all "surplus
fact" prosecutions of tails that ARE the clue's point: GARLIC "that also repels
first dates" (the joke), ESCALATOR "whether or not you step aboard" (the
paradox), SEVENTY-Psalmist "allotted" (single inherent-property modifier —
exactly the RUST-"slowly" family the MOLD example should protect), EIGHTY-days
"for going around the world" (the recognizability that makes the fact a prize).
Substitution side fully clean: all four regressed rows have points_at=answer.

**Try 3 (point-vs-appendage test):** ran after the overnight handoff cleared (23
calls, 11 min). Accepts 11/16, kills 19/20. All four try-2 regressions recovered
(GARLIC, ESCALATOR, SEVENTY-Psalmist, EIGHTY-days) and SCARECROW-sentry STAYS
killed — the point-test holds wit tails while killing restatement. New misses,
all at word granularity: FOG killed for 'Gray', TOASTER for 'Countertop',
CRICKET for 'of the summer grass' (the deletion test prosecuting atmosphere),
and UMBRELLA un-killed (the model stably reads its gust tail as vivid charm in
every wording except try-2's blunt one).

**Try 4 result** (23 calls, 10.5 min): accepts 11/16, kills 19/20 — same totals
as try 3, different composition. Texture rule recovered FOG/CRICKET/TOASTER and
MIRAGE/SCARECROW kills held, but fresh jitter rotated in: SOCKS and YAWN (held
in every previous try) now die, EIGHTY-days flipped back. **Diagnosis: not
directional overshoot but per-wording jitter — each rewording moves ~2-3
borderline taste rows at random.** More wording rotates the noise; it does not
converge.

**Rung 5 (STRUCTURAL, in flight): economy as a 3-wording majority panel
(`confirm_multiturn_v2e.py`).** Free cached-vote analysis across tries 1/3/4
scored every economy-sensitive probe row correctly except UMBRELLA (the accepted
miss): all 14 borderline accepts held, MIRAGE-revise 3/3, SCARECROW-sentry 2/3,
EIGHTY-wager 2/3 killed. v2e runs all three wordings per clue (byte-identical to
their rungs, so probe calls replay) and gates in code on 2-of-3 (is_bloated AND
quote-validated evidence); lone votes are advisories. Cost: +2 economy calls per
confirm clue. Rung 5 = FULL gentune (~36 fresh calls for the six never-probed
survivors: HONEY, KETCHUP, PILLOW, LEMON, DENTIST, SPIDER-webdev — all predicted
to hold as accepts). Pre-registered prediction: gentune accepts 20/30 (all 20
confirm-reaching accepts held; the 10 screen kills unchanged), kills 33/34
(UMBRELLA the sole miss). Then genhold for the adoption read. Wording-try budget
state: 4 of 6 used; the panel is a structural change, not a wording try.

**Rung 5 result** (36 calls, 17 min): accepts 18/30, kills 33/34 — kills exactly
as pre-registered (UMBRELLA sole miss), accepts two short. The two misses (both
never-probed rows): KETCHUP killed for "in the 1830s", PILLOW for
"Nightly"/"deposits" — each on a **t3+t4 majority with t1 dissenting**.
Diagnosis: t4 is a direct edit of t3, so the pair votes as correlated siblings
on fresh rows, not independent wordings — the probe couldn't show this because
each wording was tuned against it. The date is the prize-fact's teeth and the
joke's furniture is not bloat; a diverse third opinion protects both.

**Rung 6 (panel v2; wording try 5 of 6 on the new member):** t4 swapped out for
a trimming-editor framing with its own examples (TROLLEY/LIME cuts, WATCH/BEAVER
keeps). Panel = t1 + t3 + editor, 2-of-3 unchanged. Result (29 calls, 14.5 min):
accepts 17/30, kills 33/34 — KETCHUP recovered and EIGHTY-wager's kill held, but
the editor proved strict on prize specifics: HONEY "3,000-year-old Egyptian
tombs" and TOASTER died to t3+editor majorities; PILLOW died again.

**Panel frozen by exhaustive offline evaluation (free, all cached votes).** With
four wordings' votes on all 29 gentune survivors, every composition × threshold
was scored. The Pareto front: **unanimous (t3 + t4 + editor) = 19/20
confirm-stage accepts + 8/9 kills** (3-of-4 over the quad ties it at one more
call). All 2-of-3 rules cap at 18/20; unanimity over t1-containing triples
reaches 20/20 accepts but drops to 7/9 kills. The strict members carry the
kills; the editor's dissent protects prize-fact specifics. v2e updated: panel
(t3, t4, editor), gate on unanimity, docstrings and offline checks updated
(green). Residual misses, both label-suspect: PILLOW "Nightly recipient of drool
deposits" (3 of 4 wordings vote its tail bloated — flagged for a user ruling,
cf. UMBRELLA/HAMMOCK) and UMBRELLA (accepted).

**Genhold adoption run (~72 fresh calls ≈ 40 min):** first unseal of genhold for
all of v2. Pre-registered: every confirm-reaching accept holds (MILLION "Dollars
in the top prize" AND "The jackpot Regis dangled" via the value test, TOUCHDOWN
"Reason to spike the ball" via consequence framing, EMBER, MAPLE, IGLOO, BAKER);
kills include TOUCHDOWN "Six points?" (value test), ALARM (unmarked hyperbole,
truth), THERMOSTAT "Wall dial..." (economy panel), THERMOSTAT-thermometer
(other_object), WRAPS "Secrecy?" (idiom sense). HAMMOCK is soft — discounts
either way. Adoption bar vs the c2 table (v1 genhold: 5/13 + 12/15): clearly
better on both axes, no new failure family.

**Genhold result** (72 calls, 38 min; plus the free gentune replay under the
frozen panel: 19/30 + 33/34): genhold accepts 5/13, kills 14/15 → v2e totals
24/43 + 47/49 vs v1's 17/43 + 42/49 — decisively better on both axes.
Pre-registration hits: TOUCHDOWN-spike recovered, ALARM and both THERMOSTAT rows
and WRAPS-secrecy killed, MILLION-dollars/MAPLE/IGLOO/BAKER held. Misses, all
three diagnosed from fields:

- MILLION "The jackpot Regis dangled" false-killed: the turn derived "Value of
  Jackpot = Million" and STILL flagged other_object — the value-test sentence's
  "bet, prize, or event" list planted prize as an other_object cue. Wording
  defect, ours.
- TOUCHDOWN "Six points?" banked: the value test as written LICENSES event-value
  equations ("the thing worth six points is the touchdown itself"). Scope
  defect, ours.
- EMBER false-killed by a UNANIMOUS economy panel on "long after the flames give
  up" — arguably the defining behavior (an ember is what glows after the fire).
  First unanimous panel miss; single row; WATCH, no economy try.

**Try 6 of 6 (rung 7, in flight): value-test rewrite.** Both substitution misses
encode failures against the user's pre-genhold rulings (calibration #6/#7 named
both rows), so this is finishing the encoding, not holdout mining. New text:
amount/duration/age/score/prize whose value IS the number points at the answer
(jackpot of a million IS a million); a thing whose own value is something else
is a different thing; and an event is never its bare point value in either
direction ("Six points" describes the score, not the play). Substitution
re-keys: gentune ~29 + genhold ~12 calls ≈ 25 min. Targets: jackpot holds, "Six
points?" dies. Guards: SEVENTY both rows, EIGHTY both dispositions,
TOUCHDOWN-spike, MILLION-dollars, all wrong-object kills, the personification
family. If guards regress, fall back to the pre-try-6 v2e (7032ad3) and adopt it
as-is.

**Rung 7 result — ADOPTED (cb32390 is the adopted config).** Both targets
flipped with zero guard movement: genhold 6/13 accepts + 15/15 kills
(MILLION-jackpot holds, "Six points?" dies), gentune unchanged at 19/30 + 33/34.
**Final v2e: 25/43 accepts + 48/49 kills, vs idea-10 v1's 17/43 + 42/49 and the
single-turn v2 baseline's 17/43 + 45/49.** Wording budget closed at 6/6.
Residual misses, all named: 16 accepts die at the SCREEN (queue item 2's
territory — the confirm never sees them); PILLOW (label-suspect, user ruling
pending); UMBRELLA (accepted taste miss, the sole kill miss); EMBER (unanimous
economy-panel false kill on the defining tail — watch item, no economy budget
spent). v2e supersedes v1 as the battery confirm; production wiring still needs
the difficulty re-homing (end-of-window consolidation).

**Try 4 (superseded mid-flight by the rung-5 read):** two changes, and one scope
cut. (a) The deletion test runs on clauses and phrases, never single words. (b)
Modifier rules: repetition of content already in the clue is restatement — bloat
at any length ('hot' before "heat", PASTE "that adheres" example); sensory
texture — a color, a season, a place — is charm, never bloat (the answer is
hidden; texture is how it emerges). (c) **UMBRELLA is now an accepted miss, not
a target**: the user called this boundary a matter of taste, HAMMOCK (same
family) is soft-labeled, and chasing it is what broke FOG twice. Predictions:
FOG/CRICKET/TOASTER recover as texture, MIRAGE-revise 'hot' still dies as
repetition, SCARECROW stays killed, all try-3 recoveries hold. Fallback adoption
if tries run out: best cell so far.

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

Genhold refreshed after the TOUCHDOWN text edit (10 fresh calls, ~3.5 min; 13
accepts / 15 revise-rejects): v2 4/13 + 14/15, mt-31B 5/13 + 12/15, mt-26B
1/13 + 15/15. **New defect isolated by the edit:** with the unearned '?' gone,
both multi-turn configs now false-kill "Reason to spike the ball" (v2 still
holds it) — the substitution turn labels definition-by-consequence a referent
shift, and only the '?' carve-out had been saving it. Consequence/role
definitions are not referent shifts; this goes into the carve-out redesign
inside the economy-gate batch (queue item 1). Combined c2 totals (43 accepts /
49 revise-rejects): v2 17 + 45, mt-31B 17 + 42, mt-26B 6 + 46 — v2 and the 31B
candidate are now dead even on accepts and v2 leads on kills.

**#8 (2026-07-06):** PILLOW "Nightly recipient of drool deposits" stays an
accept, LOW PRIORITY — a real false kill but not worth tuning toward. EMBER
"Orange eye winking in the ash long after the flames give up" demoted to revise
("feels pretty bloated / inelegant") — the unanimous economy panel called it
correctly, so the idea-12 watch item dissolves and the adopted v2e re-scores to
**25/42 accepts + 49/50 kills** (genhold 6/12 + 16/16, from cache). Approved
next: the screen-off measurement (v2e alone on all rows, ~51 first-look rows,
user go for the multi-hour run), then the single-flow consolidation design, then
the 26B rehab measurement.

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

## Machine protocol (per-handoff one-offs, never a standing rule)

**2026-07-04 evening handoff (done):** ceded after slot 3a; re-acquired after
the user's direct go superseded the scan.

**2026-07-05 overnight handoff (done):** batch train paused after idea-12 rung
2; T0/T15/T30 scan (one-off) cleared 07-05 ~15:18 and the ladder resumed.

**2026-07-06 overnight handoff (ACTIVE):** fine-tune thread runs overnight ("15k
rung night 2", lease to ~10:09). Per user, ANOTHER one-off cadence — never a
standing rule; the cadence is user-specified per handoff: batch runs may start
once the lease measures free at **T0, T5, and T10** (10 free minutes with a
midpoint check). The screen-off driver (pid 79773) implements exactly this gate,
loops back to waiting if any check finds the lease held, and releases when its
runs finish. Cross-thread scheduling otherwise goes through the user until the
lease-script fork reunifies (git divergence still on the user's list).

## 26B single-flow close-out (2026-07-06)

Final word on the cheap tier: under adopted v2e on the full sets
(`mt26_screenoff_*`), the 26B holds **37/42 accepts** — the v1 referent flaw is
fully cured, vindicating the user's promptability bet — but swings lenient on
kills: **32/50** (banks a third of revise/rejects). Gentune 29/30 + 22/34;
genhold 8/12 + 10/16. High-recall/low-precision has no slot in the judge path;
#judge-26b-referent closed in tasks.md. Speed for the record: the 552-call sweep
took 54 min (~5.9 s/call).

## 26B multi-turn measurement (user-approved 2026-07-04 ~22:00)

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

Design consequence: single flow, one protocol, **31B as the only judge tier for
now**; the 26B leaves the judge path (screen policy already dead; 26B multi-turn
measured lenient) but stays on the backburner, not closed — user 2026-07-06: the
depths aren't mined; only one protocol variant was ever tried on the 26B, and
its ~6× speed keeps the prize large. See `#judge-26b-backburner` in tasks.md.
Production cost control meanwhile comes from substitution-first short-circuit
(~1 turn ≈ 30 s per junk clue), not from a smaller model. Difficulty assignment
still needs re-homing out of the screen.

## Idea 13 — single-flow consolidation (DESIGN DRAFT, awaiting user review)

Goal: one judge protocol — the adopted v2e plus one new turn — replacing the
screen's separate verdict policy entirely; the screen's two legitimate functions
move inside the protocol.

Evidence base (screen-off measurement, 2026-07-06): v2e alone scores 31/42
accepts + 40/50 kills vs the cascade's 25/42 + 49/50. The screen's whole
remaining value is nine kills in exactly two families v2e was designed not to
judge: flat glosses (6: "Sweet stuff that bees make" family) and unearned
question marks (3: "Tooth doctor?" family). Its whole remaining cost is six
false kills of user-ratified vivid definitions (OCTOPUS "three hearts", VIOLIN,
SPIDER-spinner, CANOE, LIGHTHOUSE, BAMBOO).

Design:

- **New liveliness turn** (the screen's taste call, calibrated): judges whether
  the clue's interest has a basis — prize fact, fun, elegance, aha — or is a
  flat gloss. Fields: `analysis`, `basis` (enum incl. `none`), `has_wordplay`
  (bool), `difficulty` (re-homing the screen's assignment — same judgment
  locus). Calibration examples are fresh-crafted graded pairs in the eval
  buckets' shapes (tomb-fact vs bees-gloss), never eval rows.
- **Verdict rule additions (code)**: `basis: none` → fixable (flat); '?' in clue
  AND not `has_wordplay` → fixable (unearned mark, calibration #7). Wordplay
  without '?' stays legal (late-week convention).
- **Ordering**: battery keeps all-turns-always; production short-circuits with
  liveliness FIRST — one ~30s call kills flat junk at the same price point as
  the old screen, and the rest of the protocol runs on survivors.
- **Jitter posture**: start single-wording; if rungs show borderline-taste
  rotation (the economy lesson), promote to a panel — the mechanism is already
  built.
- **Cost**: worst case 7 calls ≈ 3.7 min/clue at 31B; flat junk ~30s. Net
  comparable to the cascade for junk-heavy setter streams.

**Stretch grants (2026-07-06, user):** full idea-13 ladder through the genhold
adoption read, brief reports, no per-batch check-ins; plain FIFO lease
coordination for this stretch (one-off); after idea 13, Claude decides
setter-vs-judge for the next low-hanging fruit and proceeds; sealed fresh-bank
labeling at Claude's discretion; Fable budget refreshed to $10. Pipeline wiring
is DEFERRED entirely (user discussion 2026-07-06): integrating now was
checklist-completion, not a reasoned trigger — the pipeline only matters when it
runs, no banking runs are scheduled, and the judge stack is still moving; the
trigger is the first consumer (a scheduled banking run, or a stabilized stack).
Pulled forward instead, as measurement: run the adopted judge over the ~75
banked clues to FLAG purge candidates and REPORT them — no deletions — as input
to the setter-vs-judge decision. **Setter-vs-judge decided by the user
(2026-07-06): after the idea-13 update, move to setter-side issues — the
residual judge misses (the definitional-completeness economy family,
HUMMINGBIRD-"Only") are mostly unimportant; PARK them, no idea 14.**

**Calibration #9 (2026-07-06, false-reject taste details):** HAMMER is "rather
flat" — "for driving nails" is a DIFFICULTY MODIFIER, not charm or essential
definition; with "nails" present the clue turns trivial ("Claw-backed tool"
already suffices). The RAT/ORCHARD/CACTUS/PIANO tails read the same way:
difficulty dials, not quality. GIFT "Inborn knack, as for languages" is a
reasonable clue (the panel's kill there is a real miss). WRAPS is fine either
way. Label surgery kept minimal per the diminishing-returns call: HAMMER and
WRAPS → soft; others unchanged. **Durable concept for the setter work: tails can
be difficulty modifiers — a legitimate dial the SETTER should control
deliberately (targeting a difficulty) rather than a flaw the judge prosecutes;
the liveliness turn's difficulty field is the natural consumer.**

**Rung 1 (queued FIFO behind the 26B measurement):** `confirm_multiturn_v3 .py`
= adopted v2e + liveliness turn (basis enum prize_fact/fun/elegance/ aha/none +
has_wordplay + difficulty easy/medium/hard, matching the bank's scale;
VENUS/FROST/BARK/WINDMILL fresh example pairs). Code gates: basis none →
fixable; '?' AND no wordplay → fixable. Offline checks green. Probe: gentune
--confirm-all --only on 14 words (~27 rows, only liveliness calls fresh ≈ 15
min). Targets: HONEY-bees, OCTOPUS-eight-armed, DENTIST-"Tooth doctor?",
SPIDER-"Eight-legged web spinner?" all die. Guards: every accept in the probe
holds — especially the six screen-recovery accepts and MOON "Night light?"
(has_wordplay must come back true); PILLOW is low-priority.

Validation plan: rung ladder on gentune — targets are the nine lost kills;
guards are the six recovered accepts plus every current v2e verdict — then
genhold at adoption, then a user checkpoint BEFORE any production wiring (spec
updates, difficulty consumers, pipeline_local surgery). Wording budget 6 tries,
per the standing user direction.

**Rung 1 result** (30 calls, 15 min): kills PERFECT 15/15 — all four screen
families die (HONEY-bees, OCTOPUS-eight-armed, DENTIST "Tooth doctor?", SPIDER
"Eight-legged web spinner?") and every kill guard held. Accepts 10/15: the
flat-gate re-killed VIOLIN "Smallest instrument in a standard string quartet"
and SPIDER "Eight-legged spinner of silk" (`basis: none` — the double-tax risk
from the pre-registration), while MOON/SPIDER-"Web developer?" held with
has_wordplay true. BILLION/PILLOW/ORCHARD are the parked economy family,
unchanged.

**Rung 2 (RUNNING at compact time; driver pid 13831, acquired 12:01, scorecard
lands in `logs/idea13_rung2_driver.log` + `idea13_rung2_*.jsonl` — NO watcher
attached, read the log directly).** ONE wording try only (user
diminishing-returns signal): prize_fact gains the learn test ("the solver
plausibly LEARNS from it; a fact everyone already has is not a prize" +
LOIRE/PARIS example pair). Target: VIOLIN recovers. SPIDER-spinner is an
accepted loss unless it flips free. Guards: the four kills + all rung-1 holds.
**Decision rule: if rung 2 seesaws (any kill guard breaks or ≥2 new accept
losses), fall back to the rung-1 wording — no further tries in this category.**
Then, with the better config: full gentune (--confirm-all) + genhold adoption
read; adopt if clearly better than the v2e cascade's 25/42 + 49/50 on totals;
then the banked-clue audit (flag and report, no deletions); then the SETTER
pivot, first thread = the difficulty-modifier concept (calibration #9).

**Rung 2 result** (30 calls, 16.5 min): WIN — rung-2 wording adopted. Kills
15/15, all four guards held. Accepts 11/15: VIOLIN "Smallest instrument in a
standard string quartet" recovered via the learn test (basis prize_fact), no new
losses. Residual misses unchanged and low-priority: BILLION, PILLOW, ORCHARD
(parked economy family), SPIDER-spinner (accepted loss). Liveliness category
CLOSED at 2 of the 6-try budget; `confirm_multiturn_v3.py` as-is is the adoption
candidate.

**Adoption read (full gentune + genhold, --confirm-all): ADOPTED.** v3
single-flow scores **29/42 accepts + 49/50 kills**, vs 25/42 + 49/50 for the v2e
cascade: four accepts gained, kills identical, and the one kill miss is the SAME
clue (UMBRELLA gust-tail, the long-standing accepted miss). Strictly better, and
it retires the screen's separate verdict policy entirely — the idea-13 goal.
Split: gentune 23/30 + 33/34; genhold 6/12 + 16/16. Genhold misses: three soft
rows (HAMMER, WRAPS, HAMMOCK), HUMMINGBIRD-"Only" (parked), CACTUS
(difficulty-modifier tail — setter-side, calibration #9), and MILLION-"The
jackpot Regis dangled" (real miss). Gentune misses are the known residual
economy family plus GIFT-"Inborn knack, as for languages" and RAT-"Informer who
turns on accomplices" (real misses, user-ruled diminishing returns). Runs:
`idea13_adopt_gentune` / `idea13_adopt_genhold` logs, 62 fresh calls, ~34 min.

## Bank audit (2026-07-06, flag-and-report — nothing deleted)

Adopted v3 judge over the 75-row `local/clue_bank.jsonl`, run cheap per the
user's cheaper-tests guideline: a 10-row spread full-protocol probe (~40 min)
found every flag came from the liveliness flat-gate — zero substitution, truth,
or economy-unanimous flags — so the remaining 65 rows ran the liveliness turn
only (1 call/row instead of 7; `bank_liveliness_audit.py`, cache-key-compatible
with a future full-protocol pass).

**Result: 23/75 flagged** — 22 flat-gloss (`basis: none`) + 1 unearned '?'
(DAISY "Subject of a petal-plucking game?"). Full list in
`logs/bank_liveliness_audit.log`. Reading: the bank predates the liveliness
gate, and about a third of it is flat-but-correct — evidence that the setter's
shortage is charm at generation time, not judge leniency; feeds
`#setter-tuning`. Caveat: several flags look like judge taste, not defects —
MELODY "Whistleable earworm", SELDOM "Once in a blue moon", ZED "That last
character, overseas", COURT "Royal residence or tennis arena" (double
definition, a legitimate form) — so the true flat rate is somewhat below 23/75.
Overlap check: the queue's screen-recall examples CENTURY, CHECK "Curb an
impulse", and STOCK "Simmering base for a stew" all flagged here too; MURMUR
"Low hum of a restless crowd" passed.

## Setter funnel evidence (2026-07-06, free transcript analysis)

`setter_draft_inventory.py` parses the July-1/2 `pipeline_*.log` transcripts
(the bank's provenance) into per-word funnel rows —
`logs/setter_draft_inventory.jsonl`. Funnel shape: 338 word runs over 150 words
→ 1391 drafts → 193 editor KEEPs (14%) → ~348 judge submissions (299 harvested +
49 single-picks) → 75 banked.

Qualitative read of the six flagged bank words that join cleanly to their runs
(the other 17 need a fuzzier join — clue text drifts between harvest and bank):

- **The self-editor already prosecutes flatness in its CUT rationales** ("lacks
  the required liveliness", "dictionary-flat", "flat and repetitive") — yet what
  it KEEPs is often still flat. Its liveliness bar diverges from the v3 judge's.
- **ASIDE is the clean smoking gun**: the editor CUT "Spoken directly to the
  gallery?" (vivid theater angle) and KEPT "Brief detour in a conversation" (now
  flagged flat). Substitution safety appears to outrank charm at KEEP time.
- **COURT shows the other failure shape**: every vivid draft genuinely failed
  the substitution test (part-of-speech mismatches); the flat double definition
  was the only survivor. There the draft pool, not the editor, is the shortage —
  vivid _and_ substitution-safe drafts are scarce.

Working hypothesis for `#setter-tuning`: liveliness and substitution safety
trade off in the draft pool; the editor's KEEP gate is substitution-first, so
flat-but-safe wins. Fix directions to design (user round pending): draft-stage
craft pushing vivid-but-substitutable shapes; editor treating flatness as fatal
at KEEP; and the difficulty-modifier dial (calibration #9) as an explicit
draft-stage control.

## Setter redesign — user framing + design round 1 (2026-07-06)

**User framing (verbatim intent):** the setter optimizes for expansiveness — if
unsure, keep; the judge scores. The goal is to send the best clues the setter
can generate (multiple per word is fine, up to a fixed cap), not to pre-filter.
No baking the judge into the setter. The setter needs brainstorm GUIDANCE
(unguided candidate generation yields exclusively poor clues): aim for a high
probability of at least a couple of interesting clues per word, even for the
hardest inputs. "Interesting" ≈ satisfying for the solver. The engineering
surface is both single prompts and the SEQUENCE of prompts that guides the
setter's thinking.

**Design-round rulings:**

- **Satisfaction is the target, not difficulty** (calibration #10). Difficulty
  was only ever a proxy — early drafts were unsatisfying by being far too easy,
  and difficulty is one component of satisfaction, far from the only one. Even
  satisfaction-as-target is worth validating before heavy investment.
- **Ranking owner and early-stop policy: undecided by design.** Postulate
  hypotheses, run the cheapest experiments that give an early signal, prioritize
  by expected value; more detailed signal only when worth it vs testing other
  ideas.
- **Setter `confidence` measures nothing usable**: the prompt says only
  `"confidence" (honest)` — referent unspecified — and all-CUT fallbacks are
  stamped low, so it entangles editor-survival. No free ranking-validity check
  exists; H2 (below) replaces it.
- **Self-editor fate: open**, pending the tradeoff walkthrough (kill authority
  vs reflection value vs metadata production vs ranker-repurposing).

**Design SETTLED 2026-07-06 — `cluegen/local/setter.md` governs from here; this
section is history.** Rounds 2-3 outcomes now live in that document: the
setter-judge boundary principle ("let the setter set and the judge judge"; light
judging inside setting OK, boundary open space), rank-by-satisfaction with
diversity (never-veto dissolved into the boundary question), goal restated as
throughput of satisfying clues (experiments exempt, principle 7),
autonomous-operation rules (blocker-only check-ins, $10 Fable/window, relaxed
gates: local batches self-launch, setter wording free, sealed spends at
adoption; training still gated), judge referenced via battery indirection,
setter-output properties (why-satisfying note; judge never sees metadata),
portfolio + cache-reuse + opportunistic-capture principles, and hypotheses
H1a/H1b/H2/H3/H4. Standing beliefs + self-served quota readings recorded in
`ceiling.md` (2026-07-06). Next: H1a 5-minute sanity check.

## H1a sanity check (2026-07-06, rung 0) — taxonomy seeding NO, material-first YES

Probe: `scratch/h1a_probe.py`, gemma4:26b-qat, word COURT (the known
draft-pool-shortage word), two turns (seed then pick-and-draft), baseline = the
4 COURT runs / 16 drafts in `logs/setter_draft_inventory.jsonl`. Footprint: 26B
resident, 6 short runs, ~15 min wall, lease held throughout.

Arms, in order (all transcripts in `logs/h1a_probe_COURT_*`):

- **basis** (H1a as written: one angle per satisfaction basis, ×2 samples):
  NEGATIVE. The model fills the rubric with the same four shallow senses
  (legal/tennis/royal/wooing) and labels them; "prize trivia" angles contain
  zero facts; two drafts duplicate known-flat baseline drafts verbatim ("Site of
  a lawsuit?").
- **mechanism** (one angle per `satisfaction.md` mechanism, whole list with
  examples): NEGATIVE. One-line vague angles; the "prize fact" leaked the answer
  ("Venue where the Supreme Court meets"). Same four senses.
- **micro-probe** (one-off: "list 8 pieces of vivid raw material — facts, tiny
  concrete scenes, frames, surprising senses"): the model produced genuinely
  vivid scenes ("the heavy rhythmic squeak of sneakers on polished hardwood").
  The vivid material EXISTS at 26B; angle rubrics suppress it.
- **material** (material turn + build-from-material drafts): mixed-negative, but
  diagnostic — the material turn regressed toward sense coverage, and the PICK
  step chose the four flattest pieces (same safety-first pathology as the old
  self-editor's KEEP gate). Vividness dies at selection and development, not
  only at generation.
- **vivid** (try 6: exact micro-probe wording for turn 1 + pick "most VIVID,
  generic sense description is an automatic skip" + printed clue must keep the
  material's image): WIN. Drafts: "Where rubber soles squeak on hardwood",
  "Where a gavel strikes a sound block", "Where nobles gather around a throne",
  "Where an umpire makes a call" — the liveliest COURT drafts of the campaign
  (bank's COURT entry is a flat double definition).

Read: H1a's premise was wrong in an instructive way — satisfaction taxonomy
labels are qualities to BE, not moves to MAKE, and seeding with them changes
labels, not content. The working formula is material-first: elicit concrete
material directly, select by vividness explicitly, and require the image to
survive into print. This dissolves H1a into a reformed H1 ("material-first
width") and connects to H1b (the material turn is the natural first expansion
round) and H3 (develop-from-material is a casting step).

Residual: all four winning drafts share a "Where X" shape — location-noun
monotony. Candidate refinement for after rung 1; not touched during replication
(clean comparison first).

Rung 1 (~30 min): the vivid arm, prompts UNCHANGED, across 6 words mixing
failure shapes — ASIDE (editor smoking-gun), SCORE (parse-missing hard word),
SELDOM + MELODY (banked-but-flagged-flat), NIL + LILY (words.in categories).
Compare per-word against inventory baseline drafts; grade liveliness in-session
(layer 3); judge scoring deferred to rung 2.

## H1 rungs 1–2 (2026-07-06) — three-turn funnel across 13 words

Rung 1 (vivid arm, 6 words): nouns clearly lift — ASIDE "A brief remark
whispered while others are frozen" beats its banked flat clue; SCORE "A
cinematic swell of violins?". Bonus width find: the material turn surfaced NIL's
modern name-image-likeness sense, absent from every baseline. Clean failure: the
adverb — every SELDOM draft was a scene-sentence that cannot substitute for an
adverb. Vivid material exists; the cast into part of speech is the missing step
— direct evidence for H3.

Casting arms on the two problem words:

- **cast** (single-turn: sentence-first substitution frame merged into the draft
  turn): traded vividness for legality — SELDOM gained adverbial openers but
  kept illegal scene tails; SCORE went flat ("Remarkable achievement"). The
  liveliness/legality tension can't be resolved in one turn.
- **develop** (three turns: vivid material → vivid drafts → dedicated re-cast
  turn, image held fixed): WIN on both. SELDOM produced "As infrequently as snow
  falls in the Sahara" — vivid AND adverbially legal; the simile shape is the
  natural adverbial cast. SCORE's re-cast turn did real verification (sentence,
  fail, re-cast) and trimmed toward economy while keeping images ("Tailor's
  marks for cutting cloth").

Rung 2 generation (develop arm, prompts unchanged, 13 words total: the six
rung-1 words + TWELVE THRICE GROSS FRANK CHASE VIOLET; ~12 s/word warm on 26B).
Layer-3 grade of the final lists:

- **Strong pools** (vivid + mostly legal): MELODY ("A staircase of pitches
  climbed by a singer"), ASIDE, COURT ("Where rubber soles squeak during play"),
  CHASE (verbs work: "Tail a scent trail through the brush"), SCORE, SELDOM.
- **Weak pools**: TWELVE regressed to enumeration + one answer leak ("Twelve
  inches in a foot" survived to the final list); GROSS regressed to flat glosses
  at re-cast; THRICE still shaky (adverb #2); FRANK missed the frankfurter sense
  entirely and confabulated biography in material.
- **Systematic weaknesses**: (a) the PICK step is the weakest link — for TWELVE
  it chose eggs/inches/months over apostles/jurors/clock-face material; (b)
  material confabulates facts (a "176-item" gross — it's 144); (c) re-cast
  sometimes mangles (VIOLET's awkward "…pigment color" casts) and passed a
  number mismatch ("Spring blossoms" plural for singular VIOLET).

Rung 2 measurement (in flight): top-2 finals per word (26 clues,
`h1_finals.jsonl`) through the v3 liveliness turn on 31B —
`bank_liveliness_audit.py` generalized to take a JSONL argument, cache-key
compatible — for a flat-rate directly comparable to the bank audit's 23/75. Log:
`logs/h1_finals_liveliness.log`. 26 calls on 31B, ~18 min.

**Result: 11/26 flagged (42%) raw, but the per-word reads carry the signal.**

- Coverage: 10/13 words have ≥1 unflagged final at top-2 depth. Failures: ASIDE
  (0/2 — judge calls even "Stage speech meant only for the audience" flat),
  TWELVE (0/2), FRANK (0/2).
- Head-to-head on the 7 bank-shared words (≥1 unflagged clue per word): new
  funnel 5/7 vs old funnel 2/7. The new funnel passes exactly where the bank
  rows are flat (COURT, SCORE, MELODY, SELDOM — e.g. COURT "Where rubber soles
  squeak during play" = elegance vs banked flat double definition) and fails
  where the old funnel's count-metonymy aha's won (TWELVE "Standard in a
  courtroom?"). GROSS: both produce one good clue.
- Judge upgrades vs my layer-3 grade: NIL "An athlete's endorsement deal" = aha
  (the name-image-likeness width find validated); THRICE 2/2 ok (aha) where I
  graded it shaky. Caveat both ways: liveliness-only — substitution legality
  unchecked ("Three times for an out?" passed but is grammatically doubtful as
  an adverb clue).
- TWELVE's failure is pure pick-step: the material turn HAD
  jurors/apostles/clock-face; the vividness-only pick chose eggs, inches,
  months. Same weakest-link as the earlier material-arm diagnosis.

Repair rungs (both run, wording budget then closed for the day):

- **diverse pick** (selection spreads across kinds of satisfaction, at most one
  per kind — principle 4): marginal. ASIDE gained a real aha ("Spoken directly
  to the house?" — essentially the vivid draft the old self-editor killed);
  MELODY held; TWELVE still never picked jurors/apostles; FRANK still
  all-adjective. New artifact: a re-cast final list included a raw sentence
  containing the answer — production needs a schema'd extract turn (the old
  funnel had one).
- **sense inventory first** (list every sense — slang, abbreviations, names,
  frames — then spread material across them): fixes width upstream. FRANK's
  inventory surfaced the frankfurter AND postal franking; TWELVE's surfaced
  jurors, the twelfth man, the zodiac. But conversion downstream fumbles
  non-imagery material at 26B: frankfurter became "Relating to a bratwurst" (the
  abbreviation conventions — "briefly", "for short" — are missing from the
  model's drafting vocabulary), and the jurors draft was dropped at re-cast.

Where this leaves H1 (all rungs, one day): the three-turn funnel is validated as
the winning shape and the remaining failures are localized to one step each —
width was material-level (fixed by inventory-first), flatness was pick-level
(mostly fixed by vividness/diversity selection), and the open residual is
CONVERSION: turning fact/count/abbreviation material into legal lively clue
shapes. Candidate next levers, in expected- value order: (1) a compact
craft-conventions note (abbreviation markers, count-metonymy shapes like
"Standard in a courtroom?") in the system prompt or develop turn; (2) revalidate
conversion on 31B — 26B is the iteration model and the conversion gap may partly
be model depth; (3) full-protocol judge run over a settled prompt stack as the
adoption measurement, which also feeds H4. H2 note: my top-2 picks stood in for
the unvalidated ranker throughout — ranking owner still open.

Conversion rung (same day, fresh sub-ladder, `conventions` arm — a compact
conventions block in the draft turn: shortening markers, count metonymy, name
frames; examples from non-test words):

- On 26B: TWELVE fixed (0 → ~4 viable: "Foot's worth of inches", "The hours that
  frame day and night", "A jury's full complement", "One less than a baker's
  dozen"); MELODY held; FRANK still failed — frankfurter material + the
  "briefly" convention both in front of the model, no clue produced. Two
  diagnosed tries → suspected model depth.
- On 31B (`H1A_MODEL` env override; ~3 min/word vs ~12 s warm on 26B): FRANK
  solved by WIDTH, not the shortening — fresh senses appear ("Ancestor of the
  French" = the Franks; "First name of 'Ol' Blue Eyes'"; a cleaner franking
  clue). SELDOM: "As often as a hermit updates his guest list". TWELVE holds.
  The re-cast turn reasons visibly better (explicit substitution sentences,
  self-correction against the keep-the-image rule). Funnel prompts transfer to
  31B UNCHANGED.
- Documented gap, parked: neither model ever uses the shortening convention
  ("briefly"/"for short") even when modeled directly. Not blocking — width
  covers the affected words.

Day's arc closed. The prompt stack as of tonight: sense-inventory material turn
→ diverse pick with conventions block → re-cast turn (`h1a_probe.py` arms
`senses`/`conventions`).

Adoption measurement, as a ladder (re-planned 2026-07-06 after the user caught a
skipped adversarial check — the original plan queued a multi-hour fresh-slice
full-protocol batch as the first rung; the review showed it is the LAST):

1. **Substitution-turn-only pass over the existing 26 finals** (~26 calls, ~20
   min on 31B, cache-compatible): measures the #1 known risk — legality — which
   the liveliness pass skipped (re-cast mangling, the passed plural mismatch,
   "Three times for an out?").
2. **Full protocol on the survivors only** (~10–15 clues, ~1 h): the adoption
   verdict on the tuning words, reusing every cached turn from rung 1 and the
   liveliness audit. Feeds H4 early-stop data and gives H2 the verdicts to
   validate a ranker against.
3. **Fresh word slice, full protocol** — parked behind rungs 1–2. It only tests
   generalization beyond the 13 tuning words, and H4 data from rung 2 may shrink
   it well below the multi-hour sketch. Sealed-set spend at that moment per
   setter.md.

Also queued: H1b iterated expansion vs the single material pass at equal
compute; user taste round on judge liveliness divergences (it flagged
"Midnight's hour" and "Stage speech meant only for the audience" flat, passed
"Three times for an out?" — setter.md open question on fine-grained ordering).

### Rungs 1–2 results (2026-07-06 evening)

Rung 1, substitution turn over the 26 finals (`h1_substitution_audit.py`,
`logs/h1_finals_substitution.log`, 26 calls ~25 min): 4/26 flagged. Two genuine
catches the layer-3 grade missed — both CHASE finals embed their own objects
("Tail a scent trail…" cannot substitute for the bare transitive verb); FRANK
"Without sugarcoating" correctly killed (prepositional phrase for an adjective).
One systematic finding, non-blocking now: FRANK "Sinatra's first name" flagged
`other_object → Frank Sinatra` — the substitution turn prosecutes the standard
name-word convention; ~a third of words.in is name words, so this is a likely
judge design-round item before rung 3 samples them. One leniency: the VIOLET
plural mismatch passed. Dual-pass survivors: 13/26 rows, 9/13 words.

Rung 2, full v3 protocol on the 13 survivors (battery set `h1survivors`,
`--confirm-all`, `logs/h1rung2_20260706-200704.jsonl`): **10 bankable, 3
fixable, 0 bad — 16 new calls, 8.2 min wall** (88 cache hits from the audits;
the cache-reuse principle paid for itself). All three fixables are economy-only:
the judge trims the scene-tails ("during play", "while walking home", "that
heightens the drama of a chase scene") and its trims read as improvements — the
funnel's known wordy-tail habit, a develop-turn economy instruction is the
queued next prompt lever. 8/9 words have a directly bankable clue; SCORE's lone
survivor is fixable-by-trim. Adverbs bank (SELDOM ×2, THRICE ×2), fresh senses
bank (NIL "An athlete's endorsement deal"). VIOLET "Spring blossoms…" (plural
for singular answer) passed the FULL protocol — number-agreement is a real judge
gap, filed with the name-convention item for a future design round (judge
prompts stay frozen).

Adoption read on tuning words: the funnel's judged output beats the old funnel's
banked output on the same words by every cut used tonight. Remaining before
adoption is generalization (rung 3, fresh slice), now sizeable from tonight's H4
data (13 verdict-ranked candidates + the pick order) — analyze offline first, no
new runs needed.

Process notes for the record: the first rung-2 launch ran as an in-session
background task and was reaped at ~15 min (the detached-runs rule exists for
exactly this); the relaunch then had its model unloaded by a lease swap ordered
AFTER the launch. Correct order: lease first (pid untracked), then detached
launch under caffeinate, then expendable watcher. Total waste: one model load.

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
