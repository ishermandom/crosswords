# Crossword clue generator

**Status: work in progress**

Generates NYT crossword-style clues for acrostic puzzle answer words. Given a
list of answers and a target difficulty day, the tool produces one or more clues
per word. Runs entirely locally via [Ollama](https://ollama.com/) — no external
API calls, no per-use cost.

<!-- TODO: Add setup / installation instructions once dependencies stabilize
     (Python version, Ollama setup, model pull commands). -->

## Goal

Save puzzle constructors from writing clues by hand while producing clues that
are genuinely enjoyable to solve. The primary quality criterion is _enjoyable
while remaining solvable_ — not just grammatically correct, but worth the aha
moment.

The target style is an open mix: straight definitions, fill-in-the-blank,
wordplay and double meanings, and light cryptic elements. The tool does not use
the source quote or author as context; clues are generated from the answer word
alone.

## Difficulty

Calibrated to the NYT crossword difficulty scale. The same answer word can
appear in any day's puzzle — what changes is the clue. Difficulty is
multi-sourced: clue indirection, reference breadth, and (at the puzzle level)
grid architecture and answer length all contribute. Not every clue in a puzzle
needs to hit the day's maximum; the target is a zone, not a fixed point.

| Flag  | Character                                                              |
| ----- | ---------------------------------------------------------------------- |
| `Mon` | Direct and unambiguous; plain definitions                              |
| `Tue` | Slightly tricky; mild misdirection acceptable                          |
| `Wed` | Middle of the scale; beat of recognition required ← **default**        |
| `Thu` | Lateral leaps expected from some clues; genuine aha moments            |
| `Fri` | High license; misdirection and non-obvious angles; real thought needed |
| `Sat` | Maximum license; every difficulty lever available                      |

### Day targets

**Monday** — The most direct path to the answer: plain definitions, the obvious
angle. A solver should land on it immediately without deliberation. Wordplay is
acceptable when the mechanism is immediately apparent, but misdirection is not
the goal — clarity is. References should be universal; nothing that requires
specialist knowledge. The target is accessibility; even within the natural
variance of a full puzzle, clues should stay close to that end.

Within that band there is still a meaningful distinction between a well-crafted
Monday clue and a dull one. "Accessible" does not mean "inert." Failure modes to
avoid: dictionary-entry phrasing ("One who bakes" for BAKER), angles so generic
they provide no texture ("Musical instrument" for PIANO), and clues that hand
the solver the answer before they have had a moment to engage. A well-crafted
Monday clue leads cleanly to the answer but gives the solver a small beat of
arrival — warmth in the phrasing, a specific rather than generic angle, or a
familiar phrase that clicks into place. The answer should feel obvious in
hindsight, not before the clue is read.

**Tuesday** — One step off the most obvious angle. A mild indirection or
secondary meaning is welcome — the surface can suggest one domain while the
answer comes from another — but the connection should click quickly without
requiring a genuine leap. References can stray slightly beyond universal but
should remain broadly accessible. Most clues should resolve without
deliberation; a few can require a brief pause.

**Wednesday** — Middle of the scale. Aim for clues that require a beat of
recognition from a practiced solver: not the first and most obvious angle, but
not a tremendous leap either. Wordplay and mild misdirection are welcome and
common, though not required on every clue. References can go beyond universal —
assume a solver who does the puzzle regularly. Some clues in a Wednesday puzzle
will be simpler, some harder; the target is the zone, not a fixed point.

**Thursday** — The first day where lateral leaps are expected from some clues.
The surface can confidently lead elsewhere before the answer clicks; genuine aha
moments are the goal. The mix still varies — some clues will be more direct —
but the harder ones should genuinely mislead. References can be moderately
specialized. Thursday puzzles typically have a theme, which often provides a
structural hook that helps once cracked.

**Friday** — High license across all axes: misdirection, non-obvious angles, and
moderately specialist references are all available. The obvious answer is often
wrong; the surface should feel natural while pointing in the wrong direction.
Most clues should require real thought from a practiced solver, but the mix
still varies — not every clue needs a trick. Friday puzzles are themeless;
difficulty comes from clue craft and the architecture of an open grid.

**Saturday** — Maximum license: misdirection, specialist or niche references,
unexpected angles, and precise-but-non-obvious definitions are all fair game.
The obvious answer is usually wrong. Not every clue needs to be devious —
Saturday difficulty also comes from the puzzle's architecture (longer entries,
fewer black squares, fewer easy footholds) — but individual clues can reach as
far as they like. The mix within a Saturday puzzle still varies; some clues will
be relatively clean. What distinguishes Saturday is the absence of easy entry
points and the full availability of every difficulty lever.

## Process

The generator uses a two-stage pipeline: a multi-turn brainstorm that produces
candidate clues, followed by independent validation of each candidate.

### Stage 1 — Brainstorm

A multi-turn conversation with a constructor persona works through the following
turns in order. Each turn targets one cognitive mode to prevent the model from
anchoring on its first mechanism and producing variations on a single idea.

1. **Answer analysis** — parts of speech and all senses (including rare and
   figurative), morphological variants, near-miss answers of the same letter
   count, and semantic fields. Establishes the full space before any clue
   writing begins.

2. **Mechanism brainstorm** — 20+ distinct mechanisms named and described, but
   no clues written yet. Separating mechanism discovery from drafting prevents
   the model from committing to its first framing. Mechanisms span wordplay
   types (double meaning, pun, pivot on secondary meaning) and surface
   misdirection types (part-of-speech switch, domain switch, idiom → literal,
   etc.).

