#!/bin/zsh
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
# Morning analyses for the 5e-5 overnight run: full loss gaps on best/
# (iter 3399), then the decoupling trace — reduced-n gaps at iters 400,
# 1400, 2400 and on the final adapter, same seed so the subset matches.
# Per-step timeouts keep the driver inside its lease.

set -u
cd /Users/Shared/code/crosswords-finetune-probe/cluegen/scratch/finetune
export HF_HUB_CACHE=/Users/Shared/models/mlx
PY=$HOME/.venvs/default/bin/python
ADAPTERS=adapters/adapters_12b_stage1_lr5e5

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

boxed 2100 $PY loss_gaps.py --adapter $ADAPTERS/best \
    > loss_gaps_12b_lr5e5_best.log 2>&1

for label in trace_0000400 trace_0001400 trace_0002400 final; do
  target=$ADAPTERS/$label
  [[ $label == final ]] && target=$ADAPTERS
  boxed 900 $PY loss_gaps.py --adapter $target \
      --limit 40 --definition-limit 40 \
      > loss_gaps_12b_lr5e5_${label}.log 2>&1
done

echo done
