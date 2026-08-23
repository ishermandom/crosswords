# Tasks

Status key: `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` dropped

This tracker covers the repo as a whole. Individual projects keep their own
trackers alongside their code, in subdirectories.

---

## Recurring maintenance

**Goal:** keep what this repo depends on current, on a chosen cadence rather
than by surprise. Entries here never complete — a finished run leaves the task
in place for its next turn — so never prune them.

- [ ] **Refresh pinned dependencies** {#dependency-refresh} — about monthly, run
      `uv lock --upgrade && uv sync --all-groups`, so everything this repo pins
      picks up improvements on a chosen schedule instead of drifting.
      `--dry-run` previews what would move, and the Stop checks report within
      one turn whether the new versions object to anything — read those before
      committing the lockfile.
  - Note: Without `--all-groups`, a plain `uv sync` installs only the `dev`
    group, so the refreshed pins for `scratch` and `finetune` would go
    unexercised until something else pulled them in.
  - Note: use `git log -1 --format=%as -- uv.lock` to determine when this last
    ran.

---

## Backlog

- [ ] **Carry the uv workspace into the sibling worktrees** —
      `crosswords-finetune-probe` and `crosswords-local-ceiling` sit on their
      own branches, so they keep resolving imports through the shared user-level
      venv until they pick this up. Each needs its own `uv sync` once rebased;
      the venvs hardlink out of the shared cache, so the second and third cost
      almost nothing on disk.
  - Note: the shared venv's editable `clue-gen` currently resolves
    `cluegen.local` from the `finetune-probe` checkout, so that worktree is the
    one whose imports change behaviour rather than just their source.

- [ ] **Move the repo-wide entries out of `cluegen/local/tasks.md`** — its Git
      workflow section and the Ollama store-path cleanup describe the repo
      rather than the cluegen project, and predate this tracker existing.
  - Note: worth checking the campaign-tracker index in that file during the same
    pass — it names `tasks-local-ceiling.md` and `tasks-finetune-probe.md` but
    omits `cluegen/cloud/tasks.md`.
