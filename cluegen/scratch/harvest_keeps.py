"""Harvest never-extracted KEEP drafts from pipeline logs, judge, bank.

Under the bank-shape goal (breadth, then as many good clues per word as
are cost-effective), every KEEP draft that clears the cascade is
inventory. The bank rate doubles as a measurement: how much bankable
material sits unexploited in the draft pools of completed runs.
"""

import datetime
import re

from pipeline_local import _BANK, _LOG_DIR, _bank, _judge

_SCREEN_MODEL = 'gemma4:26b-qat'
_CONFIRM_MODEL = 'gemma4:31b-qat'

# First lines of edit-turn blocks that are commentary, not clue text.
_NOISE_PREFIXES = (
  'sentence:',
  'substitution:',
  'check:',
  'verdict:',
  'trap:',
  'angle',
  'note:',
  'draft',
  'clue ',
)


def _norm(text):
  """Comparison key: case- and ?-insensitive."""
  return text.lower().rstrip('?').strip()


def _keep_clues(edit_text, word):
  """First line of each block the setter's editor marked KEEP, filtered
  to strings that plausibly are clue text."""
  clues = []
  for block in re.split(r'\n\s*\n', edit_text):
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
      continue
    if not any(re.search(r'(?i)verdict.*\bkeep\b', line) for line in lines):
      continue
    candidate = re.sub(r'^["\'\d\.\)\s]+', '', lines[0]).strip('"\' ')
    candidate = re.sub(r'(?i)^clue:\s*', '', candidate)
    if not 4 <= len(candidate) <= 90:
      continue
    if candidate.lower().startswith(_NOISE_PREFIXES):
      continue
    # Meta-commentary, not clue text: label lines and setter chatter.
    if candidate.endswith(':'):
      continue
    if re.search(
      r"(?i)\b(let's|i will|actually|final clue|is better)\b", candidate
    ):
      continue
    if re.search(rf'\b{word}\b', candidate, re.I):  # answer leakage
      continue
    clues.append(candidate)
  return clues


def _collect_candidates():
  """(word, clue) pairs from all pipeline logs: KEEP drafts that were
  never extracted for judging and are not already banked."""
  banked = set()
  if _BANK.exists():
    import json

    for line in _BANK.read_text().splitlines():
      record = json.loads(line)
      banked.add((record['word'], _norm(record['clue']['clue'])))

  candidates = {}
  for log_path in sorted(_LOG_DIR.glob('pipeline_*.log')):
    for section in re.split(r'^===== ', log_path.read_text(), flags=re.M)[1:]:
      word = section.split(' ', 1)[0].strip('= \n')
      edit_match = re.search(
        r'--- setter Now act[^\n]*\n(.*?)(?=\n--- |\Z)', section, re.S
      )
      if not edit_match:
        continue
      extracted = {
        _norm(c) for c in re.findall(r'"clue":\s*"([^"]*)"', section)
      }
      for clue in _keep_clues(edit_match.group(1), word):
        key = (word, _norm(clue))
        if key in banked or _norm(clue) in extracted:
          continue
        candidates.setdefault(key, (word, clue, log_path.name))
  return list(candidates.values())


def main():
  candidates = _collect_candidates()
  print(f'{len(candidates)} never-extracted KEEP candidates', flush=True)

  stamp = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
  log_path = _LOG_DIR / f'harvest_{stamp}.log'
  banked_count = 0
  with log_path.open('w') as log_file:

    def tee(text):
      log_file.write(text)
      log_file.flush()

    for word, clue, source in candidates:
      tee(f'\n===== {word}: {clue} [{source}]\n')
      screen = _judge(_SCREEN_MODEL, word, clue, tee, 'screen')
      if screen['verdict'] != 'bankable':
        print(f'{word}: "{clue}" -> {screen["verdict"]}', flush=True)
        continue
      confirm = _judge(_CONFIRM_MODEL, word, clue, tee, 'confirm')
      if confirm['verdict'] != 'bankable':
        print(f'{word}: "{clue}" -> confirm {confirm["verdict"]}', flush=True)
        continue
      _bank(
        word,
        {'clue': clue, 'trap': None, 'confidence': 'medium'},
        confirm['difficulty'],
        {
          'generator': _SCREEN_MODEL,
          'prompt_version': 'pool-harvest',
          'judge': f'{_SCREEN_MODEL} + {_CONFIRM_MODEL}',
          'verdict': 'local-harvest',
          'source_log': source,
        },
      )
      banked_count += 1
      print(f'{word}: "{clue}" -> BANKED', flush=True)
  print(f'banked {banked_count}/{len(candidates)}', flush=True)
  print(f'log: {log_path}')


if __name__ == '__main__':
  main()
