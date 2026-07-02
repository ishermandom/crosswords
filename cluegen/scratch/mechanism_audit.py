# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tag banked clues by satisfaction mechanism; report the distribution.

An offline diversity audit (see local/satisfaction.md): a bank that leans
on one trick reads tropey even when each clue is individually good. The
26B judge tags each record with a mechanism and anchor; the report shows
the spread and flags monoculture. Re-runnable as the bank grows; tags are
written to a sidecar file, never into the bank itself.

Usage:
  python cluegen/scratch/mechanism_audit.py            # tag new + report
  python cluegen/scratch/mechanism_audit.py --report   # report only
"""

import argparse
import collections
import json
import pathlib

from pipeline_local import _BANK, _chat

_TAGS = pathlib.Path(__file__).parent / 'mechanism_tags.jsonl'
_MODEL = 'gemma4:26b-qat'

# Alarm threshold: any single mechanism holding more than this share of
# the bank suggests monoculture worth investigating.
_MONOCULTURE_SHARE = 0.4

_MECHANISMS = [
  'sense pivot',
  'frame anchor',
  'count or role metonymy',
  'definition by example',
  'double definition',
  'conceptual reframe',
  'metaphor as definition',
  'vignette',
  'relational pivot',
  'prize fact',
  'plain definition',
]

_TAGGER_SYSTEM = """\
You classify American-style crossword clues by the mechanism that makes
them satisfying. Definitions:

- sense pivot: the surface leads with one sense of a polysemous word;
  the answer uses another ("Bank deposit?" SILT).
- frame anchor: the meaning lives inside a named cultural, regional, or
  professional frame ("Love, at Wimbledon" ZERO).
- count or role metonymy: the answer defined by what it counts or the
  role it plays ("Innings in a standard ballgame" NINE).
- definition by example: a specific instance stands in for the answer's
  class ("Jackson one might break?" TWENTY).
- double definition: two unrelated senses joined, each defining the
  answer ("Royal residence or tennis arena" COURT).
- conceptual reframe: an abstract property described concretely, as a
  small riddle ("It's next to nothing" ONE).
- metaphor as definition: a figurative description literally apt on
  inspection ("Prehistoric time capsule?" AMBER).
- vignette: a tiny scene the answer completes ("Reaction to a jump
  scare" GASP).
- relational pivot: the answer defined by its relation to another item,
  the relation itself carrying a surprise ("One-twelfth gross?" DOZEN).
- prize fact: a straight clue carried by interesting, checkable trivia
  ("Spinal Tap amp's top setting" ELEVEN).
- plain definition: a straight definition with none of the above.

Pick the DOMINANT mechanism; name the anchor (the knowledge that
legitimizes the answer) in a short phrase."""

_TAG_SCHEMA = {
  'type': 'object',
  'properties': {
    'mechanism': {'type': 'string', 'enum': _MECHANISMS},
    'anchor': {'type': 'string'},
  },
  'required': ['mechanism', 'anchor'],
}


def _bank_records():
  return [json.loads(line) for line in _BANK.read_text().splitlines() if line]


def _load_tags():
  """Existing tags keyed by (word, clue text)."""
  tags = {}
  if _TAGS.exists():
    for line in _TAGS.read_text().splitlines():
      tag = json.loads(line)
      tags[(tag['word'], tag['clue'])] = tag
  return tags


def _tag_new():
  """Tag bank records that have no sidecar entry yet."""
  tags = _load_tags()
  new_count = 0
  with _TAGS.open('a') as sidecar:
    for record in _bank_records():
      key = (record['word'], record['clue']['clue'])
      if key in tags:
        continue
      prompt = 'Classify this clue.\n\n' + json.dumps(
        {'word': key[0], 'clue': key[1]}
      )
      reply = _chat(
        _MODEL,
        [
          {'role': 'system', 'content': _TAGGER_SYSTEM},
          {'role': 'user', 'content': prompt},
        ],
        schema=_TAG_SCHEMA,
      )
      tag = {'word': key[0], 'clue': key[1], **json.loads(reply)}
      sidecar.write(json.dumps(tag) + '\n')
      sidecar.flush()
      new_count += 1
      print(
        f'{key[0]}: "{key[1]}" -> {tag["mechanism"]} ({tag["anchor"]})',
        flush=True,
      )
  print(f'tagged {new_count} new records')


def _report():
  tags = _load_tags()
  bank_keys = {(r['word'], r['clue']['clue']) for r in _bank_records()}
  tagged = [t for k, t in tags.items() if k in bank_keys]
  counts = collections.Counter(t['mechanism'] for t in tagged)
  total = len(tagged)
  print(f'{total} tagged of {len(bank_keys)} banked\n')
  for mechanism, count in counts.most_common():
    share = count / total
    alarm = '  <-- MONOCULTURE ALARM' if share > _MONOCULTURE_SHARE else ''
    print(f'  {mechanism:26s} {count:3d}  ({share:4.0%}){alarm}')


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument(
    '--report', action='store_true', help='report only; skip tagging'
  )
  cli = parser.parse_args()
  if not cli.report:
    _tag_new()
  _report()
