# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Evaluate a tuned setter served by `optiq serve` against the fixed panel.

Bare single-turn eval: each panel word gets the same prompt the adapter was
trained on, one completion per run, then the local screen judge (Ollama, same
judge prompt/schema as the pipeline) scores each clue. Standalone by design: the
judge prompt, schema, and panel are copied from the local-ceiling harness
(scratch/pipeline_local.py, scratch/eval_panel.py) rather than imported — that
branch belongs to another thread, and scratch code doesn't import across
(prototyping independence).

Usage: python eval_tuned.py [--runs N] [--words WORD ...] [--no-screen]
                       [--serve-url URL]

`optiq serve --adapter <path>` must be running; screening additionally needs the
shared Ollama server up with the screen model pulled.
"""

import argparse
import datetime
import json
import pathlib

import httpx

from prompts import DIFFICULTIES, PROMPT_TEMPLATE

_SERVE_URL_DEFAULT = 'http://127.0.0.1:8788/v1/chat/completions'
_OLLAMA_CHAT_URL = 'http://localhost:11434/api/chat'
_SCREEN_MODEL = 'gemma4:26b-qat'
_RESULTS_DIR = pathlib.Path(__file__).parent / 'evals'

# Fixed iteration panel — copied from scratch/eval_panel.py (local-ceiling).
_PANEL = ['SCORE', 'DAISY', 'GRANT', 'CHECK', 'GASP', 'AMBER',
          'TWENTY', 'GROSS', 'PAIR', 'VIOLET', 'ROBIN', 'STOCK']

# Screen judge contract — copied from scratch/pipeline_local.py (local-ceiling).
_JUDGE_SYSTEM = """\
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
- Liveliness: a dictionary-flat clue is not bankable, however accurate.
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

The costly error is banking a flawed clue. When your analysis leaves
genuine doubt, verdict "fixable", never "bankable".

Calibration examples — where the boundaries sit:

- "Innings in a standard ballgame" -> NINE: bankable (easy). A number is
  legitimately defined by what it counts; metonymic count clues are fine.
- "One who delivers your letters" -> MAIL: bad. Defines the mail CARRIER,
  not the answer itself.
- "Unwanted gift" -> ELEPHANT: bad. The sense lives only inside the idiom
  WHITE ELEPHANT.
- "You, old-style" -> THOU: bankable (medium). A secondary or archaic
  sense is fully legitimate.
- "Number of days in a week" -> SEVEN: fixable. Accurate but
  dictionary-flat.
- "A large body of salt water?" -> OCEAN: fixable. Straight definition
  wearing a question mark.
- "Bank deposit?" -> SILT: bankable (hard). The ? is earned: "bank"
  pivots from finance to riverbank.
- "Born to Die singer" -> LANA: bankable (medium). For a name answer, a
  famous bearer is a legitimate definition — the bearer is not "merely
  associated" with the name; she instantiates it."""

_JUDGE_SCHEMA = {
    'type': 'object',
    'properties': {
        'analysis': {'type': 'string'},
        'difficulty': {'type': 'string', 'enum': ['easy', 'medium', 'hard']},
        'verdict': {'type': 'string', 'enum': ['bankable', 'fixable', 'bad']},
    },
    'required': ['analysis', 'difficulty', 'verdict'],
}


def generate_clue(serve_url: str, word: str, difficulty: str) -> str:
  """One bare single-turn completion from the tuned setter."""
  body = {
      'messages': [
          {'role': 'user',
           'content': PROMPT_TEMPLATE.format(difficulty=difficulty,
                                             answer=word)},
      ],
      'max_tokens': 60,
      'temperature': 1.0,
  }
  response = httpx.post(serve_url, json=body, timeout=300.0)
  response.raise_for_status()
  return response.json()['choices'][0]['message']['content'].strip()


def screen_clue(word: str, clue_text: str) -> dict:
  """Screen judge verdict via Ollama — same contract as the pipeline's."""
  prompt = (
      'Judge this one clue. In "analysis": name the sense used, write the '
      'substitution sentence, and name any flaws — before the verdict.\n\n'
      + json.dumps({'word': word, 'clue': clue_text}))
  body = {
      'model': _SCREEN_MODEL,
      'messages': [
          {'role': 'system', 'content': _JUDGE_SYSTEM},
          {'role': 'user', 'content': prompt},
      ],
      'stream': False,
      'think': False,
      'keep_alive': '30m',
      'format': _JUDGE_SCHEMA,
      'options': {'num_ctx': 16384, 'temperature': 0.2},
  }
  response = httpx.post(_OLLAMA_CHAT_URL, json=body, timeout=900.0)
  response.raise_for_status()
  return json.loads(response.json()['message']['content'])


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--runs', type=int, default=1)
  parser.add_argument('--words', nargs='+', default=_PANEL)
  # The harness evals at medium; other values drive the steering spot-check.
  parser.add_argument('--difficulty', choices=DIFFICULTIES, default='medium')
  parser.add_argument('--no-screen', action='store_true')
  parser.add_argument('--serve-url', default=_SERVE_URL_DEFAULT)
  args = parser.parse_args()

  _RESULTS_DIR.mkdir(exist_ok=True)
  stamp = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
  out_path = _RESULTS_DIR / f'tuned_{stamp}.jsonl'

  for word in args.words:
    for run_index in range(args.runs):
      clue = generate_clue(args.serve_url, word, args.difficulty)
      record = {'word': word, 'run': run_index,
                'difficulty': args.difficulty, 'clue': clue}
      if not args.no_screen:
        record |= screen_clue(word, clue)
      with out_path.open('a') as file:
        file.write(json.dumps(record) + '\n')
      verdict = record.get('verdict', '-')
      print(f'{word} r{run_index}: {clue!r} [{verdict}]', flush=True)

  print(f'results: {out_path}')


if __name__ == '__main__':
  main()
