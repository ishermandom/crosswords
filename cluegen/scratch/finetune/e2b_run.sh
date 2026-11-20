#!/bin/zsh
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
# One e2b rehearsal run: train at the given learning rate, then generation
# probe and loss gaps on the best checkpoint. Scores the e2b base model once
# as the shared reference. Args: LEARNING_RATE OUTPUT_DIR

set -u
cd /Users/Shared/code/crosswords-finetune-probe/cluegen/scratch/finetune
export HF_HUB_CACHE=/Users/Shared/models/mlx
# This checkout's environment, synced with `uv sync --group finetune`.
PY=/Users/Shared/code/crosswords-finetune-probe/.venv/bin/python
OPTIQ=/Users/Shared/code/crosswords-finetune-probe/.venv/bin/optiq
E2B=mlx-community/gemma-4-e2b-it-OptiQ-4bit
LR=$1
OUT=$2

[ -f loss_gaps_e2b_base.log ] \
  || $PY loss_gaps.py --model $E2B > loss_gaps_e2b_base.log 2>&1

# Hard 20-minute deadline on the train step so the driver cannot outlive its
# lease (2026-07-03 overlap incident rule); evals then run on best-so-far.
$PY -c "
import subprocess, sys
try:
    subprocess.run(sys.argv[1:], timeout=1200, check=True)
except subprocess.TimeoutExpired:
    print('train step hit the 20-minute deadline; continuing to evals')
" $OPTIQ lora train $E2B --data data/data_stage1 -o $OUT \
    --rank-scaling constant --preset default --batch-size 1 \
    --iters 1000 --learning-rate $LR > train_${OUT}.log 2>&1

$PY gen_probe.py $OUT/best $E2B > gen_probe_${OUT}.log 2>&1
$PY loss_gaps.py --model $E2B --adapter $OUT/best > loss_gaps_${OUT}.log 2>&1
echo done
