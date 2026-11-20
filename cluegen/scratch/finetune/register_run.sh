#!/bin/zsh
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
# Matched-pair register preference, base then tuned: 100 pairs scored under
# the hard prompt. Per-step timeouts keep the driver inside its lease.

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

boxed 900 $PY register_pairs.py > register_pairs_base.log 2>&1
boxed 900 $PY register_pairs.py --adapter adapters/adapters_12b_stage1_lr5e5 \
    > register_pairs_tuned.log 2>&1

echo done
