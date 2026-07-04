#!/bin/zsh
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
# Instrument window A: wait for the machine, take a lease, run the stratified
# false-signal check and the matched-pair register instrument, release.

set -u
cd /Users/Shared/code/crosswords-finetune-probe/cluegen/scratch/finetune
PY=$HOME/.venvs/default/bin/python
LEASE=/Users/Shared/code/crosswords-finetune-probe/cluegen/local/compute_lease.py

$PY $LEASE wait --timeout-minutes 180 || { echo 'lease wait timed out'; exit 1 }
$PY $LEASE acquire --holder finetune --minutes 50 \
    --task 'instrument window A: stratified false-signal + register pairs' \
    || { echo 'lease acquire failed'; exit 1 }

zsh strata_run.sh
zsh register_run.sh

$PY $LEASE release --holder finetune
echo window_a done
