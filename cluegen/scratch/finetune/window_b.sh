#!/bin/zsh
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
# Training-experiment window B: batch-size timing on the 12B (30 iters at
# batch 1/2/4 — throughput and peak memory from the mlx-lm report lines),
# then a learning-rate range probe at batch 4 (80 iters at three peaks,
# scheduled). All through launch_train.py, which this session also validates.

set -u
cd /Users/Shared/code/crosswords-finetune-probe/cluegen/scratch/finetune
export HF_HUB_CACHE=/Users/Shared/models/mlx
# This checkout's environment, synced with `uv sync --group finetune`.
PY=/Users/Shared/code/crosswords-finetune-probe/.venv/bin/python
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
$PY $LEASE acquire --holder finetune --minutes 100 \
    --task 'window B: 12B batch timing + learning-rate range at batch 4' \
    || { echo 'lease acquire failed'; exit 1 }

for BATCH in 1 2 4; do
  boxed 900 $PY launch_train.py $MODEL --data data/data_stage1_15k \
      --output checkpoints/probe_batch${BATCH} --iters 30 --batch-size $BATCH \
      --constant-lr --peak-lr 5e-5 > timing_batch${BATCH}.log 2>&1
done

for LR in 5e-5 1e-4 2e-4; do
  boxed 1500 $PY launch_train.py $MODEL --data data/data_stage1_15k \
      --output checkpoints/probe_lr${LR}_b4 --iters 80 --batch-size 4 \
      --peak-lr $LR --warmup-fraction 0.1 --decay-fraction 0.2 \
      > range_lr${LR}_b4.log 2>&1
done

$PY $LEASE release --holder finetune
echo window_b done
