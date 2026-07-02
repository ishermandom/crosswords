"""Measure 31B confirm verdict stability on borderline (fixable) clues.

If the same clue text draws different verdicts across re-judges, the
confirm gate is noisy and a best-of-N vote could recover yield; if
verdicts are stable, the gate is a real quality bar and yield needs
better clues, not more votes.
"""
import json
import pathlib
from collections import Counter

from pipeline_local import _LOG_DIR, _judge

_MODEL = 'gemma4:31b-qat'
_VOTES = 5

sample = json.loads(pathlib.Path('flip_sample.json').read_text())
log_path = _LOG_DIR / 'flip_check.log'
with log_path.open('w') as log_file:
  def tee(text):
    log_file.write(text)
    log_file.flush()
  flippers = 0
  for entry in sample:
    verdicts = Counter(
      _judge(_MODEL, entry['word'], entry['clue'], tee, f'vote{i}')['verdict']
      for i in range(_VOTES))
    is_flipper = len(verdicts) > 1
    flippers += is_flipper
    print(f"{entry['word']}: {dict(verdicts)} \"{entry['clue']}\"",
          flush=True)
  print(f'{flippers}/{len(sample)} clues drew mixed verdicts '
        f'across {_VOTES} votes', flush=True)
