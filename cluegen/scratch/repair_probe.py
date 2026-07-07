# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Repair-pass probe: judge-directed fixes for the fixable clues.

The rung 2–3 full-protocol runs left four fixables, each with a judge flaw list
in the agreed (non-disputed) region — mostly economy trims. This probe tests the
production repair loop: one repair turn per clue on the iteration model,
minimally changing the clue to fix the named flaws while keeping its image, then
the repaired texts go back through the full protocol (separate run,
quality-of-record model) via the `h1repair` battery set.

Usage: python3 repair_probe.py <rung_log.jsonl> [more logs...] Writes
h1_repaired.jsonl and prints before/after pairs.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import pipeline_local

_MODEL = 'gemma4:26b-qat'
_OUT = pathlib.Path(__file__).parent / 'h1_repaired.jsonl'

_REPAIR_PROMPT = """\
Answer word: {word}

This clue for {word} was judged nearly bankable, with named flaws:

Clue: {clue}
Flaws: {flaws}

Rewrite the clue with the SMALLEST change that fixes every named flaw
while keeping what the clue does well — its specific image, fact, or
misdirection. An "economy: X" flaw means the words X are removable; cut or
tighten them. A "sense: too obscure" flaw means the anchor needs a fairer
handle in the same sense, not a new sense. The result must still read as a
clue that could substitute for {word} in a sentence.

Reply with the repaired clue text alone, exactly as it would print —
no quotes, no commentary."""


def main() -> None:
  """Collect fixables from the given rung logs and repair each."""
  repaired = []
  for log_path in sys.argv[1:]:
    for line in pathlib.Path(log_path).read_text().splitlines():
      row = json.loads(line)
      confirm = row['confirms'][0]
      if confirm['verdict'] != 'fixable':
        continue
      # Probe finding (2026-07-07): only economy-family flaws convert;
      # sense/obscurity repairs fail and waste a re-judge. Decline them.
      if not all(flaw.startswith('economy') for flaw in confirm['flaws']):
        print(f'declined {row["word"]} (non-economy): {confirm["flaws"]}')
        continue
      prompt = _REPAIR_PROMPT.format(
        word=row['word'], clue=row['clue'], flaws='; '.join(confirm['flaws'])
      )
      messages = [
        {'role': 'system', 'content': pipeline_local._SETTER_SYSTEM},
        {'role': 'user', 'content': prompt},
      ]
      new_clue = pipeline_local._chat(_MODEL, messages).strip().strip('"')
      print(f'{row["word"]}:\n  before: {row["clue"]}\n  after:  {new_clue}')
      repaired.append({'word': row['word'], 'clue': new_clue})

  _OUT.write_text(''.join(json.dumps(r) + '\n' for r in repaired))
  print(f'\n{len(repaired)} repairs -> {_OUT}')


if __name__ == '__main__':
  main()
