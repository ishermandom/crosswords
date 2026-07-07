# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Morning read of the overnight H2 + breadth run — offline, no model calls.

Answers, from the pool, rankings, and audit logs:
- per-word coverage: does the ranker-top-4 hold a candidate passing both
  single-turn audits, and at which rank the first survivor sits;
- ranker quality: coverage@2 against coverage@4 (the oracle within the audited
  set);
- breadth: the same numbers grouped by word class.
"""

import collections
import json
import pathlib

_SCRATCH = pathlib.Path(__file__).parent
_LOGS = _SCRATCH / 'logs'

_CLASSES = {
  'number/ordinal': [
    'TWELVE', 'SIXTY', 'THIRD', 'TWICE', 'THRICE', 'FOURTH', 'NINTH',
    'FORTY', 'DOZEN', 'HUNDRED', 'SCORE', 'GROSS', 'NIL',
  ],
  'name-word': [
    'OSCAR', 'ROBIN', 'FRANK', 'GRACE', 'HAZEL', 'PEARL', 'RUBY', 'JACK',
    'DREW', 'LANCE', 'REED', 'LILY', 'VIOLET', 'MELODY',
  ],
  'kinship': ['WIDOW', 'UNCLE', 'TWIN', 'HEIR', 'BRIDE', 'ORPHAN'],
  'polysemous': [
    'COURT', 'ASIDE', 'SELDOM', 'CHASE', 'BOW', 'POUND', 'SET', 'RUN',
    'BANK', 'BAT', 'CASE', 'CHARGE', 'CLUB', 'CRANE', 'DATE', 'DRAFT',
    'DUCK', 'FAIR',
  ],
}


def _flagged(log_name: str) -> set[tuple[str, str]]:
  """(word, clue) pairs flagged in one audit log."""
  flags = set()
  for line in (_LOGS / log_name).read_text().splitlines():
    if not line.startswith('  FLAG '):
      continue
    word, _, rest = line[7:].partition(': "')
    flags.add((word, rest.rpartition('" — ')[0]))
  return flags


def main() -> None:
  """Print the coverage, ranker, and breadth tables."""
  flagged = _flagged('h1_overnight_liveliness.log') | _flagged(
    'h1_overnight_substitution.log'
  )
  audited = collections.defaultdict(list)
  for line in (_SCRATCH / 'h1_overnight_audit.jsonl').read_text().splitlines():
    row = json.loads(line)
    audited[row['word']].append(row['clue'])

  survivor_rank: dict[str, int | None] = {}
  survivors: dict[str, list[str]] = {}
  for word, clues in audited.items():
    passing = [
      (rank, clue)
      for rank, clue in enumerate(clues, 1)
      if (word, clue) not in flagged
    ]
    survivor_rank[word] = passing[0][0] if passing else None
    survivors[word] = [clue for _, clue in passing]

  words = sorted(audited)
  covered4 = [w for w in words if survivor_rank[w] is not None]
  covered2 = [w for w in words if survivor_rank[w] in (1, 2)]
  covered1 = [w for w in words if survivor_rank[w] == 1]
  print(f'words audited: {len(words)}')
  print(f'coverage@1: {len(covered1)}  @2: {len(covered2)}  '
        f'@4 (oracle within audited): {len(covered4)}')
  print()

  print('per class: covered@2 / covered@4 / total')
  for class_name, class_words in _CLASSES.items():
    present = [w for w in class_words if w in audited]
    c2 = sum(1 for w in present if survivor_rank[w] in (1, 2))
    c4 = sum(1 for w in present if survivor_rank[w] is not None)
    print(f'  {class_name:15s} {c2:2d} / {c4:2d} / {len(present)}')
  print()

  print('uncovered words (no survivor in ranker-top-4):')
  for word in words:
    if survivor_rank[word] is None:
      print(f'  {word}')
  print()

  print('sample survivors (first per covered word):')
  for word in covered4:
    print(f'  {word:8s} [rank {survivor_rank[word]}] "{survivors[word][0]}"')


if __name__ == '__main__':
  main()
