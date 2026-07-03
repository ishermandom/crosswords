<!-- Copyright 2026 Ilya Sherman (ishermandom@) -->
<!-- SPDX-License-Identifier: MIT -->

# Git workflow — extended rationale

_This is the long-form companion to `spec.md`: a capture of the full design
discussion (2026-07-02/03), preserved so the subtle reasoning behind each
decision can be reconstructed rather than re-derived. The spec is normative;
this document explains why. It follows the arc of the original conversation,
because the order in which the problems surfaced is itself part of the
rationale._

## 1. Origin: two frictions in one afternoon

The design began as an incident post-mortem, not an abstract exercise. Two
things happened while integrating a feature branch (`finetune-probe`) with
`main`:

- A repository ruleset rejected a push because the branch contained a merge
  commit ("This branch must not contain merge commits"). The integration had
  been done as a merge precisely to avoid rewriting 22 published commits. The
  ruleset forced a redo as a rebase.
- The rebase produced a rewritten branch whose push required `--force`, and the
  client-side git gate (a Claude Code hook classifying force-pushes as
  irreversibly destructive) blocked it, requiring a human to run the push
  manually.

The combination was self-defeating: one rule mandated rebases, another treated
the force-pushes that rebases require as emergencies. Every future branch
integration would hit the same wall. That prompted the real questions: what is
the force-push protection actually protecting against? Where should such
protections live? And what workflow makes them unnecessary?

## 2. Mechanics: why rebases force force-pushes

A commit's identity (hash) covers its content **and its entire parent chain**. A
rebase therefore cannot "move" commits — it re-creates them with new parents and
new identities. The original chain still exists; a parallel replacement history
is built and the branch label moved to it.

A normal `git push` only fast-forwards: it appends commits whose history
includes the remote's current tip, so nothing the remote holds can disappear. A
rebased branch's new chain does not include the old tip — it replaces it — so
the push is rejected as a non-fast-forward. `--force` is the explicit consent to
replace remote history. `--force-with-lease` adds the seatbelt: replace only if
the remote tip is exactly the one last fetched, which makes clobbering work you
have not seen mechanically impossible.

Consequences that shaped the design:

- Any workflow that rebases published branches carries a force-push per rebase,
  forever.
- The loss mode force-pushing actually risks (erasing unseen remote work) is
  fully prevented by the lease form. The other cost — the superseded chain
  losing its name — is not prevented by anything in stock git; it merely remains
  recoverable via reflogs (~90 days, local, archaeology-grade).
- "Recoverable in principle" was judged insufficient: the user's requirement is
  history preservation that is **visible** — named refs in a place one would
  actually look — not forensic.

## 3. Linearity is a property with a location

"Linear history" conflates several distinct choices. Untangling them was the
pivotal move in the discussion.

A merge commit ties two lines with a two-parent knot, preserving what actually
happened. A rebase rewrites the story into "it was always one line" — tidier,
but the commits are benign forgeries: each claims a parent context it was never
written or tested in.

The key decoupling: **`main`'s shape and branches' shapes are independent
policies.** `main` stays perfectly linear as long as whatever lands arrives as a
fast-forward or a one-time replay at landing; what a branch looked like
mid-flight (including "merge `main` in to update" knots) is scaffolding that
never has to reach `main`. Where the clean line lives is a choice:

- at the trunk level (strict linearity — Chromium),
- at the first-parent level (merge landings; `git log --first-parent` is the
  clean line — the Linux kernel),
- at the leaf level (immaculate patch series inside messy integration — also the
  kernel).

Cleanliness is achieved by **choosing a level**, never by rewriting shared refs.

## 4. Branch-update strategies, and the keep-alive problem

Two ways for a living branch to take updates from `main`:

