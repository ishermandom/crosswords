#!/usr/bin/env bash
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
#
# Tests for the local clue-generation pipeline. Run directly, or through the
# repo-root run_tests.sh, which delegates to every runner in the repo.

marker_args=()
[ -n "$PYTEST_FROM_HOOK" ] && marker_args=(-m "not wip")

here="$(dirname "$0")"
# The workspace root, which owns the lockfile and the shared `.venv`.
repo_root="$(cd "$here/../.." && pwd)"

# `uv run --project` uses this checkout's own `.venv`, building it from uv.lock
# when absent — so a fresh clone or a new worktree runs green with no setup
# step, and each worktree tests against its own environment rather than
# whichever venv the caller's shell activated.
exec uv run --project "$repo_root" pytest -q "${marker_args[@]}" "$here/tests"
