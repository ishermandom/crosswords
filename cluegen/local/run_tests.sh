#!/usr/bin/env bash
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
marker_args=()
[ -n "$PYTEST_FROM_HOOK" ] && marker_args=(-m "not wip")

exec python -m pytest -q "${marker_args[@]}" "$(dirname "$0")/tests"