- **Rebase-update** (the old ruleset's mandate): linear branch, but every update
  rewrites the whole chain — repeated conflict re-resolution (the triggering
  incident replayed 22 commits), a force-push per update, an orphaned chain per
  update.
- **Merge-update**: one append-only knot per update; conflicts resolved once, in
  a commit that is itself reviewable; nothing rewritten or orphaned. Costs: the
  branch log grows knots (readable via `--first-parent`), and the knots must be
  dropped at landing.

An apparent resolution — merge-update during life, single replay-rebase at
landing — surfaced a subtler problem when tested against the actual workflow:
**branches here stay alive across landings.** Landing by replay copies commits
onto `main` under new identities while the branch keeps the originals. The same
changes then exist twice under different names:

- Updating the branch from `main` makes git reconcile originals against their
  own copies. Identical changes auto-merge; changes adjusted during landing
  (conflict resolutions) conflict with their own copies — confusing, because
  both sides are "you."
- The next landing must ship only what is new, so something must track the
  landed/unlanded boundary. Git has real machinery for patch-identity matching
  (`git log --cherry-pick`, auto-skip of patch-identical commits in rebases), so
  the pattern functions — but it is bookkeeping-flavored and log-noisy.

The clean resolution adopted in the spec: **reset the branch onto `main` after
every landing** (the land script's final step). A live branch is then always
exactly "`main` + unlanded work" — no duplicates, no boundary tracking. The
price is one lease-protected branch rewrite per landing, which is what the
archive machinery exists to make lossless. `git rerere` ("reuse recorded
resolution" — records every conflict resolution and replays it when the
identical conflict reappears) blunts the re-resolution cost at replay time.

## 5. The first-parent alternative

Given keep-alive branches, first-parent linearity dissolves nearly everything:
landings are merge commits on `main`; branch and `main` share the same commit
objects, so there are no duplicates, no boundary, no replay, no archive
machinery — everything is append-only by construction, and a fast-forward-only
rule on `main` alone gives agents free rein with structural safety.

Costs, honestly: raw `git log main` shows knots and branch interiors
(`--first-parent` restores the clean view; `git bisect --first-parent` exists);
GitHub's "require linear history" enforcement must stay off; merge commits are
where changes can hide (see §7).

At one point in the discussion this was the leading recommendation. It was
ultimately not chosen — see §8 — but it is the explicit runner-up, and the spec
records a revisit trigger: if landing friction (replay conflicts, archive
discipline) proves materially higher than expected in practice, this is the
design to fall back to, not a reason to weaken the adopted one.

## 6. Survey: what the durable workflows actually do

Correcting a premise first: **the Linux kernel is the canonical _non_-linear
project** — mainline is a stream of merge commits; it is cited as "clean
history" because its first-parent view is tidy and its leaf patch series are
immaculate. Chromium is the canonical strict-linear project. That the two
opposite graph shapes are both held up as exemplary is the clearest evidence
that "clean" is a level choice (§3).

- **Kernel model**: patch series rewritten freely **while private**
  (mailing-list review, before publication); once applied to a maintainer tree,
  never rewritten; trees integrate upward via merge commits with meaningful
  messages; back-merges discouraged except at defined sync points. Doctrine:
  never rebase published history. Preservation is in-graph and total.
- **Chromium/Gerrit model** (also Go, Android): every change is a single
  reviewable unit landed by rebase onto trunk after machine verification (commit
  queue); no merge commits ever. The part casually missed: **the true history is
  archived in the review system** — Gerrit permanently stores every patchset
  revision of every change as a named, diffable object. Strict linearity is
  affordable because the archive burden moved out of the graph. The spec's
  `refs/archive/**` namespace is a homemade equivalent of exactly this.
- **GitHub flow + squash**: short-lived branch → PR → squash to linear main;
  history preserved in PR refs and the PR narrative. Degrades precisely on
  long-lived, repeatedly landing branches.
- **Trunk-based development**: tiny changes straight to main behind flags;
  branches near-nonexistent. Append-only by construction; discipline cost moves
  into the code.
- **git-flow**: the elaborate 2010 merge choreography; the one pattern the
  industry has broadly walked away from for continuous work. Included only as a
  marker.

Two invariants shared by every survivor:

1. **Published history is append-only.** Rewriting happens before publication,
   or inside a system that archives every superseded state by name. No mature
   workflow force-pushes shared refs as routine practice.
2. **The clean line is a deliberately positioned view** — leaf, first-parent, or
   trunk — never the product of rewriting shared history.

## 7. The case against non-linear history

Why Chromium and Google-internal (Piper — a centralized single-sequence system
where nonlinearity is not even expressible) standardize on linear history; the
mechanisms, so the choice is informed rather than aesthetic:

1. **Loss of total order.** Merge graphs give partial order; "what's in this
   build," release-cut reasoning, and culprit windows become queries instead of
   glances. Linear trunk makes them trivial, and enormous automation (commit
   queues, culprit finders, rollback tooling) is built on that.
2. **Death of the every-state-tested invariant.** With merges, branch commits
   were tested against stale bases; the merged combination is a new, untested
   state. Semantic conflicts — both sides pass alone, textual merge clean,
   combination broken — produce a "culprit" that is a merge commit with no
   interesting diff.
3. **Bisect degradation.** Bisect descends into branch interiors and can finger
   merges. `git bisect --first-parent` restores the landing-level experience;
   interior hygiene is then a second concern.
4. **The merge-revert footgun.** Reverting a landed merge (`git revert -m 1`)
   then later re-merging the fixed branch does **not** restore the changes — the
   original merge already entered the base. One must revert the revert. A
   classic, documented burn.
5. **Merges are where changes hide.** A merge's diff is relative to each parent;
   conflict resolutions and smuggled edits ("evil merges") are easy to miss.
   Linear commits have one plain reviewable diff.
6. **Ecosystem assumptions.** Changelog tools, UI commit lists, and casual log
   readers all handle the linear case best.
7. **Enforceability asymmetry.** "No merge commits" is a server checkbox; "make
   good merges" is a culture. Organizations of thousands choose the invariant a
   machine can guarantee — and pay for it by making the review system the
   permanent archive.

At solo-plus-agents scale, most of these bite lightly (no commit queue, rare
bisects, single writer at a time), which is why the decision legitimately came
down to §8.

## 8. The decision: strict linearity, chosen on familiarity

With the structural costs equalized (agents absorb the ritual either way), the
tie-breaker was explicit and is worth preserving: **the user's operating
instincts were formed on Chromium and Piper — strict-linear cultures — and a
known-good workflow one can reason about under stress has real value.** The
agent-powered twist strengthens rather than weakens the choice:

- The ritual costs that make strict linearity expensive for humans (replay,
  archive pushes, branch resets, rerere care) convert into script execution, the
  one resource an agent-powered repo has in surplus.
- Fast-forward-only `main` is a free commit queue: concurrent landings serialize
  because the second push is rejected as non-fast-forward and simply re-replays
  and retries — optimistic concurrency from one ruleset checkbox.
- Total order plus per-commit session trailers makes `git log main` a complete
  audit log of agent activity, and reverting an agent misfire is a
  one-dimensional `git revert` with no merge-revert trap — safe to delegate.
- Linearity is enforceable by server checkbox (§7.7), aligning the protection
  with the workflow instead of against it.

## 9. The enforcement seam: convention vs structure

The design's sharpest question, raised by the user against the near-final
proposal: _if the land script can rewrite history, so can any other invocation —
is "nothing meaningful is lost" enforced for those too?_

The honest answer at that point was no: server rulesets made `main` and the
archive namespace untouchable, but the archive-before-rewrite step for branches
lived only in the land script — convention, exactly what a raw push bypasses.
Two things were already structurally true and scoped the exposure: everything
**landed** is loss-proof (append-only `main`), and every pushed chain also
survives ~90 days in the pushing clone's reflog. But the requirement was visible
preservation, not forensics.

The principle that resolves it: **clients cannot be made trustworthy; only the
receiving end can refuse to lose things.** (This is the actual design insight
behind Gerrit — it archives every patchset because it _is_ the server accepting
the push.) Three implementations, by strength:

1. **Auto-archive via GitHub Actions** (adopted): push events carry the `before`
   SHA and a `forced` flag; deletions carry the old tip. A workflow snapshots
   `before` into `refs/archive/<branch>/<timestamp>` through the API on every
   force-push and deletion, from any client. The rewritten-away objects still
   exist server-side when it runs. Reactive: an Actions outage leaves a gap
   (covered by the pushing clone's reflog); the trust anchors become GitHub's
   ref storage and the Actions machinery.
2. **Self-hosted bare hub as origin** (rejected): pre-receive hooks make
   archiving a _precondition_ of accepting any rewrite — prevention rather than
   reaction, the only version where the invariant cannot even transiently fail.
   Rejected for a solo setup: owning a second origin, its hooks, and a mirror
   link is disproportionate infrastructure. Recorded because it is the correct
   answer at higher stakes.
3. **Never-prune local mirror** (optional depth, not adopted): scheduled fetch
   of all refs into a never-gc'd bare repo; the only layer that also survives
   GitHub-side failures; polling gap for short-lived chains. Compose it in later
   if the repo's value justifies it.

With layer 1, the land script's explicit archive step is demoted from guarantee
to convenience: it produces _legible_ names; the Action is the dragnet no
invocation can skip.

## 10. Decision record

All settled 2026-07-03 through two structured question rounds:

- **Model**: strict-linear `main`; first-parent recorded as explicit runner-up
  with a friction-based revisit trigger (§5, §8).
- **Enforcement**: ruleset trio + auto-archive Action adopted; bare hub
  rejected; never-prune mirror deferred as optional depth (§9).
- **Presubmit**: full suite once per landing on the final replayed state;
  per-commit verification available by flag, not default — mid-chain replayed
  commits as unverified intermediates is a rare, shallow risk at solo scale, and
  the flag exists for landings where chain bisectability matters (§7.3).
- **Gate (dotfiles, at migration)**: allow `--force-with-lease` to
  `refs/heads/*` except `main`; bare `--force` blocked everywhere (no legitimate
  use over the lease form); rewrite plumbing stays gated (§2, §9).
- **Land script**: built now in crosswords (`scripts/land.py`, Python),
  migrating with the docs; a working reference implementation beats spec-only.
- **Scope**: crosswords now (it carries the active multi-thread agent traffic);
  all personal repos, `gh-protect.sh` audit assertions, gate narrowing, and
  global `rerere` at the dotfiles migration.

## 11. Consciously accepted costs

- One homegrown script (~100 lines) to own and eventually migrate.
- `refs/archive` is CLI-browsable only; GitHub's UI does not surface it. A
  documented recovery drill (one `git ls-remote` pattern, one fetch/diff
  example) is part of the land-script deliverable, because an archive nobody
  knows how to read fails the visibility requirement that motivated it.
- Replayed mid-chain commits are unverified intermediate states unless the
  per-commit flag is used.
- The auto-archive layer is reactive, with GitHub and Actions as trust anchors;
  the prevention-grade and GitHub-independent layers exist (§9) and are
  deliberately not built today.
- Archive refs accumulate indefinitely; pruning is a policy decision deferred
  until it matters, which at text-repo scale may be never.
