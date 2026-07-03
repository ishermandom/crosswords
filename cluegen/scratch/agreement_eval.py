# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Local-judge agreement eval against the Fable reference verdicts.

Re-judges the 32 labeled clues in `satisfaction_reference_verdicts.jsonl`
through the production cascade (26B screen, then 31B confirm on screen passes)
and reports agreement with the cloud reference. Success looks like: chunk-1
flats die locally; Fable-accepted regression clues stay bankable.

Model-batched like the pipeline: all 26B screens first, then the 31B confirms,
because a gemma4 model switch drains and rewires wired memory.

Usage: python cluegen/scratch/agreement_eval.py
"""

import datetime
import json
import pathlib
import sys

import pipeline_local

_SCRATCH = pathlib.Path(__file__).parent
_REFERENCE = _SCRATCH / 'satisfaction_reference_verdicts.jsonl'
_LOG_DIR = _SCRATCH / 'logs'

_SCREEN_MODEL = 'gemma4:26b-qat'
_CONFIRM_MODEL = 'gemma4:31b-qat'

# Fable verdicts and local-cascade verdicts use different vocabularies; this
# maps the reference onto the local scale for the agreement check.
_FABLE_TO_LOCAL = {'accept': 'bankable', 'revise': 'fixable', 'reject': 'bad'}


def main():
  """Run the cascade over the reference clues; print the agreement table."""
  reference = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else _REFERENCE
  records = [
    json.loads(line) for line in reference.read_text().splitlines() if line
  ]
  stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
  log_path = _LOG_DIR / f'agreement_eval_{stamp}.jsonl'
  quiet = lambda text: None  # noqa: E731 — _judge's tee is unused here

  # Pass 1 (26B): screen everything.
  for record in records:
    screen = pipeline_local._judge(
      _SCREEN_MODEL, record['word'], record['clue'], quiet, 'screen'
    )
    record['local_screen'] = screen
    print(
      f'screen {screen["verdict"]:8s} {record["word"]}: "{record["clue"]}"',
      flush=True,
    )

  # Pass 2 (31B): confirm only screen-bankables, as production does.
  for record in records:
    if record['local_screen']['verdict'] != 'bankable':
      record['local_confirm'] = None
      record['local_cascade'] = record['local_screen']['verdict']
      continue
    confirm = pipeline_local._judge(
      _CONFIRM_MODEL,
      record['word'],
      record['clue'],
      quiet,
      'confirm',
      system=pipeline_local._CONFIRM_SYSTEM,
    )
    record['local_confirm'] = confirm
    record['local_cascade'] = confirm['verdict']
    print(
      f'confirm {confirm["verdict"]:8s} {record["word"]}: "{record["clue"]}"',
      flush=True,
    )

  with log_path.open('w') as log:
    for record in records:
      log.write(json.dumps(record) + '\n')

  # Agreement table + the two success counts.
  print(
    f'\n{"word":12s} {"fable":22s} {"screen":9s} {"cascade":9s} '
    f'{"basis":11s} agree?'
  )
  accepts_held = flats_died = accepts_total = revises_total = 0
  for record in records:
    fable_as_local = _FABLE_TO_LOCAL[record['verdict']]
    is_match = record['local_cascade'] == fable_as_local
    if record['verdict'] == 'accept':
      accepts_total += 1
      accepts_held += record['local_cascade'] == 'bankable'
    else:
      revises_total += 1
      flats_died += record['local_cascade'] != 'bankable'
    fable_label = f'{record["verdict"]} ({record["basis"] or "-"})'
    deciding_stage = record['local_confirm'] or record['local_screen']
    local_basis = deciding_stage.get('basis', '-')
    print(
      f'{record["word"]:12s} {fable_label:22s} '
      f'{record["local_screen"]["verdict"]:9s} '
      f'{record["local_cascade"]:9s} {local_basis:11s} '
      f'{"yes" if is_match else "NO"}  "{record["clue"]}"'
    )

  print(
    f'\nFable accepts locally bankable: {accepts_held}/{accepts_total}\n'
    f'Fable revises/rejects locally non-bankable: '
    f'{flats_died}/{revises_total}'
  )
  print(f'log: {log_path}', file=sys.stderr)


if __name__ == '__main__':
  main()
