#!/bin/zsh
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
# Abbreviation-conditioning probe: marker-cost scoring on the base 12B, then
# scoring + generation sampling on the tuned final adapter. Per-step timeouts
# keep the driver inside its lease.

set -u
cd /Users/Shared/code/crosswords-finetune-probe/cluegen/scratch/finetune
export HF_HUB_CACHE=/Users/Shared/models/mlx
# This checkout's environment, synced with `uv sync --group finetune`.
PY=/Users/Shared/code/crosswords-finetune-probe/.venv/bin/python

boxed() {
  local deadline=$1
  shift
  $PY -c "
import subprocess, sys
try:
    subprocess.run(sys.argv[2:], timeout=float(sys.argv[1]), check=True)
except subprocess.TimeoutExpired:
    print('step hit its deadline; moving on')
" $deadline "$@"
}

boxed 1200 $PY abbr_probe.py --skip-generate \
    > abbr_probe_base.log 2>&1
boxed 1800 $PY abbr_probe.py --adapter adapters/adapters_12b_stage1_lr5e5 \
    > abbr_probe_tuned.log 2>&1

echo done
