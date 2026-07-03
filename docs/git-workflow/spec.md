<!-- Copyright 2026 Ilya Sherman (ishermandom@) -->
<!-- SPDX-License-Identifier: MIT -->

# Git workflow for agent-managed repos — spec

_Scope: how history is structured, protected, and landed in repos where agents
perform most git operations, including on `main`. The extended reasoning behind
every decision here — mechanisms, surveyed alternatives, tradeoff analysis — is
in `rationale.md`; this document is the concise normative record. Adopted
2026-07-03 for the crosswords repo; migrates to dotfiles as the home for all
personal repos (task queued)._

## Goal

Agents manage every ref, `main` included, with **structural** guarantees —
enforced by the server, not by client behavior or human vigilance — that:

1. published history is append-only, and
2. nothing superseded ever loses its name.

Friction on the happy path is treated as a defect: a protection that fires on
routine legitimate work gets redesigned, not tolerated.

## Invariants

1. **`main` is strictly linear.** Every commit is a landing that passed the
   presubmit at its final content; merge commits never appear.
2. **`main` is append-only.** Force-pushes and deletions are rejected by the
   server for every pusher.
3. **Superseded chains keep names.** Any branch rewrite or deletion leaves the
   prior tip reachable under `refs/archive/**`.
4. **The archive is immutable.** `refs/archive/**` accepts creations only;
   updates and deletions are rejected by the server.
5. **Rewrites cannot clobber unseen work.** The only permitted force form is
   `--force-with-lease`, which the remote rejects unless its tip matches the
   pusher's last-fetched state.

## History model

- **`main`** — a chain of verified landings; the project's audit log. With
  per-commit session trailers, `git log main` is also the record of which agent
  session landed what, in total order.
- **Branches** — workspaces, not history-of-record. One branch = one worktree =
  one writer (standing practice). Mid-flight, branches update from `main` by
  merging it in — append-only, conflicts resolved once — and those merge knots
  never reach `main` (they are dropped at landing).
- **`refs/archive/<branch>/<utc-timestamp>`** — the permanent home of every
  superseded chain: pre-landing branch states, retired branches. Browsable with
  `git ls-remote origin 'refs/archive/*'`; fetchable and diffable like any ref.

## Enforcement layers

Protections are layered by strength; the load-bearing ones live at the server,
where no client mistake can bypass them.

1. **Server rulesets (absolute).**
   - `main`: require linear history + block force pushes + block deletions.
     Scoped to `main` only — branches are explicitly exempt (the earlier
     all-branches linear-history rule is retired; it forced mid-flight rebases,
     the workflow this design eliminates).
   - `refs/archive/**`: creation allowed; updates and deletions blocked.
2. **Auto-archive Action (dragnet).** A GitHub Actions workflow fires on
   force-pushes and ref deletions and snapshots the event's `before` SHA to
   `refs/archive/<branch>/<timestamp>` via the API. Every rewrite is archived
   regardless of which client performed it — the land script is a convenience,
   not the guarantee. Reactive by nature: an Actions outage leaves a gap,
   covered in practice by the pushing clone's reflog (~90 days).
3. **Land script (curated path).** `scripts/land.py` performs the landing ritual
   (below), producing legibly named archives and running the presubmit. Agents
   and humans both land through it.
4. **Client git gate (hygiene; dotfiles, applied at migration).** Allow
   `push --force-with-lease` to `refs/heads/*` except `main`; block bare
   `--force` everywhere (it has no legitimate use over the lease form);
   history-rewriting plumbing (`filter-branch`, `reset --hard` on shared state)
   stays gated. Under layers 1–2 the gate is defense in depth, not the last
   line.

Considered and not adopted (full analysis in `rationale.md`): a self-hosted bare
hub as origin with pre-receive archive hooks — prevention-grade rather than
reactive, rejected as infrastructure weight disproportionate to a solo setup; a
never-prune local mirror — recorded as optional future depth, not part of the
current design.

## Landing flow

`scripts/land.py`, run from the branch's worktree:

1. **Replay**: rebase the branch's unlanded commits onto `main`'s tip
   (update-merge knots drop out; `rerere` replays previously resolved
   conflicts).
2. **Presubmit**: run the full check suite (tests, mypy, ruff) once, on the
   final replayed state. Per-commit verification of the chain is deliberately
   not the default — solo-scale cost/benefit, revisit trigger recorded in
   `rationale.md` — but is available as a flag for landings where chain
   bisectability matters.
3. **Land**: fast-forward push `main`. A rejection means another landing won the
   race; re-replay and retry (fast-forward-only `main` serializes concurrent
   landings like a commit queue).
4. **Archive**: push the branch's superseded (pre-replay) chain to
   `refs/archive/<branch>/<timestamp>` — an ordinary append-only push.
5. **Reset**: move the branch to sit atop new `main` (lease-protected). A live
   branch is always exactly "`main` + unlanded work," which is what dissolves
   the duplicate-commit bookkeeping that repeated landings from a kept-alive
   branch would otherwise accumulate.

Each step refuses loudly on failure; no step destroys anything (the archive push
precedes the branch reset).

## Adoption and migration

- **Now (crosswords):** rulesets created in the GitHub UI (user-run);
  `.github/workflows/archive-rewrites.yml`; `scripts/land.py`; this spec and
  `rationale.md` under `docs/git-workflow/`.
- **At dotfiles migration (task queued in `cluegen/local/tasks.md`):** these
  documents and the land script move to dotfiles as the all-repos standard;
  `gh-protect.sh` gains audit assertions for the ruleset trio and archive
  namespace; the git gate narrows per layer 4; `rerere` is enabled in global git
  config.

## Rejected alternatives

Recorded so they are not re-litigated casually; each has a full section in
`rationale.md`.

- **First-parent linear `main`** (kernel-style merge landings): everything
  append-only with no replay and no archive machinery, at the cost of merge
  knots in raw `git log` and losing GitHub's linear-history enforcement.
  Rejected on familiarity grounds — strict linearity matches the user's
  Chromium/Piper-trained operating model — with costs falling on agents. The
  explicit runner-up if landing friction proves higher than expected.
- **Squash landings**: zero rewrites, but collapses a branch's curated commit
  story to one commit on `main`. Reserved for spike branches whose history is
  genuinely noise.
- **Mid-flight rebase-updating of branches**: the workflow this design retires —
  every update rewrote the whole chain and demanded a force-push (the friction
  that started this design).
- **Blanket client-side force-push blocking**: gated the workflow's own happy
  path while protecting against a loss mode the lease form already prevents
  mechanically; replaced by layers 1–2 plus the narrowed gate.
