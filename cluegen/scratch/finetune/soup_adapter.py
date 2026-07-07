# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Average the tail checkpoints of a LoRA run into a "soup" adapter.

Iterates at the end of training orbit the basin floor; their average sits nearer
the (lower, flatter) center than any single iterate. This builds that average
from the run's numbered checkpoints and writes a loadable adapter directory
(averaged weights + copied configs).

Usage: python soup_adapter.py --run-dir DIR --output DIR
       [--checkpoints 0001100 0001200 ...]
"""

import argparse
import shutil
from pathlib import Path

import mlx.core as mx

DEFAULT_CHECKPOINTS = ('0001100', '0001200', '0001300', '0001400', '0001500')

CONFIG_FILES = ('adapter_config.json', 'optiq_lora_config.json')


def average_checkpoints(run_dir: Path, names: list[str]) -> dict:
  """Elementwise mean of the named checkpoints' weights.

  Accumulates in float32, then casts back to the checkpoints' own dtype.
  """
  sums: dict = {}
  dtypes: dict = {}
  for name in names:
    weights = mx.load(str(run_dir / f'{name}_adapters.safetensors'))
    for key, value in weights.items():
      dtypes[key] = value.dtype
      sums[key] = sums.get(key, 0) + value.astype(mx.float32)
  return {
    key: (total / len(names)).astype(dtypes[key]) for key, total in sums.items()
  }


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--run-dir', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument(
    '--checkpoints',
    nargs='+',
    default=list(DEFAULT_CHECKPOINTS),
    help='iteration prefixes of the checkpoints to average',
  )
  args = parser.parse_args()

  averaged = average_checkpoints(args.run_dir, args.checkpoints)
  args.output.mkdir(parents=True, exist_ok=True)
  mx.save_safetensors(str(args.output / 'adapters.safetensors'), averaged)
  for config_name in CONFIG_FILES:
    shutil.copy(args.run_dir / config_name, args.output / config_name)
  print(
    f'soup of {len(args.checkpoints)} checkpoints '
    f'({args.checkpoints[0]}..{args.checkpoints[-1]}) -> {args.output}'
  )


if __name__ == '__main__':
  main()
