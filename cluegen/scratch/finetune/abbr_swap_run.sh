#!/bin/zsh
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
# Swap-instrument rerun at n=60 per cell (expanded lexicon, pooled clues,
# signal-purity filter), base then tuned. Per-step timeouts keep the driver
# inside its lease.

set -u
cd /Users/Shared/code/crosswords-finetune-probe/cluegen/scratch/finetune
export HF_HUB_CACHE=/Users/Shared/models/mlx
PY=$HOME/.venvs/default/bin/python

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

boxed 1200 $PY abbr_probe.py --swap-only --group-size 60 \
    > abbr_swap_base.log 2>&1
boxed 1200 $PY abbr_probe.py --swap-only --group-size 60 \
    --adapter adapters_12b_stage1_lr5e5 \
    > abbr_swap_tuned.log 2>&1

echo done
