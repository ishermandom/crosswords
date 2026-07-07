# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Rung-3 driver: audits, survivor selection, and full protocol, unattended.

Runs the liveliness and substitution single-turn audits over the rung-3 finals,
drops every flagged row, writes the survivors to the `h1r3` battery set, and
runs the full v3 protocol on them. Designed to run detached under the compute
lease; each stage tees to its own log.
"""

import json
import pathlib
import subprocess
import sys

_SCRATCH = pathlib.Path(__file__).parent
_FINALS = _SCRATCH / 'h1_finals_r3.jsonl'
_SURVIVORS = _SCRATCH / 'h1_survivors_r3.jsonl'
_LOGS = _SCRATCH / 'logs'


def _run_audit(script: str, log_name: str) -> set[tuple[str, str]]:
  """Run one single-turn audit; return the flagged (word, clue) pairs."""
  result = subprocess.run(
    [sys.executable, script, str(_FINALS)],
    capture_output=True,
    text=True,
    cwd=_SCRATCH,
    check=True,
  )
  (_LOGS / log_name).write_text(result.stdout)
  flagged = set()
  for line in result.stdout.splitlines():
    if line.startswith('  FLAG '):
      word, _, rest = line[7:].partition(': "')
      clue = rest.rpartition('" — ')[0]
      flagged.add((word, clue))
  print(f'{script}: {len(flagged)} flagged', flush=True)
  return flagged


def main() -> None:
  """Audit, select survivors, and run the full protocol."""
  flagged = _run_audit(
    'bank_liveliness_audit.py', 'h1r3_liveliness.log'
  ) | _run_audit('h1_substitution_audit.py', 'h1r3_substitution.log')

  rows = [json.loads(line) for line in _FINALS.read_text().splitlines()]
  survivors = [r for r in rows if (r['word'], r['clue']) not in flagged]
  _SURVIVORS.write_text(''.join(json.dumps(r) + '\n' for r in survivors))
  print(f'survivors: {len(survivors)}/{len(rows)}', flush=True)

  subprocess.run(
    [
      sys.executable,
      'battery.py',
      '--sets',
      'h1r3',
      '--confirm-all',
      '--patch',
      'variants/confirm_multiturn_v3.py',
      '--tag',
      'h1rung3',
    ],
    stdout=(_LOGS / 'h1_rung3_full_protocol.log').open('w'),
    stderr=subprocess.STDOUT,
    cwd=_SCRATCH,
    check=True,
  )
  print('rung 3 chunk 1 complete', flush=True)


if __name__ == '__main__':
  main()
