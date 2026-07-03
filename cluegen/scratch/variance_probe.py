# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Verdict-distribution probe for the judge cascade.

Samples both judge stages K times per clue at the production temperature, to
separate three cases the single-sample agreement eval conflates: stable-right,
stable-wrong (prompt or knowledge problem), and genuinely split (taste
borderline, where either verdict is fine).

Usage: python cluegen/scratch/variance_probe.py [judge_temperature]
"""

import collections
import json
import pathlib
import sys

import pipeline_local

K = 4

if len(sys.argv) > 1:
  pipeline_local.SCHEMA_TEMPERATURE = float(sys.argv[1])

# Optional second argument restricts to one stage ('screen'/'confirm'); a third
# argument tags the output file (e.g. a prompt-variant name).
_STAGE_FILTER = sys.argv[2] if len(sys.argv) > 2 else None
_RUN_TAG = sys.argv[3] if len(sys.argv) > 3 else ''

_TEMPERATURE_TAG = str(pipeline_local.SCHEMA_TEMPERATURE).replace('.', 'p')
_LOG = (
  pathlib.Path(__file__).parent
  / 'logs'
  / f'variance_probe_t{_TEMPERATURE_TAG}{_RUN_TAG}.jsonl'
)

# The six-run flippers, the suspected stable-wrongs, and two stable controls
# (CHECK bank, SEVEN kill).
TARGETS = [
  ('WYE', 'Forked path?'),
  ('THIRTEEN', 'A number often skipped in elevators'),
  ('GASP', 'Reaction to a jump scare'),
  ('ONE', 'Sole digit'),
  ('FOURTEEN', 'A score, slightly diminished'),
  ('MELODY', 'Whistleable earworm'),
  ('ZED', 'That last character, overseas'),
  ('MURMUR', 'Low hum of a restless crowd'),
  ('CHARGE', 'Attack at full tilt'),
  ('FELIX', 'Favored by fortune?'),
  ('CHECK', 'Threaten the king'),
  ('SEVEN', 'Lucky prime'),
]

STAGES = (('screen', 'gemma4:26b-qat'), ('confirm', 'gemma4:31b-qat'))


def main():
  """Sample each stage K times per clue; print verdict distributions."""
  quiet = lambda text: None  # noqa: E731
  samples = []
  # Model-batched: all screens, then all confirms.
  for stage, model in STAGES:
    if _STAGE_FILTER and stage != _STAGE_FILTER:
      continue
    system = pipeline_local._CONFIRM_SYSTEM if stage == 'confirm' else None
    for word, clue in TARGETS:
      for i in range(K):
        v = pipeline_local._judge(
          model, word, clue, quiet, stage, system=system
        )
        samples.append(
          {
            'word': word,
            'clue': clue,
            'stage': stage,
            'sample': i,
            'verdict': v['verdict'],
            'basis': v['basis'],
            'analysis': v['analysis'],
          }
        )
        print(
          f'{stage:7s} {word:9s} #{i} {v["verdict"]} ({v["basis"]})', flush=True
        )

  with _LOG.open('w') as log:
    for s in samples:
      log.write(json.dumps(s) + '\n')

  print(f'\n{"word":9s} {"stage":7s} verdict distribution (K={K})')
  for stage, _ in STAGES:
    if _STAGE_FILTER and stage != _STAGE_FILTER:
      continue
    for word, clue in TARGETS:
      counts = collections.Counter(
        s['verdict']
        for s in samples
        if s['word'] == word and s['stage'] == stage
      )
      dist = ', '.join(f'{v}:{n}' for v, n in counts.most_common())
      print(f'{word:9s} {stage:7s} {dist}   "{clue}"')


if __name__ == '__main__':
  main()