3. **Mechanism filter** — culls to a shortlist of 5–7 strongest mechanisms, plus
   1–2 rough-but-high-ceiling ideas. Biases toward novelty and surprise; away
   from the obvious default angle.

4. **Clue drafting** — 3–5 draft clues per surviving mechanism, each labeled
   with its mechanism type. Surface reading quality matters here: clues should
   read as natural language.

5. **Solver simulation and credibility check** — for each draft, lists plausible
   alternative answers a real solver would try before landing on the correct
   one. Flags clues where the misdirection is invented rather than genuine
   (alternatives that aren't real words or phrases).
   <!-- TODO: Decide how to scope this turn. With 5–7 mechanisms × 3–5
        drafts each, up to ~35 clues may need simulation. Options: filter
        more aggressively in turn 3, or accept a heavier turn 5. -->

6. **Refinement and diversity audit** — tightens wording, strips filler.
   Critically, checks that surviving clues use _different mechanisms_, not just
   different phrasing of the same one. The common failure mode without this step
   is producing many near-identical clues that exploit the same angle.

7. **Polish** — applies stylistic conventions as a final pass: the `?` suffix
   when warranted by the day and the wordplay present, the substitution test
   (clue and answer must be interchangeable in a sentence), abbreviation
   signals, and other mechanical rules. Keeping this separate from earlier turns
   lets the creative turns stay focused on ideas.

8. **Extract** — produces structured output (a JSON list of candidate clues) for
   handoff to Stage 2.

The system prompt uses a **constructor persona** calibrated to the target
difficulty day. The day description tells the constructor how much misdirection
is expected, what counts as an appropriate reference, and how deceptive the
surface should be.

<!-- TODO: Document the day descriptions once they are finalized. The key
     axes are: level of misdirection expected, whether the obvious reading
     should be correct, and what reference breadth is appropriate. -->

### Stage 2 — Validation

Each candidate clue is validated independently through two calls, each with a
different persona and different information:

**Solvability check** (blind) — a solver persona that does _not_ know the
answer. Given only the clue text and letter count, it reasons through
interpretations and produces a ranked guess list. The clue passes if the correct
answer appears within the top N guesses. This tests whether a real solver could
arrive at the answer without help from crosses.

**Quality evaluation** (answer-aware) — an editor persona that knows the answer.
Checks five stylistic conventions (tense agreement, wordplay indicator,
abbreviation signaling, fill format, genuine alternatives) and scores six rubric
dimensions (angle craft, misdirection, elasticity, reference accessibility,
surface coherence, fairness of deception). Scores are checked against the
expected range for the target difficulty day.

The two checks provide different signals that the other cannot: solvability
catches clues that are too obscure or ambiguous to reach; quality catches clues
that are solvable but stylistically weak or convention-violating.

<!-- TODO: Document the day profiles (expected rubric score ranges per day)
     once they are calibrated against a golden set. The current profiles in
     quality.py are initial estimates. -->

## Usage

```
# Full pipeline: generate and validate
clue-gen run --words words.txt --difficulty Thu --model gemma4:26b-qat

# Single word
clue-gen run --word MATCH --difficulty Wed --model gemma4:26b-qat

# Generation only (no validation)
clue-gen generate --word MATCH --difficulty Mon

# Validate an existing clue
clue-gen solvability --clue "Starts a fire?" --answer MATCH --difficulty Wed
clue-gen quality --clue "Starts a fire?" --answer MATCH --difficulty Wed
```

Output is JSON (single word) or JSONL (word list), written to stdout. Each run
writes a timestamped debug log to `logs/`. Pass `--verbose` to also show debug
output on the console.

## Prototyping

Active prompt development happens in `prototyping/` rather than the production
codebase. Probe scripts there run individual pipeline turns directly against
Ollama for fast iteration:

```
python prototyping/probe_make_clue.py --answer MATCH
python prototyping/probe_quality_multi.py --clue "Starts a fire?" --answer MATCH
```

Findings from probes are incorporated into the production prompts once
validated. The task tracker (`tasks.md` at the project root) tracks what is in
progress and what is pending.

## References

Primary sources on NYT crossword construction and clue standards:

- **[NYT puzzle submission guidelines](https://www.nytimes.com/article/submit-crossword-puzzles-the-new-york-times.html)**
  — official requirements for puzzle submission, including format, grid rules,
  and editorial standards.

- **[NYT: How to write crossword clues](https://www.nytimes.com/2018/07/11/crosswords/how-to-make-a-crossword-puzzle-4.html)**
  — NYT guide on clue craft: grammar rules, wordplay conventions, what makes a
  clue fair.

- **[NYT: How to edit crossword clues](https://www.nytimes.com/2018/08/17/crosswords/how-to-make-a-crossword-puzzle.html)**
  — companion piece on the editorial pass: what Shortz and Fagliano look for and
  fix.

- **[XWordInfo: Shortz and Fagliano edit a puzzle](https://www.xwordinfo.com/Editing)**
  — direct editorial commentary clue by clue from the NYT editors. The most
  concrete primary source on what passes and what doesn't.

- **[Amuse Labs: 24 tips for writing crossword clues](https://amuselabs.com/resources/guides/writing-crossword-clues/)**
  — practitioner rules from an NYT constructor, numbered and specific. Covers
  grammar matching, the substitution test, abbreviation signaling, and more.
