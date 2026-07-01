# Local model ceiling — spec

_Scope: goals, quality yardstick, and operating rules for an autonomous
exploration of how good locally-generated crossword clues can get, using the
cloud pipeline (`cluegen/cloud`) as the reference bar. The tool's own
requirements stay in `spec.md`._

## Goal

Find the practical quality ceiling of the local Gemma-4 stack for crossword clue
generation. This is not a parity project: the cloud pipeline's Fable output is
the inspiration and reference bar, and is likely unreachable. The question being
answered is how close the local stack can get through prompt and pipeline
iteration alone, and where it plateaus.

**Why:** the cloud pipeline generates excellent clues but consumes ~3–6% of a
plan-quota window per word; running it over the full 547-word `words.in` is
cost-prohibitive. Local inference has zero marginal cost. Knowing the local
ceiling determines what role local generation can play — and whether levers
beyond prompting (fine-tuning, a different harness) would be worth their cost.
Those levers are out of scope for autonomous action — see _Autonomy rules_.

The deliverable is a measured quality curve — baseline, then per-iteration
scorecards — and a plateau assessment, built in prototype-quality code.

## Milestone and scope

One milestone is in scope: **prototype-quality exploration of generating a
single American-style clue at a time**, iterated until quality plateaus, ending
in a manual check-in with the user. Everything beyond that — cryptic-style
clues, multi-clue-per-word output, bank-mergeable JSONL, production-code
integration — is aspirational at best and stays unscoped until that check-in.

- **Codebase:** probe scripts under `cluegen/scratch/`, at the exploratory bar.
  Per the standing prototyping rule, probes do not import from production code —
  prompt text is copied in directly. The production package
  (`cluegen/local/cluegen/`) is not modified during this milestone.
- **Quality bar for a clue:** `CLUE_SPEC.md` Part A (American-style) — the same
  editorial standard the cloud bank enforces, including the craft invariants and
  the difficulty dial.
- **Reference material:** `cluegen/cloud/` is a read-only reference throughout —
  its prompts and spec are read and rendered by scratch harnesses, never edited.

## Quality yardstick

Layered, cheapest signal first. Each layer gates what reaches the next; only the
top layer spends meaningful plan quota.

1. **Mechanical checks** (free, pure code): answer leakage, uniqueness — the
   single-clue-relevant subset of the checks in `cloud/mechanical_checks.py`.
2. **Local judge** (free, local tokens): local model validation calls drive
   day-to-day prompt iteration. Known limitation: a local judge shares the
   generator's blind spots, so its verdicts rank iterations rather than certify
   quality.
3. **In-session Fable-grade review** (session tokens): Claude blind-grades small
   samples against `CLUE_SPEC.md` in conversation. Quota discipline: samples of
   ~10 clues or fewer, terse tabular formats, no re-reading of full generation
   logs.
4. **Cloud-verify checkpoints** (plan quota, capped): the cloud pipeline's
   verify prompt rendered over an eval sample via `claude -p`, producing the
   same accept/revise/reject verdicts the bank uses. This is the metric of
   record.

### Eval set and metric

Eval words come from the cloud project's own list, `cloud/words.in`, sampled
across its word categories — numbers and ordinals, words that double as names,
flower names, polysemous short words, spelled-out letters — not just the number
words the cloud bank happens to have processed first (user direction
2026-07-01). Words with accepted cloud clues additionally support a same-word
comparison against Fable output; include a few in every sample. Checkpoint
samples are sized to fit the quota cap — start at 8–12 words; a full-eval-set
run needs explicit approval.

The primary metric is the **bankable rate under quality-first judging**
(clarified 2026-07-01: the goal is high-quality, satisfying-for-a-solver clues;
label accuracy is secondary). The judge evaluates the clue TEXT on the craft
invariants (accuracy, natural surface, economy) and solver satisfaction
(liveliness, fair aha when misdirection is present), at the difficulty the judge
itself assigns — a clue mislabeled by the generator is relabeled, not failed.
The `?` convention stays a text criterion, since it prints with the clue.
Generator-label accuracy is tracked as a secondary, non-gating series.

