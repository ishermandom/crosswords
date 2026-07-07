# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Fresh-context candidate ranker (H2): order each word's pool by satisfaction.

Reads the generation pool (`h1_pool.jsonl`), dedupes candidates per word, and
asks a fresh-context model to order them by expected solver satisfaction — one
schema'd call per word. The ranking is the H2 candidate under test; judge
verdicts on the ranked candidates are its ground truth.

Usage: python3 rank_pool.py [model] (default gemma4:26b-qat) Writes
h1_rankings.jsonl: {"word", "model", "candidates", "ranking"}.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import pipeline_local

_POOL = pathlib.Path(__file__).parent / 'h1_pool.jsonl'
_OUT = pathlib.Path(__file__).parent / 'h1_rankings.jsonl'

_RANK_PROMPT = """\
Answer word: {word}

Below are candidate crossword clues for {word}, numbered. Order ALL of
them from most to least satisfying for a solver.

What satisfying means, in priority order: the clue must be accurate for
{word} (an inaccurate clue ranks last no matter how clever); then prefer
clues that earn their keep — a genuine aha, elegant phrasing, a fair
fight, an interesting checkable fact, or humor — over dictionary-flat
definitions; a question mark is a defect unless the clue has genuine
wordplay or a stretched definition.

Candidates:
{candidates}

Return JSON: {{"ranking": [...]}} — every candidate number exactly once,
best first."""

_RANK_SCHEMA = {
  'type': 'object',
  'properties': {
    'ranking': {'type': 'array', 'items': {'type': 'integer'}},
  },
  'required': ['ranking'],
}


def load_pools() -> dict[str, list[str]]:
  """Per-word deduped candidate lists from the generation pool."""
  pools: dict[str, list[str]] = {}
  for line in _POOL.read_text().splitlines():
    record = json.loads(line)
    pool = pools.setdefault(record['word'], [])
    for clue in record['clues']:
      clue = clue.strip()
      if clue and clue.lower() not in (c.lower() for c in pool):
        pool.append(clue)
  return pools


def main() -> None:
  """Rank every word's pool; append results to the rankings file."""
  model = sys.argv[1] if len(sys.argv) > 1 else 'gemma4:26b-qat'
  with _OUT.open('a') as out:
    for word, pool in sorted(load_pools().items()):
      numbered = '\n'.join(f'{i + 1}. {clue}' for i, clue in enumerate(pool))
      prompt = _RANK_PROMPT.format(word=word, candidates=numbered)
      reply = pipeline_local._chat(
        model,
        [{'role': 'user', 'content': prompt}],
        schema=_RANK_SCHEMA,
      )
      ranking = json.loads(reply)['ranking']
      # A malformed ranking (wrong length, bad indices) is recorded as-is; the
      # analysis stage treats it as a ranker failure, not a crash.
      out.write(
        json.dumps(
          {
            'word': word,
            'model': model,
            'candidates': pool,
            'ranking': ranking,
          }
        )
        + '\n'
      )
      print(f'{word}: {len(pool)} candidates ranked', flush=True)


if __name__ == '__main__':
  main()
