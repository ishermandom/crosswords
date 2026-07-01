# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Quality-first local judge, calibrated against checkpoint-1 Fable verdicts.

Judges the archived checkpoint clues (text only — no submitted difficulty
label, no trap note) with a local model, then scores agreement against two
ground-truth mappings from checkpoint 1: Fable's raw accepts, and the
quality-adjusted classification (accept OR label-only revise = good clue).

Usage:
  python cluegen/scratch/judge_quality.py
  python cluegen/scratch/judge_quality.py --model gemma4:31b-qat
"""

import argparse
import datetime
import json
import pathlib

import httpx

_HERE = pathlib.Path(__file__).parent
_DATA = _HERE / 'checkpoint_clues.jsonl'
_OLLAMA_CHAT_URL = 'http://localhost:11434/api/chat'

# Checkpoint-1 revises whose only flaw was the label/trap metadata (see
# ceiling-log.md, criteria re-analysis). Everything else revised has a real
# text flaw.
_LABEL_ONLY = {
  ('v1', 'IRIS'), ('v2', 'DUCK'), ('v2', 'DRAFT'), ('v2', 'TEE'),
  ('v3', 'DUCK'), ('v3', 'IRIS'), ('v4', 'DUCK'), ('v5', 'DRAFT'),
  ('v5', 'IRIS'), ('v5', 'TWELVE'), ('v5', 'TEE'), ('v6', 'DUCK'),
  ('v6', 'MARK'),
}

_SYSTEM = """\
You are a demanding editor for an American-style crossword clue bank. A
mediocre bank is worse than a smaller good one; accepting a flawed clue is
the costly error.

Judge each clue's TEXT ONLY, on:
- Accuracy: the clue could substitute for the answer in a sentence — part
  of speech, tense, number, register all match; every content word is true
  of the answer in the clued sense; the clue defines the answer itself,
  never a person or thing merely associated with it, and never a sense
  that exists only inside a longer idiom.
- Natural surface: reads like something a person would actually say or
  write.
- Economy: every word earns its place.
- Liveliness: a dictionary-flat clue is not bankable, however accurate —
  the bank wants clues that are satisfying to solve.
- Question-mark honesty: a ? belongs only with genuine wordplay or a
  stretched definition; a straight definition takes none.
- Fair misdirection: when the surface misleads, the answer must be fair in
  retrospect.

Also assign each clue the difficulty its text actually achieves:
easy (direct, signposted), medium (less-first sense, mild ambiguity), or
hard (active misdirection).

Verdicts:
- "bankable" — publishable as-is at your assigned difficulty.
- "fixable" — one concrete text flaw; name it.
- "bad" — fundamentally flawed for this answer.
"""

_FEW_SHOT = """
Calibration examples — where the boundaries sit:

- "Innings in a standard ballgame" -> NINE: bankable (easy). A number is
  legitimately defined by what it counts; metonymic count clues are fine.
- "One who delivers your letters" -> MAIL: bad. Defines the mail CARRIER,
  a person associated with the answer — not the answer itself.
- "Unwanted gift" -> ELEPHANT: bad. The sense lives only inside the idiom
  WHITE ELEPHANT; ELEPHANT alone never means an unwanted gift.
- "You, old-style" -> THOU: bankable (medium). A secondary or archaic
  sense is fully legitimate — judge the sense the clue uses, not the
  word's most common sense.
- "Number of days in a week" -> SEVEN: fixable. Accurate but
  dictionary-flat — no angle, no life.
- "A large body of salt water?" -> OCEAN: fixable. Straight definition
  wearing a question mark; drop the ?.
- "Bank deposit?" -> SILT: bankable (hard). The ? is earned: "bank"
  pivots from finance to riverbank.
"""

_SCRATCHPAD_TEMPLATE = """\
Before any verdicts: for EACH clue below, write a brief analysis (2-3
sentences): name the sense of the answer the clue uses; write the
substitution sentence (a sentence where the clue's text replaces the
answer); then name any flaws against the criteria, or state that the clue
is clean. Plain text, one block per clue.

{clues}
"""

_TRANSCRIBE = """\
Now transcribe your analyses into verdicts, faithfully: a clue you found
clean is "bankable"; one concrete text flaw is "fixable"; fundamentally
flawed is "bad". Do not re-judge — encode what your analysis concluded.
Return JSON only.
"""

_USER_TEMPLATE = """\
Judge each clue below. Return JSON only.

