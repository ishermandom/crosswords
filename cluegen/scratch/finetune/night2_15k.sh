#!/bin/zsh
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
# 15k rung, night 2 of 2: resume from night 1's adapter and finish the epoch
# (1,500 of 3,750 total iters), spending most of it on the cosine glide to
# the 10% floor. Writes to its own output directory so night 1's numbered
# checkpoints survive for the soup experiment. Launch detached under
# caffeinate -is with start_new_session=True; to pause, kill the process
# group, never the bare pid.

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
$PY $LEASE acquire --holder finetune --minutes 470 \
    --task '15k rung night 2: 12B resume + cosine decay, 1500 iters batch 4' \
    || { echo 'lease acquire failed'; exit 1 }

# ~7 h expected at 0.060 it/s; boxed at 7.7 h so a stall cannot hold the
# lease past its term. steps_per_save=100 caps the loss from a deadline stop.
boxed 27600 $PY launch_train.py $MODEL --data data/data_stage1_15k \
    --output adapters/adapters_12b_15k_n2 --iters 1500 --batch-size 4 \
    --peak-lr 5e-5 --warmup-fraction 0.01 --decay-fraction 0.9 \
    --resume-adapter-file adapters/adapters_12b_15k/adapters.safetensors \
    > night2_15k.log 2>&1

$PY $LEASE release --holder finetune
echo night2_15k done
