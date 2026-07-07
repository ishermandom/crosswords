# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Liveliness-only audit of the clue bank (flag and report, no deletions).

The chunk-1 full-protocol probe flagged bank clues only via the liveliness
flat-gate, so this covers the whole bank with just that turn — one call per row
instead of seven. Cache keys match battery.py's v3 runs exactly, so any later
full-protocol audit reuses every call made here.

With a JSONL path argument (rows of `{"word", "clue"}`), audits that file
instead of the bank — the same instrument over any candidate pool, so flat-rates
compare directly against the bank's.
"""

import collections
import json
import pathlib
import sys

import battery
import pipeline_local

_V3_VARIANT = (
  pathlib.Path(__file__).parent / 'variants' / 'confirm_multiturn_v3.py'
)


def main() -> None:
  """Run the v3 liveliness turn over every bank row and print the flags."""
  namespace: dict[str, object] = {}
  exec(compile(_V3_VARIANT.read_text(), str(_V3_VARIANT), 'exec'), namespace)
  system = namespace['_LIVELINESS_SYSTEM']
  prompt = namespace['_LIVELINESS_PROMPT']
  schema = namespace['_LIVELINESS_SCHEMA']

  cache = battery._load_cache()
  counts: collections.Counter[str] = collections.Counter()
  flags = []
  if len(sys.argv) > 1:
    source = pathlib.Path(sys.argv[1])
    rows = [json.loads(line) for line in source.read_text().splitlines()]
  else:
    source = pathlib.Path('bank')
    rows = battery._load_set('bank')
  for row in rows:
    turn = battery._cached_turn(
      cache,
      counts,
      battery._CONFIRM_MODEL,
      row['word'],
      row['clue'],
      0,
      pipeline_local.SCHEMA_TEMPERATURE,
      'confirm.liveliness',
      system,
      prompt,
      schema,
    )
    # The two v3 code gates, flag-only here: a clue with no liveliness basis is
    # a flat gloss; a '?' without wordplay is unearned.
    row_flags = []
    if turn['basis'] == 'none':
      row_flags.append('flat gloss, no basis')
    if '?' in row['clue'] and not turn['has_wordplay']:
      row_flags.append('unearned question mark')
    status = ' + '.join(row_flags) if row_flags else f'ok ({turn["basis"]})'
    print(f'{row["word"]:12s} {status:28s} "{row["clue"]}"', flush=True)
    if row_flags:
      flags.append((row['word'], row['clue'], row_flags))

  print(f'\n{source.name}: {len(flags)}/{len(rows)} rows flagged')
  for word, clue, row_flags in flags:
    print(f'  FLAG {word}: "{clue}" — {"; ".join(row_flags)}')
  print(f'{counts["calls"]} model calls, {counts["hits"]} cache hits')


if __name__ == '__main__':
  main()