{clues}
"""

_SCHEMA = {
  'type': 'object',
  'properties': {
    'verdicts': {
      'type': 'array',
      'items': {
        'type': 'object',
        'properties': {
          'word': {'type': 'string'},
          'verdict': {'type': 'string',
                      'enum': ['bankable', 'fixable', 'bad']},
          'difficulty': {'type': 'string',
                         'enum': ['easy', 'medium', 'hard']},
          'reason': {'type': 'string'},
        },
        'required': ['word', 'verdict', 'difficulty', 'reason'],
      },
    },
  },
  'required': ['verdicts'],
}


def _chat(model: str, messages: list[dict], schema: dict | None) -> str:
  body = {
    'model': model,
    'messages': messages,
    'stream': False,
    'think': False,
    'keep_alive': '30m',
    'options': {'num_ctx': 16384, 'temperature': 0.2},
  }
  if schema is not None:
    body['format'] = schema
  response = httpx.post(_OLLAMA_CHAT_URL, json=body, timeout=600.0)
  response.raise_for_status()
  return response.json()['message']['content']


def _judge_group(
  model: str, entries: list[dict], use_scratchpad: bool, use_few_shot: bool
) -> list[dict]:
  clue_lines = '\n'.join(
    json.dumps({'word': e['word'], 'clue': e['clue']['clue']})
    for e in entries
  )
  system = _SYSTEM + (_FEW_SHOT if use_few_shot else '')
  messages: list[dict] = [{'role': 'system', 'content': system}]
  if use_scratchpad:
    messages.append(
      {'role': 'user',
       'content': _SCRATCHPAD_TEMPLATE.format(clues=clue_lines)}
    )
    analysis = _chat(model, messages, schema=None)
    messages.append({'role': 'assistant', 'content': analysis})
    messages.append({'role': 'user', 'content': _TRANSCRIBE})
  else:
    messages.append(
      {'role': 'user', 'content': _USER_TEMPLATE.format(clues=clue_lines)}
    )
  return json.loads(_chat(model, messages, schema=_SCHEMA))['verdicts']


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--model', default='gemma4:26b-qat')
  parser.add_argument('--scratchpad', action='store_true')
  parser.add_argument('--fewshot', action='store_true')
  parser.add_argument('--quiet', action='store_true',
                      help='print mismatches and totals only')
  cli = parser.parse_args()

  groups: dict[str, list[dict]] = {}
  for line in _DATA.read_text().splitlines():
    entry = json.loads(line)
    groups.setdefault(entry['version'], []).append(entry)

  # Ground truth: raw Fable accepts from the latest checkpoint results.
  results_path = sorted((_HERE / 'logs').glob('checkpoint_2026*.jsonl'))[-1]
  # Key by (version, word) — unique outside controls; controls (which
  # repeat ZERO) key by clue text. Some Fable verdict lines omit 'clue'.
  fable: dict[tuple[str, str], str] = {}
  fable_control: dict[str, str] = {}
  for line in results_path.read_text().splitlines():
    record = json.loads(line)
    for v in record['verdicts']:
      if record['version'] == 'control':
        fable_control[v.get('clue', '')] = v['verdict']
      else:
        fable[(record['version'], v['word'])] = v['verdict']

  stamp = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
  out_path = _HERE / 'logs' / f'judge_calibration_{stamp}.jsonl'
  agree_raw = agree_adjusted = total = 0

  for version, entries in groups.items():
    verdicts = _judge_group(
      cli.model, entries, cli.scratchpad, cli.fewshot
    )
    by_word = {v['word']: v for v in verdicts}
    # Two ZERO controls share a word; match those by order instead.
    if version == 'control':
      by_word = None
    for i, e in enumerate(entries):
      local = verdicts[i] if by_word is None else by_word.get(e['word'])
      if local is None:
        print(f'{version} {e["word"]}: MISSING local verdict')
        continue
      if version == 'control':
        fable_verdict = fable_control.get(e['clue']['clue'], 'accept')
      else:
        fable_verdict = fable.get((version, e['word']), 'accept')
      is_good_raw = fable_verdict == 'accept'
      is_good_adjusted = (
        is_good_raw or (version, e['word']) in _LABEL_ONLY
      )
      local_good = local['verdict'] == 'bankable'
      total += 1
      agree_raw += local_good == is_good_raw
      agree_adjusted += local_good == is_good_adjusted
      row = {
        'version': version, 'word': e['word'],
        'clue': e['clue']['clue'], 'local': local['verdict'],
        'local_difficulty': local['difficulty'],
        'fable': fable_verdict,
        'quality_adjusted_good': is_good_adjusted,
        'reason': local['reason'],
      }
      with out_path.open('a') as f:
        f.write(json.dumps(row) + '\n')
      marker = '=' if local_good == is_good_adjusted else '!'
      if cli.quiet and marker == '=':
        continue
      print(f'{marker} {version:7s} {e["word"]:7s} '
            f'local={local["verdict"]:8s}({local["difficulty"]:6s}) '
            f'fable={fable_verdict:7s} adjusted_good={is_good_adjusted}')

  print(f'\nagreement vs raw accepts:      {agree_raw}/{total}')
  print(f'agreement vs quality-adjusted: {agree_adjusted}/{total}')
  print(f'rows: {out_path}')
