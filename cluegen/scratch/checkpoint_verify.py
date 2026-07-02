# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Cloud-verify checkpoint: judge archived probe clues with the bank's judge.

Groups checkpoint_clues.jsonl by version and fires one verify-only
`claude -p` call per version, using the cloud pipeline's exact judge
contract (CLUE_SPEC as system prompt, prompts/verify.md as the user turn,
trimmed flags, scratch cwd). Cloud files are read, never written.

Usage:
  python cluegen/scratch/checkpoint_verify.py --dry-run
  python cluegen/scratch/checkpoint_verify.py
  python cluegen/scratch/checkpoint_verify.py --versions v2,v6
"""

import argparse
import datetime
import json
import pathlib
import subprocess
import tempfile

_CLOUD = pathlib.Path('/Users/Shared/code/crosswords/cluegen/cloud')
_HERE = pathlib.Path(__file__).parent
_DATA = _HERE / 'checkpoint_clues.jsonl'
_RESULTS_DIR = _HERE / 'logs'


def _load_groups(versions: list[str] | None,
                 data: pathlib.Path) -> dict[str, list[dict]]:
  groups: dict[str, list[dict]] = {}
  for line in data.read_text().splitlines():
    entry = json.loads(line)
    if versions and entry['version'] not in versions:
      continue
    groups.setdefault(entry['version'], []).append(entry)
  return groups


def _render_prompt(entries: list[dict]) -> str:
  template = (_CLOUD / 'prompts' / 'verify.md').read_text()
  clue_lines = [
    json.dumps({'word': e['word'], **e['clue']}) for e in entries
  ]
  return template.replace('{{CLUES_JSONL}}', '\n'.join(clue_lines))


def _verify_call(prompt: str, cwd: str) -> dict:
  command = [
    'claude', '-p',
    '--output-format', 'json',
    '--disable-slash-commands',
    '--disallowedTools', '*',
    '--model', 'claude-fable-5',
    '--system-prompt-file', str(_CLOUD / 'CLUE_SPEC.md'),
  ]
  completed = subprocess.run(
    command, input=prompt, capture_output=True, text=True,
    timeout=600, cwd=cwd, check=True,
  )
  return json.loads(completed.stdout)


def _parse_verdicts(result_text: str) -> list[dict]:
  verdicts = []
  for line in result_text.splitlines():
    line = line.strip().strip('`')
    if line.startswith('{'):
      verdicts.append(json.loads(line))
  return verdicts


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--dry-run', action='store_true')
  parser.add_argument('--versions', default=None,
                      help='comma list; default all')
  parser.add_argument('--data', default=None,
                      help='clues JSONL; default checkpoint_clues.jsonl')
  cli = parser.parse_args()
  wanted = cli.versions.split(',') if cli.versions else None
  groups = _load_groups(wanted,
                        pathlib.Path(cli.data) if cli.data else _DATA)

  if cli.dry_run:
    first = next(iter(groups))
    print(f'--- rendered prompt for {first} '
          f'({len(groups[first])} clues) ---')
    print(_render_prompt(groups[first]))
    raise SystemExit(0)

  _RESULTS_DIR.mkdir(exist_ok=True)
  stamp = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
  results_path = _RESULTS_DIR / f'checkpoint_{stamp}.jsonl'
  workdir = tempfile.mkdtemp(prefix='checkpoint-verify-')
  total_cost = 0.0

  for version, entries in groups.items():
    envelope = _verify_call(_render_prompt(entries), workdir)
    verdicts = _parse_verdicts(envelope.get('result', ''))
    usage = envelope.get('usage', {})
    cost = envelope.get('total_cost_usd', 0.0)
    total_cost += cost
    tally = {'accept': 0, 'revise': 0, 'reject': 0}
    for v in verdicts:
      tally[v.get('verdict', 'reject')] = (
        tally.get(v.get('verdict', 'reject'), 0) + 1
      )
    record = {
      'version': version, 'tally': tally, 'verdicts': verdicts,
      'cost_usd': cost, 'usage': usage,
      'session_id': envelope.get('session_id'),
    }
    with results_path.open('a') as f:
      f.write(json.dumps(record) + '\n')
    print(f'{version}: {tally["accept"]}A/{tally["revise"]}RV/'
          f'{tally["reject"]}RJ  ${cost:.3f}  '
          f'in={usage.get("input_tokens")} out={usage.get("output_tokens")} '
          f'cr={usage.get("cache_read_input_tokens")} '
          f'cw={usage.get("cache_creation_input_tokens")}')
    for v in verdicts:
      if v.get('verdict') != 'accept':
        print(f'  {v["word"]} [{v["verdict"]}]: {v.get("reason")}')

  print(f'TOTAL ${total_cost:.3f}  results: {results_path}')
