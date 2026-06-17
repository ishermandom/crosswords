#!/usr/bin/env bash
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
#
# Root-level test runner. Discovers and delegates to every run_tests.sh script
# found anywhere in the repo, so new packages are included automatically.

dir="$(dirname "$0")"

# -mindepth 2 excludes this script itself.
runners=$(find "$dir" -mindepth 2 -name "run_tests.sh" | sort)

overall_exit=0
# IFS= and -r prevent word-splitting and backslash interpretation on each path.
while IFS= read -r runner; do
  [ -n "$runner" ] || continue
  "$runner" "$@" || overall_exit=$?
done <<< "$runners"

exit $overall_exit
