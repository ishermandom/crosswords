#!/bin/zsh
# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
# 15k rung readout: build the checkpoint soup, then run the instrument suite
# (loss gaps, stratified false-signal, matched-pair difficulty preference)
# on both the plain night-2 adapter and the soup. Baselines for comparison
# already exist from the 5k rung's window A logs. Launch detached under
# caffeinate -is with start_new_session=True; kill the process group to stop.

set -u
cd /Users/Shared/code/crosswords-finetune-probe/cluegen/scratch/finetune
export HF_HUB_CACHE=/Users/Shared/models/mlx
PY=$HOME/.venvs/default/bin/python
LEASE=/Users/Shared/code/crosswords-finetune-probe/cluegen/local/compute_lease.py
PLAIN=adapters/adapters_12b_15k_n2
SOUP=adapters/adapters_12b_15k_soup

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
$PY $LEASE acquire --holder finetune --minutes 210 \
    --task '15k rung readout: instrument suite on plain + soup adapters' \
    || { echo 'lease acquire failed'; exit 1 }

$PY soup_adapter.py --run-dir $PLAIN --output $SOUP \
    > soup_build.log 2>&1 || { echo 'soup build failed'; }

boxed 1800 $PY loss_gaps.py --adapter $PLAIN > loss_gaps_15k.log 2>&1
boxed 1800 $PY loss_gaps.py --adapter $SOUP > loss_gaps_15k_soup.log 2>&1
boxed 1800 $PY strata_check.py --adapter $PLAIN > strata_15k.log 2>&1
boxed 1800 $PY strata_check.py --adapter $SOUP > strata_15k_soup.log 2>&1
boxed 900 $PY register_pairs.py --adapter $PLAIN > register_pairs_15k.log 2>&1
boxed 900 $PY register_pairs.py --adapter $SOUP \
    > register_pairs_15k_soup.log 2>&1

$PY $LEASE release --holder finetune
echo night2_measures done
