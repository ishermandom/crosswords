#!/bin/zsh
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
# Stratified false-signal check on the tuned adapter: 3 strata x 20 answers
# x 5 draws. Per-step timeout keeps the driver inside its lease.

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

boxed 1800 $PY strata_check.py --adapter adapters/adapters_12b_stage1_lr5e5 \
    > strata_tuned.log 2>&1

echo done
