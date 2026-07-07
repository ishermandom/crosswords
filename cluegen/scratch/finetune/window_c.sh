#!/bin/zsh
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
# Basin-mapping window C: one exponential learning-rate ramp on the 12B at
# batch 4 (1e-6 -> 5e-4 over 250 iters, loss reported every 5 steps).

set -u
cd /Users/Shared/code/crosswords-finetune-probe/cluegen/scratch/finetune
export HF_HUB_CACHE=/Users/Shared/models/mlx
PY=$HOME/.venvs/default/bin/python
LEASE=/Users/Shared/code/crosswords-finetune-probe/cluegen/local/compute_lease.py
MODEL=mlx-community/gemma-4-12B-it-qat-OptiQ-4bit

boxed() {
  local deadline=$1
  shift
  $PY -c "
import subprocess, sys
try:
    subprocess.run(sys.argv[2:], timeout=float(sys.argv[1]), check=True)
except subprocess.TimeoutExpired:
    print('step hit its deadline; moving on')
except subprocess.CalledProcessError as error:
    print(f'step failed with code {error.returncode}; moving on')
" $deadline "$@"
}

$PY $LEASE wait --timeout-minutes 180 || { echo 'lease wait timed out'; exit 1 }
$PY $LEASE acquire --holder finetune --minutes 90 \
    --task 'window C: learning-rate basin ramp, 12B batch 4' \
    || { echo 'lease acquire failed'; exit 1 }

boxed 4500 $PY launch_train.py $MODEL --data data/data_stage1_15k \
    --output checkpoints/probe_ramp_b4 --iters 250 --batch-size 4 \
    --peak-lr 1e-6 --ramp-to 5e-4 > ramp_b4.log 2>&1

$PY $LEASE release --holder finetune
echo window_c done
