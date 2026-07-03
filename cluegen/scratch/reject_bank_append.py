# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Append Fable-confirmed rejections from checkpoint results to the reject bank.

The reject bank (`cluegen/local/reject_bank.jsonl`) collects correctly-rejected
clues with labeled reasons — eval data now, judge fine-tuning data later. This
is the capture point the #reject-bank task calls for: run it on any
checkpoint_verify results file and it appends every revise/reject verdict whose
clue is (a) not in the clue bank (banked and rejected stay disjoint) and (b) not
already in the reject bank.

Usage: python reject_bank_append.py <results.jsonl> --data <input_clues.jsonl>
\\
      --source <tag>

`--data` is the same clues file the checkpoint ran on; it supplies the full clue
dicts (the verdict lines carry only word + clue text).
"""

import argparse
import datetime
import json
import pathlib

_LOCAL = pathlib.Path(__file__).parent.parent / 'local'
_CLUE_BANK = _LOCAL / 'clue_bank.jsonl'
_REJECT_BANK = _LOCAL / 'reject_bank.jsonl'


def _key(word, clue_text):
  return (word, clue_text.lower())


def _load_keys(path, nested):
  """Existing (word, clue) keys; `nested` selects the clue-dict layout."""
  keys = set()
  if path.exists():
    for line in path.read_text().splitlines():
      if line:
        record = json.loads(line)
        text = record['clue']['clue'] if nested else record['clue']
        keys.add(_key(record['word'], text))
  return keys


def main():
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument('results', type=pathlib.Path)
  parser.add_argument('--data', type=pathlib.Path, required=True)
  parser.add_argument('--source', required=True)
  parser.add_argument('--contract', required=True,
                      help='which judge contract produced the labels')
  args = parser.parse_args()

  clue_dicts = {}
  for line in args.data.read_text().splitlines():
    if line:
      entry = json.loads(line)
      clue_dicts[_key(entry['word'], entry['clue']['clue'])] = entry['clue']

  banked = _load_keys(_CLUE_BANK, nested=True)
  already_rejected = _load_keys(_REJECT_BANK, nested=True)
  appended = skipped_banked = 0

  with _REJECT_BANK.open('a') as reject_bank:
    for line in args.results.read_text().splitlines():
      if not line:
        continue
      for verdict in json.loads(line).get('verdicts', []):
        if verdict.get('verdict') not in ('revise', 'reject'):
          continue
        key = _key(verdict['word'], verdict['clue'])
        if key in banked:
          # A banked clue Fable now flags is a purge candidate, not a settled
          # reject; surface it instead of appending.
          print(f'PURGE CANDIDATE (in bank): {verdict["word"]} '
                f'"{verdict["clue"]}" — {verdict.get("reason")}')
          skipped_banked += 1
          continue
        if key in already_rejected:
          continue
        record = {
          'word': verdict['word'],
          'clue': clue_dicts.get(key, {'clue': verdict['clue']}),
          'label': {
            'verdict': verdict['verdict'],
            'reason': verdict.get('reason'),
            'basis': verdict.get('basis'),
            'contract': args.contract,
          },
          'source': args.source,
          'ts': datetime.datetime.now(datetime.UTC).isoformat(
            timespec='seconds'
          ),
        }
        reject_bank.write(json.dumps(record) + '\n')
        already_rejected.add(key)
        appended += 1

  print(f'appended {appended}, purge candidates {skipped_banked}')


if __name__ == '__main__':
  main()
