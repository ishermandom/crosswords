# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Batch-4 driver: run pipeline_local over the batch word list in chunks.

Chunking bounds interruption loss — the pipeline banks incrementally but holds a
whole invocation's phase work in memory, so a kill mid-invocation loses at most
one chunk (~25 words, ~30 min), not the batch. Each chunk runs with
--skip-banked, so relaunching this driver resumes cleanly.

Drain: touch cluegen/scratch/logs/batch4.stop and the driver exits after the
in-flight chunk. A stale stop file is cleared at startup.

Launch detached (survives the session reaper): python3 -c "import subprocess;
subprocess.Popen(
    ['python3', 'cluegen/scratch/batch4_driver.py'],
    start_new_session=True)"
"""

import datetime
import json
import pathlib
import subprocess
import sys

_SCRATCH = pathlib.Path(__file__).parent
_PIPELINE = _SCRATCH / 'pipeline_local.py'
_WORDS = _SCRATCH / 'batch4_words.txt'
_BANK = _SCRATCH.parent / 'local' / 'clue_bank.jsonl'
_LOG_DIR = _SCRATCH / 'logs'
_DRIVER_LOG = _LOG_DIR / 'batch4_driver.log'
_CHUNK_FILE = _LOG_DIR / 'batch4_chunk.txt'
_STOP_FILE = _LOG_DIR / 'batch4.stop'
_CHUNK_SIZE = 25


def _bank_count() -> int:
  """Count records currently in the clue bank."""
  if not _BANK.exists():
    return 0
  return sum(1 for line in _BANK.read_text().splitlines() if line)


def _log(message: str) -> None:
  """Append a timestamped line to the driver log."""
  stamp = datetime.datetime.now().strftime('%H:%M:%S')
  with _DRIVER_LOG.open('a') as f:
    f.write(f'[{stamp}] {message}\n')


def main() -> None:
  _LOG_DIR.mkdir(exist_ok=True)
  _STOP_FILE.unlink(missing_ok=True)

  words = [w.strip() for w in _WORDS.read_text().splitlines() if w.strip()]
  # Skip banked words up front so chunk numbering reflects remaining work; each
  # chunk also passes --skip-banked as the authoritative re-check.
  banked_words = {
    json.loads(line)['word'] for line in _BANK.read_text().splitlines() if line
  }
  words = [w for w in words if w not in banked_words]

  chunks = [
    words[i : i + _CHUNK_SIZE] for i in range(0, len(words), _CHUNK_SIZE)
  ]
  _log(
    f'batch 4 start: {len(words)} words in {len(chunks)} chunks '
    f'of {_CHUNK_SIZE}; bank at {_bank_count()}'
  )

  for number, chunk in enumerate(chunks, start=1):
    if _STOP_FILE.exists():
      _log(f'stop file found — draining before chunk {number}')
      break
    _CHUNK_FILE.write_text('\n'.join(chunk) + '\n')
    _log(f'chunk {number}/{len(chunks)}: {chunk[0]}..{chunk[-1]}')
    result = subprocess.run(
      [
        sys.executable,
        str(_PIPELINE),
        '--words',
        str(_CHUNK_FILE),
        '--skip-banked',
      ],
      capture_output=True,
      text=True,
    )
    for line in result.stdout.splitlines():
      _log(f'  {line}')
    if result.returncode != 0:
      _log(f'chunk {number} FAILED (rc={result.returncode}):')
      for line in result.stderr.splitlines()[-20:]:
        _log(f'  {line}')
      _log('aborting batch — inspect before relaunch')
      break
    _log(f'chunk {number} done; bank at {_bank_count()}')
  else:
    _log(f'batch 4 complete; bank at {_bank_count()}')


if __name__ == '__main__':
  main()
