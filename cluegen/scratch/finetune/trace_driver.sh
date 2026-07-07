#!/bin/zsh
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
# Sequential diagnostics batch: direct-load generation probe, then loss-gap
# checkpoint trace at iterations 400 and 1400. One model in memory at a time.

set -u
cd /Users/Shared/code/crosswords-finetune-probe/cluegen/scratch/finetune
export HF_HUB_CACHE=/Users/Shared/models/mlx
PY=~/.venvs/default/bin/python

$PY gen_probe.py adapters/adapters_12b_stage1/best > gen_probe_best.log 2>&1
$PY loss_gaps.py --adapter adapters/adapters_12b_stage1/trace_0000400 \
    > loss_gaps_0400.log 2>&1
$PY loss_gaps.py --adapter adapters/adapters_12b_stage1/trace_0001400 \
    > loss_gaps_1400.log 2>&1
echo done
