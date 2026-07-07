# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Substitution-turn-only audit of a candidate pool (rung 1 of adoption).

The liveliness audit tested flatness only; legality is the new funnel's #1 known
risk (re-cast mangling, a passed plural mismatch). This runs just the v3
substitution turn over a `{"word", "clue"}` JSONL — one call per row, cache keys
matching battery.py's v3 runs exactly, so the full-protocol pass on survivors
(rung 2) reuses every call made here.

Usage: python3 h1_substitution_audit.py <pool.jsonl>
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
  """Run the v3 substitution turn over every pool row and print the flags."""
  namespace: dict[str, object] = {}
  exec(compile(_V3_VARIANT.read_text(), str(_V3_VARIANT), 'exec'), namespace)
  system = namespace['_SUBSTITUTION_SYSTEM']
  prompt = namespace['_SUBSTITUTION_PROMPT']
  schema = namespace['_SUBSTITUTION_SCHEMA']

  source = pathlib.Path(sys.argv[1])
  rows = [json.loads(line) for line in source.read_text().splitlines()]

  cache = battery._load_cache()
  counts: collections.Counter[str] = collections.Counter()
  flags = []
  for row in rows:
    turn = battery._cached_turn(
      cache,
      counts,
      battery._CONFIRM_MODEL,
      row['word'],
      row['clue'],
      0,
      pipeline_local.SCHEMA_TEMPERATURE,
      'confirm.substitution',
      system,
      prompt,
      schema,
    )
    verdict = turn['points_at']
    detail = f' -> {turn["other_object_name"]}' if turn['other_object_name'] else ''
    status = 'ok' if verdict == 'answer' else f'{verdict}{detail}'
    print(f'{row["word"]:12s} {status:28s} "{row["clue"]}"', flush=True)
    if verdict != 'answer':
      flags.append((row['word'], row['clue'], status))

  print(f'\n{source.name}: {len(flags)}/{len(rows)} rows flagged')
  for word, clue, status in flags:
    print(f'  FLAG {word}: "{clue}" — {status}')
  print(f'{counts["calls"]} model calls, {counts["hits"]} cache hits')


if __name__ == '__main__':
  main()
