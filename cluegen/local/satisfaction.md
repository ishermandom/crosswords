<!-- Copyright 2026 Ilya Sherman (ishermandom@) -->
<!-- SPDX-License-Identifier: MIT -->

# What makes a clue satisfying

A taxonomy of the ways an American-style clue earns its keep. Its purpose is
defensive: a clue bank that leans on one trick reads tropey, however good each
clue is individually. Naming the bases of satisfaction and the mechanisms lets
us audit the bank for monoculture and keep the pipeline from rewarding a single
kind of cleverness.

Sources and their biases: the cloud pipeline's accepted clues (number words only
— a category that skews toward count-metonymy and arithmetic), the local bank
(small, friendly words), and general crossword craft. The banks are biased
samples; this document maps the mechanism space, not their empirical
distribution. Treat any one source — especially the cloud bank — as an input,
never the standard.

Why articulation matters (user, 2026-07-03): the ground-truth judges — the user
and Fable alike — distinguish satisfying from unsatisfying clues partly by "I'll
know it when I see it," which transfers to nobody. Progress on judge quality has
come from converting that tacit sense into named dimensions with graded example
pairs — a virtue named next to its near-miss (SNOOZE "Button smacked at 6:00,
6:09, and 6:18" vs "Alarm clock button"). The space is genuinely
multi-dimensional on both sides — many ways a clue earns its keep, many ways one
tanks — so expect refinement to be perpetual: each misjudged cluster is a
dimension not yet articulated, and the fix is naming the dimension, not
adjusting a verdict. Generating fresh graded pairs from the stronger judge
(cheap, avoids eval contamination) is the standing technique for pinning a fuzzy
line.

## The bases of satisfaction

There is no single thing a clue must do. A clue earns its keep on one or more of
these bases; the "aha" is the sharpest but not the only one:

- **The aha.** The surface points somewhere else; the answer is obvious only in
  retrospect; confirming it lands as recognition — "of course." Satisfaction
  scales with the distance of the leap and the fairness of the landing.
- **Elegance.** Phrasing so apt and economical that a straight clue pleases on
  its own — no misdirection required, just nothing wasted and nothing trivial.
- **Fair resistance.** A clue hard to get cold but gettable — and confirmable —
  with cross-check letters. The pleasure is a fight the solver can win.
- **Prize trivia.** The solver recalls or learns something interesting but not
  obscure; the clue is a small gift of fact.
- **Fun.** Humor or surprise in the surface itself — the clue is simply
  enjoyable to read.

What kills satisfaction is common to all bases: triviality (a dictionary gloss
with no other virtue) and unfairness (obscurity, inaccuracy, a referent the clue
never actually defines).

Anatomy, in any clue:

- **Anchor** — the knowledge that legitimizes the answer (a word sense, a
  cultural frame, a fact). The anchor must be checkable in retrospect.
- **Misdirection** — the wrong path the surface invites. Optional: clues
  standing on elegance, trivia, or fun may have none.
- **Surface** — the scene the words paint. It must read like something a person
  would say; any misdirection lives in its ambiguity, not its strangeness.

## The mechanisms

Mechanisms compose — a clue often pivots a sense _inside_ a frame — but each
names a distinct way a clue can work.

1. **Sense pivot.** The surface leads with one sense of a polysemous word; the
   answer uses another. "Bank deposit?" (SILT), "Curb an impulse" (CHECK), "A
   chill in the air?" (DRAFT).

2. **Frame anchor.** The answer's meaning lives inside a named cultural,
   regional, or professional frame; naming the frame makes it fair. "Love, at
   Wimbledon" (ZERO), "Behind, to a fighter pilot" (SIX), "That last character,
   overseas" (ZED), "A zero in cricket" (DUCK).

3. **Count or role metonymy.** The answer is defined by what it counts or the
   role it plays. "Innings in a standard ballgame" (NINE), "Standard in a
   courtroom?" (TWELVE), "Headcount in the U.S. Senate" (HUNDRED).

4. **Definition by example.** A specific instance stands in for the answer's
   class, usually flagged with a ?. "Jackson one might break?" (TWENTY — the
   bill), "One of the four Gospels" (MARK).

5. **Double definition.** Two unrelated senses joined in one surface, each
   independently defining the answer. "Royal residence or tennis arena" (COURT).

6. **Conceptual reframe.** An abstract property described concretely, as a small
   riddle. "It separates the positives from the negatives" (ZERO), "It's next to
   nothing" (ONE), "When both hands are up?" (TWELVE).

7. **Metaphor as definition.** A figurative description that is literally apt on
   inspection. "Prehistoric time capsule?" (AMBER), "Ships launched by a face?"
   (THOUSAND).

8. **Vignette.** A tiny scene the answer completes; satisfaction comes from
   aptness and vividness rather than misdirection. "Reaction to a jump scare"
   (GASP), "Heads down!" (DUCK).

9. **Relational pivot.** The answer defined by its relation to another quantity
   or item, where the relation itself carries a pivot or surprise. "One-twelfth
   gross?" (DOZEN), "Half a deuce?" (FORTY — the tennis score). A bare equation
   with no pivot ("Twenty times two") is the flat end of this mechanism, not a
   different one.

10. **Prize fact.** A straight clue carried by interesting, checkable trivia —
    no misdirection, satisfaction from the fact itself. "Spinal Tap amp's top
    setting" (ELEVEN), "Warhol's allotment of fame, in minutes" (FIFTEEN), "Age
    of ABBA's dancing queen" (SEVENTEEN).

A property that cuts across mechanisms: **under-determination is a virtue, not a
flaw** (user calibration, 2026-07-04). A true clue that also fits other answers
— "When shadows stretch" reads as DAWN as well as DUSK — is doing extra work: it
forces the solver to cross-check against crossing answers, which is where a
crossword's difficulty is supposed to live. Judges test truth, not uniqueness;
prosecuting "several answers fit equally well" kills exactly the clues that
resist longest.

## Failure modes, restated as missing pieces

- **Flat gloss** — no leap and no other virtue; a thesaurus entry.
- **Unearned ?** — the mark promises a leap the clue doesn't make.
- **Trivia wall** — an anchor too obscure to check in retrospect; the leap is
  unfair, so the landing never comes.
- **Associated referent** — the clue defines something _near_ the answer, not
  the answer; the landing collapses on inspection.
- **Idiom fragment** — the anchor exists only inside a longer phrase.

## Uses in the pipeline

- **Diversity audit.** Periodically tag banked clues by mechanism and look at
  the spread. The monoculture most likely here is sense-pivot-plus-?; the
  number-word categories tilt toward count metonymy instead.
- **Breadth in the angles turn.** If the setter needs nudging, show it the whole
  list — never one favored mechanism. The standing rule stands: no
  single-mechanism prompt hints, in setter or judge.
- **Angle-distinct depth.** Two clues for the same word are genuinely distinct
  when the anchor or the mechanism differs — a sharper test than surface
  wording.
- **Judge calibration balance.** The judge's few-shot examples should span
  mechanisms, or "satisfying" quietly narrows to whichever mechanism the
  examples exhibit.

## Snapshot: local bank distribution (2026-07-02, 32 records)

Tagged by dominant mechanism: frame anchor 7, sense pivot 6, vignette 6,
count/role metonymy 4, metaphor 2, conceptual reframe 2, plain definition 2,
definition by example 1, double definition 1, relational pivot 1. Tags are
judgment calls at the margins. A reasonable spread for the friendly categories;
count metonymy will grow as number words land. Re-tag after the bank changes
shape — this table is a dated snapshot, not a living count.