Rationale: the bank's verify prompt enforces quality and label coherence
together — sound when Fable both writes and labels, but on local output it
conflates the two. Checkpoint 1 re-analysis (see the campaign log): 13 of 21
revises were label/metadata-only; quality-adjusted, the flat curve becomes a
real ordering that matches in-session grading. The cloud pipeline's own accept
rate on the same words (~88–97% per batch) remains the reference ceiling.

### Quota rules

- Every `claude -p` run, single call or batch, is user-gated: propose the run —
  scope, clue count, dollar estimate — and launch only on the user's go.
  Report-only on completion. Rationale (2026-07-01, checkpoint 1): Claude cannot
  reliably calibrate session-quota cost — a run estimated at ~10% of a window
  consumed most of one ($2.65 / 7 calls). Percent-of-quota caps are therefore
  not an operational control; the gate is the control. Per-call dollar/token
  usage still gets logged for the record.
- In-session review manages its own cost by sample size and format, per layer 3
  above.

## Autonomy rules

**Ask before, always** (a stop-point ends the work turn with a question):

- Pulling or downloading any model, of any size, by any mechanism.
- Switching inference off Ollama (e.g. to `llama-server` or `mlx-lm`) — even
  though `toolchains.md` argues for it; that decision is the user's.
- Any fine-tuning work, local or cloud.
- Editing anything under `cluegen/cloud/`.
- Exceeding the checkpoint quota cap, or running `claude -p` outside a
  checkpoint.
- Merging the campaign branch into `main`.
- Any work beyond the single-American-clue milestone.

**Allowed without asking:**

- Prompt iteration without limit — task wording, personas, turn structure — in
  scratch probes. (This campaign's core work; the usual
  don't-iterate-prompt-wording default is lifted here.)
- Long local batch runs, when judged genuinely worth their cost — the costs
  being thermal throttling on the fanless Air _and_ slow iteration. Record the
  cost–benefit call in the campaign log before starting one.

**Server management:** Claude runs the Ollama server itself as needed —
`OLLAMA_MODELS=/Users/Shared/ollama/models ~/tmp/ollama serve` from the
`claude-sandbox` account (user authorization 2026-07-01) — and may bring it up
and down freely. Pulling models through it remains forbidden, per the ask-first
rule above.

## Model tier

All models below are already installed; the tier requires no new pulls.

- **Smoke / plumbing:** `qwen3.5:2b` — pipeline checks where output quality is
  irrelevant.
- **Iteration:** `gemma4:26b-qat` — fast prompt-shape iteration.
- **Quality of record:** `gemma4:31b-qat` — the dense model `toolchains.md`
  fixes as the no-compromise choice, in its recommended QAT quant. Every
  reported quality number and every checkpoint runs on it.

Prompts tuned on 26B must be re-validated on 31B before any checkpoint — the MoE
and dense models have different failure modes (see `toolchains.md` §4.5). The
long-conversation speed cliff observed on the 31B MLX variant (`tasks.md` —
Findings) may or may not apply to the QAT quant; keep conversations short until
measured.

## Git isolation

The campaign runs in a dedicated git worktree on its own branch, leaving the
main checkout free for interactive use:

- Branch `local-ceiling`, based on `main`; worktree as a sibling directory of
  the repo.
- Commits land on the branch at normal cadence; scratch probes follow the
  exploratory bar, so committing them needs no review.
- Merge to `main` only after review with the user at the milestone check-in;
  abandoning the campaign is deleting the worktree and branch.

## Reporting

Milestone reports are non-interrupting: appended to
`cluegen/local/ceiling-log.md` on the campaign branch (committed, so it is
inspectable from the branch or tailed directly in the worktree), with only a
one-line pointer in chat.

A report records: what changed since the last report, measurements (accept rate,
verdict mix, sample), interpretation, and the next step. Report occasions: eval
harness working, baseline measured, each prompt-iteration scorecard, and any
stop-point or blocker.

## Success and stop criteria

There is no fixed numeric target; the local ceiling is the empirical result this
campaign produces. The campaign ends in a manual check-in with the user when
single-American-clue quality plateaus — operationally, when two successive
prompt-iteration cycles at the quality-of-record model show no accept-rate
movement, or when remaining ideas look exhausted. It pauses earlier whenever a
stop-point is hit.

At the check-in, the campaign log holds the full quality curve and a
recommendation on whether further levers (fine-tuning, harness change,
Stage-2-style ambitions) look worth pursuing.
