# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Overnight H2 + breadth driver (user go-ahead 2026-07-07, ~01:50).

Phases, in model-contiguous blocks:

1. **Generation (26B)**: the frozen `calibrated` arm, K=3 samples over the 21
   baselined words and K=2 over 30 fresh breadth words, each run ending in the
   schema'd extract turn that appends to `h1_pool.jsonl`.
2. **Ranking (26B)**: `rank_pool.py` — one fresh-context ranking call per word
   over its deduped pool (H2 candidate ranker).
3. **Audits (31B)**: liveliness over each word's ranker-top-4
   (`h1_overnight_audit.jsonl`), then substitution over the liveliness passers.
   Full protocol on survivors is deliberately left for the morning read —
   verdict data is only useful with a human-paced look at what it says about
   ranking quality first.

The driver self-terminates at its deadline and releases the lease it assumes the
launcher acquired (holder `local-ceiling`). Every stage appends progress to
stdout (the launcher redirects to the driver log).
"""

import json
import pathlib
import subprocess
import sys
import time

_SCRATCH = pathlib.Path('/Users/Shared/code/crosswords-local-ceiling/cluegen/scratch')
_LOGS = _SCRATCH / 'logs'
_LEASE = _SCRATCH.parent / 'local' / 'compute_lease.py'
_DEADLINE = time.time() + 6.5 * 3600

_BASELINED = [
  'COURT', 'ASIDE', 'MELODY', 'SCORE', 'SELDOM', 'NIL', 'LILY', 'CHASE',
  'VIOLET', 'TWELVE', 'GROSS', 'THRICE', 'FRANK',
  'SIXTY', 'THIRD', 'TWICE', 'OSCAR', 'ROBIN', 'WIDOW', 'BOW', 'POUND',
]
# Breadth: untouched words.in categories; judge-eval words excluded so their
# cached eval turns stay uncontaminated.
_BREADTH = [
  'FOURTH', 'NINTH', 'FORTY', 'DOZEN', 'HUNDRED',
  'GRACE', 'HAZEL', 'PEARL', 'RUBY', 'JACK', 'DREW', 'LANCE', 'REED',
  'UNCLE', 'TWIN', 'HEIR', 'BRIDE', 'ORPHAN',
  'SET', 'RUN', 'BANK', 'BAT', 'CASE', 'CHARGE', 'CLUB', 'CRANE', 'DATE',
  'DRAFT', 'DUCK', 'FAIR',
]


def _run(command: list[str], log_name: str | None = None) -> str:
  """Run a subprocess in scratch; return stdout (also teed to a log)."""
  result = subprocess.run(
    command, capture_output=True, text=True, cwd=_SCRATCH, check=True
  )
  if log_name:
    (_LOGS / log_name).write_text(result.stdout + result.stderr)
  return result.stdout


def _out_of_time() -> bool:
  """Whether the deadline has passed; logs when it has."""
  if time.time() > _DEADLINE:
    print('deadline reached — stopping cleanly', flush=True)
    return True
  return False


def generate() -> None:
  """Phase 1: K samples per word through the calibrated arm, pooled."""
  plan = [(w, 3) for w in _BASELINED] + [(w, 2) for w in _BREADTH]
  for word, samples in plan:
    for index in range(samples):
      if _out_of_time():
        return
      try:
        _run(['python3', 'h1a_probe.py', word, 'calibrated', '--pool'])
      except subprocess.CalledProcessError as error:
        # One bad run (malformed extract JSON, a transient model error) must not
        # kill the night; the word just contributes one fewer sample.
        print(f'gen {word} sample {index + 1} FAILED: {error}', flush=True)
        continue
      print(f'gen {word} {index + 1}/{samples}', flush=True)


def rank() -> None:
  """Phase 2: fresh-context ranking per word on the iteration model."""
  print(_run(['python3', 'rank_pool.py', 'gemma4:26b-qat'], 'h1_rank_26b.log'))


def audit() -> None:
  """Phase 3: liveliness on ranker-top-4, substitution on the passers."""
  top4_path = _SCRATCH / 'h1_overnight_audit.jsonl'
  rows = []
  for line in (_SCRATCH / 'h1_rankings.jsonl').read_text().splitlines():
    record = json.loads(line)
    candidates = record['candidates']
    valid = [
      n for n in record['ranking'] if isinstance(n, int)
      and 1 <= n <= len(candidates)
    ]
    for n in valid[:4]:
      rows.append({'word': record['word'], 'clue': candidates[n - 1]})
  top4_path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
  print(f'audit set: {len(rows)} rows', flush=True)

  if _out_of_time():
    return
  liveliness_out = _run(
    ['python3', 'bank_liveliness_audit.py', str(top4_path)],
    'h1_overnight_liveliness.log',
  )
  flagged = set()
  for line in liveliness_out.splitlines():
    if not line.startswith('  FLAG '):
      continue
    # `  FLAG WORD: "clue" — reason`; partition once from the left for the word
    # and once from the right for the reason, so clues containing quotes or
    # colons survive.
    word, _, rest = line[7:].partition(': "')
    flagged.add(word + '\x00' + rest.rpartition('" — ')[0])
  passers = [
    r for r in rows if (r['word'] + '\x00' + r['clue']) not in flagged
  ]
  passers_path = _SCRATCH / 'h1_overnight_passers.jsonl'
  passers_path.write_text(''.join(json.dumps(r) + '\n' for r in passers))
  print(f'liveliness passers: {len(passers)}/{len(rows)}', flush=True)

  if _out_of_time():
    return
  _run(
    ['python3', 'h1_substitution_audit.py', str(passers_path)],
    'h1_overnight_substitution.log',
  )
  print('substitution audit done', flush=True)


def main() -> None:
  """Run all phases, then release the lease."""
  try:
    generate()
    if not _out_of_time():
      rank()
    if not _out_of_time():
      audit()
    print('overnight driver complete', flush=True)
  finally:
    subprocess.run(
      ['python3', str(_LEASE), 'release', '--holder', 'local-ceiling'],
      capture_output=True,
    )
    print('lease released', flush=True)


if __name__ == '__main__':
  main()
