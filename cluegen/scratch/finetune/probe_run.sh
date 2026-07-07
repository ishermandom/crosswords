#!/bin/zsh
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
# One boxed probe run: train MODEL at LR for ITERS (hard DEADLINE_SECONDS on
# the train step), then generation probe and loss gaps on the FINAL adapter
# (short runs may never write a best/ checkpoint).
# Args: MODEL LR OUTPUT_DIR ITERS DEADLINE_SECONDS

set -u
cd /Users/Shared/code/crosswords-finetune-probe/cluegen/scratch/finetune
export HF_HUB_CACHE=/Users/Shared/models/mlx
PY=$HOME/.venvs/default/bin/python
OPTIQ=$HOME/.venvs/default/bin/optiq
MODEL=$1
LR=$2
OUT=$3
ITERS=$4
DEADLINE=$5

$PY -c "
import subprocess, sys
try:
    subprocess.run(sys.argv[2:], timeout=float(sys.argv[1]), check=True)
except subprocess.TimeoutExpired:
    print('train step hit the deadline; continuing to evals')
" $DEADLINE $OPTIQ lora train $MODEL --data data/data_stage1 -o $OUT \
    --rank-scaling constant --preset default --batch-size 1 \
    --iters $ITERS --learning-rate $LR > train_${OUT}.log 2>&1

$PY gen_probe.py $OUT $MODEL > gen_probe_${OUT}.log 2>&1
$PY loss_gaps.py --model $MODEL --adapter $OUT > loss_gaps_${OUT}.log 2>&1
echo done
