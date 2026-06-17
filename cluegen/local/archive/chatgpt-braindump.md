Goal

Generate NYT-style crossword clues, especially late-week quality, for a known
answer.

The target is not:

immediate solvability unique answer from the clue alone

The target is:

elegant clue surfaces productive ambiguity satisfying resolution via cross
letters a strong solver experience Key Insight: Optimize for Solver Experience

A great clue often creates:

plausible interpretation → uncertainty → cross-checks → "ohhh"

Not:

obvious clue → obvious answer

Cross letters are part of the clue. A clue does not need to uniquely determine
the answer in isolation.

What We Learned About Good Clues Weak clues definitional factual arithmetic
obvious category labels hedge words ("sometimes", "in many places", etc.)

Examples:

Voting age One shy of nineteen Two times nine

These might be acceptable early-week clues but are not interesting.

Strong clues often involve:

1. Productive ambiguity

Example:

"Prime" → THREE, FIVE, SEVEN, etc.

The clue does not uniquely identify the answer. Crosses do the final work.

2. Domain reinterpretation

Example:

Golf: holes in a round (9 vs 18) Baseball: innings per side vs total innings 3.
Linguistic ambiguity

Example:

"nibling" → NEPHEW homophones dual-meaning words 4. Cultural references

Example:

"Dewey, to Donald" → NEPHEW

These often outperform generic clues because they are specific and memorable.

5. Strong alternate interpretations

A clue should ideally create:

multiple plausible answers not just one obvious answer and one correction

A clue with only:

9 18

is often less interesting than a clue with a wider plausible search space.

Important Insight About Difficulty

We originally optimized for:

strong wrong answer commit → break → snap

This was too narrow.

The updated target is:

elegant ambiguity that resolves cleanly through crosses

A clue does not need a single dominant wrong answer.

Evaluation Criteria LS — Lure Strength

Does the clue naturally suggest plausible fills?

High:

several reasonable answers come to mind

Low:

answer is obvious EL — Elasticity

Does the clue support multiple coherent interpretations?

High:

crane = bird or machine prime = number or excellent

Low:

purely definitional CP — Cross-check Payoff

Do crosses meaningfully resolve ambiguity?

High:

several plausible answers collapse to one

Low:

clue already determines answer RF — Resolution Fit

Once solved, is the clue:

exact fair satisfying

Must be high.

SQ — Surface Quality

Natural language. No awkward wording. No editorial hedges.

IN — Inevitability

After enough crosses, does the answer feel inevitable?

Bullshit Rating

Very important.

Many clue ideas sound plausible but fail solver simulation.

For each clue ask:

Are the alternative answers real? Would a solver actually think of them? Is the
ambiguity genuine? Is the resolution exact?

Do not invent solver behavior.

Major Discovery

The model often generates:

plausible explanations weak clues

Why?

Because clue writing is:

search + evaluation

not:

generation

LLM Failure Mode

The model can explain a rubric very well.

But generation requires:

exploring many candidates comparing alternatives rejecting most outputs

The model does not naturally do that.

It tends to:

find one mechanism produce variations overrate them

Example:

many versions of "Down, on a map" Recommended Workflow Phase 0

Analyze answer:

part of speech morphology near-miss answers Phase 1

Generate 20–40 mechanisms.

Examples:

map reinterpretation idiom → literal bird migration cultural reference homophone
domain ambiguity

Do not generate clues yet.

Phase 2

Filter mechanisms.

Keep:

strongest plus a few high-risk/high-upside ideas

Do not kill weird ideas too early.

Example:

"crane movement, seasonally"

This may be rough but has higher ceiling than many safe ideas.

Phase 3

For each surviving mechanism: Generate 5–10 clue candidates.

Wide exploration.

Phase 4

Run solver simulation.

For each clue:

List:

plausible answers alternate interpretations

Evaluate:

LS EL CP RF Phase 5

Refine survivors.

Multiple passes:

tighten wording improve ambiguity improve surface Phase 6

Editor pass.

Remove:

filler language hedge words unnecessary explanation

Make surface feel natural.

Phase 7

Diversity audit.

Two clues are not different merely because wording differs.

Check:

mechanism decoy set reinterpretation path

If those are the same:

keep only the better clue Phase 8

Final credibility check.

Ask:

Would an actual solver plausibly experience this clue the way I claim? Important
Taste Preference Discovered

High-ceiling clue directions often come from:

unusual ambiguity dual-meaning nouns narrative framing cultural references
language-level reinterpretation

Example that sparked discussion:

"Crane movement, seasonally"

This is probably not yet a finished clue.

But it points toward:

bird vs machine ambiguity migration elegant understatement

This kind of clue family is much more interesting than straightforward
definitions.

Key Philosophy

Do not optimize for:

uniqueness of answer from clue alone

Optimize for:

a small cloud of plausible answers that collapses elegantly through crosses

Cross letters are part of the solving experience.

The goal is not perfect clue determinism.

The goal is a satisfying solver journey.
