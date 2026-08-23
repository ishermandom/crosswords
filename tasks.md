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
