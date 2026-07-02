# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Compare a judge-prompt revision against the current judge.

Judge changes move the bank's gate itself, so setter-style panel evals don't
apply. Instead: (a) agreement with Fable ground truth on the
checkpoint-verdicted clues must hold (no precision give-back), and (b) recall on
the name-clue sample should rise (the measured hole: famous-bearer clues for
name answers draw bad at 3.5x the base rate).

Usage: python cluegen/scratch/judge_eval.py --model gemma4:26b-qat
"""

import argparse
import json
import pathlib

import pipeline_local as pl

_HERE = pathlib.Path(__file__).parent

# The candidate revision: one calibration example legitimizing famous-bearer
# definitions for name answers.
_NAME_EXAMPLE = """
- "Born to Die singer" -> LANA: bankable (medium). For a name answer, a
  famous bearer is a legitimate definition — the bearer is not "merely
  associated" with the name; she instantiates it."""

_JUDGE_V2_SYSTEM = pl._JUDGE_SYSTEM + _NAME_EXAMPLE


# Fable-verdicted clues: (word, clue, fable_verdict) from checkpoints 2-3, read
# out of the bank's provenance annotations.
def _fable_ground_truth():
  truth = []
  for line in (pl._BANK).read_text().splitlines():
    record = json.loads(line)
    fable = record['provenance'].get('fable', '')
    if not fable:
      continue
    verdict = fable.split(' ', 1)[0]
    if verdict in ('accept', 'revise', 'reject'):
      truth.append((record['word'], record['clue']['clue'], verdict))
  return truth


# Name-clue recall sample: legitimate famous-bearer clues the screen has killed
# or would plausibly kill; all verified accurate by hand.
_NAME_SAMPLE = [
  ('LANA', 'Born to Die singer'),
  ('ANNE', 'Green Gables heroine'),
  ('FELIX', 'Fussy half of an odd couple'),
  ('NINA', 'Simone of "Feeling Good"'),
  ('TIM', 'Tiny Dickens boy'),
  ('RITA', 'Educating ___ (Caine film)'),
  ('DAVE', 'Letterman, to friends'),
  ('MARK', 'Twain, on book spines'),
]


def _run_judge(system, model, word, clue, tee):
  """pl._judge with a swappable system prompt."""
  prompt = (
    'Judge this one clue. In "analysis": name the sense used, write the '
    'substitution sentence, and name any flaws — before the verdict.\n\n'
    + json.dumps({'word': word, 'clue': clue})
  )
  content = pl._chat(
    model,
    [
      {'role': 'system', 'content': system},
      {'role': 'user', 'content': prompt},
    ],
    schema=pl._JUDGE_SCHEMA,
  )
  return json.loads(content)['verdict']


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--model', default='gemma4:26b-qat')
  cli = parser.parse_args()

  log_path = pl._LOG_DIR / 'judge_eval.log'
  with log_path.open('w') as log_file:

    def tee(text):
      log_file.write(text)

    truth = _fable_ground_truth()
    print(f'part A: agreement on {len(truth)} Fable-verdicted clues')
    # Fable accepts should stay local-bankable; Fable revises/rejects should
    # stay local-non-bankable. Score each judge the same way.
    for label, system in [('v1', pl._JUDGE_SYSTEM), ('v2', _JUDGE_V2_SYSTEM)]:
      agree = 0
      for word, clue, fable in truth:
        local = _run_judge(system, cli.model, word, clue, tee)
        is_match = (fable == 'accept') == (local == 'bankable')
        agree += is_match
        if not is_match:
          print(
            f'  {label} disagree: {word} fable={fable} local={local} "{clue}"',
            flush=True,
          )
      print(f'  {label}: {agree}/{len(truth)} agree', flush=True)

    print(f'part B: recall on {len(_NAME_SAMPLE)} legit name clues')
    for label, system in [('v1', pl._JUDGE_SYSTEM), ('v2', _JUDGE_V2_SYSTEM)]:
      kills = 0
      for word, clue in _NAME_SAMPLE:
        verdict = _run_judge(system, cli.model, word, clue, tee)
        kills += verdict == 'bad'
        print(f'  {label} {word}: {verdict} "{clue}"', flush=True)
      print(f'  {label}: {kills}/{len(_NAME_SAMPLE)} killed as bad', flush=True)


if __name__ == '__main__':
  main()
