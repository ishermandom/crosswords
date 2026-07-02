# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""End-to-end local pipeline prototype: setter -> judge -> bank.

Per word: the v2 setter (the measured generation peak) produces one clue;
the per-clue judge screens it (J4 config); optionally a dense-model judge
confirms bankables (cascade). A "fixable" screen verdict earns one retry —
the judge's analysis is fed back into the setter conversation, mirroring
the cloud pipeline's revise path. Accepted clues append to
cluegen/local/clue_bank.jsonl with full provenance.

Self-contained per the prototyping independence rule: prompts and HTTP
are local to this file.

Usage:
  python cluegen/scratch/pipeline_local.py --word SUE
  python cluegen/scratch/pipeline_local.py --words words.txt --limit 10
  python cluegen/scratch/pipeline_local.py --word SUE --confirm-model gemma4:31b-qat
"""

import argparse
import datetime
import json
import pathlib
import sys

import httpx

_OLLAMA_CHAT_URL = 'http://localhost:11434/api/chat'
_BANK = pathlib.Path(__file__).parent.parent / 'local' / 'clue_bank.jsonl'
_LOG_DIR = pathlib.Path(__file__).parent / 'logs'

# --- Setter (v7 = v2 lineage, the measured generation peak) ---

_SETTER_SYSTEM = """\
You are an expert setter writing American-style (NYT-style) crossword clues
for an acrostic puzzle's clue bank. You will develop ONE original clue for a
given answer word at a given difficulty.

The contract: a single deceptive definition or description. No cryptic
wordplay grammar — the craft is misdirection within a natural surface.

Craft invariants, applying at every difficulty:
- Accuracy: the clue could substitute for the answer in a sentence —
  matching part of speech, tense, number, and register.
- Economy: every word earns its place; remove anything removable.
- Natural surface: reads like something a person would actually say or
  write.
- Liveliness: prefer the vivid, specific angle over the dictionary-flat
  one. Easy does not mean dull.
- Cleverness that needs a paragraph to justify is a craft failure.
- Self-contained: acrostic clues cannot cross-reference other entries.
- The clue must not contain the answer word or a trivial inflection of it.

Question mark: signals wordplay, a stretched definition, or definition-by-
example. Use it honestly; its absence promises straightness.

Failure modes to reject in your own work: padding words; surfaces no human
would write; misdirection by obscurity instead of ambiguity; a question
mark used as an apology; a trap that does not survive a re-read."""

_TURN_ANGLES = """\
Answer word: {word}
Target difficulty: {difficulty}

First, brainstorm cluing angles — at least 10, genuinely distinct. An angle
combines a surface domain (what the clue appears to be about) and the sense
or convention of the answer it exploits. For each angle: a short name, one
sentence on how it applies to {word}, and the wrong reading a solver would
chase (the trap), if the angle sets one.

No clue drafts yet — this turn is breadth, not phrasing. Plain unformatted
text; your output will be read by an LLM in the next turn."""

_TURN_DRAFTS = """\
Pick the 4 or 5 strongest angles for a {difficulty} clue — favor genuine
traps and lively surfaces over safe, predictable definitions. Draft exactly
one clue per chosen angle.

Three hard rules when drafting:
- The clue must define the answer word ITSELF — never a person or thing
  merely associated with it.
- If a sense exists only inside a longer phrase (an idiom fragment),
  discard the angle unless the clue genuinely works for the answer word
  alone.
- No dictionary-flat surfaces. A draft that could pass as a thesaurus
  entry or dictionary gloss is dead on arrival — each surface must put a
  specific scene, image, or wordplay in the solver's head. (Both clue
  IRIS: "Messenger from the clouds?" lives; "Part of the eye" is flat
  despite being accurate.)

For each draft: the clue text as it would appear in print, then on the next
line its angle name and the trap it sets — the specific wrong answer or
wrong reading the surface invites. Apply the craft invariants as you draft.
Plain unformatted text."""

_TURN_EDIT = """\
Now act as your own toughest editor. For EACH draft, perform the
substitution test — do not merely assert it. Write one natural sentence
using {word} in the clued sense, then rewrite the sentence with the clue's
definition in place of {word}. The draft fails if the rewritten sentence
changes part of speech, tense, number, or referent — or reads unnaturally.

Then check each surviving draft: question-mark honesty, no answer leakage,
whether the trap survives a re-read — and liveliness: CUT any draft that
reads like a dictionary gloss or thesaurus entry, however accurate. An
accurate-but-flat clue will be rejected downstream; it is not a safe pick.

End with a verdict line per draft: KEEP or CUT, with the one-phrase
reason. Plain unformatted text."""

_TURN_EXTRACT = """\
Select the single best KEEP clue for a {difficulty} target and return it as
JSON: "clue" (exact print text), "difficulty" (your honest calibration,
which may differ from the target), "trap" (one sentence naming the specific
wrong answer or wrong reading the surface invites; null if the clue is
straight), "confidence" (honest; "low" if no draft survived cleanly)."""

_TURN_RETRY = """\
An independent editor reviewed your selected clue and found a flaw:

{feedback}

Produce ONE corrected clue. If the editor names a specific fix (drop an
unearned question mark, retag the difficulty), apply exactly that fix and
change nothing else. Otherwise select and polish a different draft — one
whose surface is vivid, never dictionary-flat. Return the same JSON shape:
"clue", "difficulty", "trap", "confidence"."""

_CLUE_SCHEMA = {
  'type': 'object',
  'properties': {
    'clue': {'type': 'string'},
    'difficulty': {'type': 'string', 'enum': ['easy', 'medium', 'hard']},
    'trap': {'type': ['string', 'null']},
    'confidence': {'type': 'string', 'enum': ['high', 'medium', 'low']},
  },
  'required': ['clue', 'difficulty', 'trap', 'confidence'],
}

# --- Judge (J4 config: per-clue, few-shot, doubt-rule) ---

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
  pivots from finance to riverbank."""

_JUDGE_SCHEMA = {
  'type': 'object',
  'properties': {
    'analysis': {'type': 'string'},
    'difficulty': {'type': 'string', 'enum': ['easy', 'medium', 'hard']},
    'verdict': {'type': 'string', 'enum': ['bankable', 'fixable', 'bad']},
  },
  'required': ['analysis', 'difficulty', 'verdict'],
}


def _chat(model, messages, schema=None, think=False):
  body = {
    'model': model, 'messages': messages, 'stream': False, 'think': think,
    'keep_alive': '30m',
    'options': {'num_ctx': 16384,
                'temperature': 1.0 if schema is None else 0.2},
  }
  if schema is not None:
    body['format'] = schema
  response = httpx.post(_OLLAMA_CHAT_URL, json=body, timeout=900.0)
  response.raise_for_status()
  return response.json()['message']['content']


def _run_setter(model, word, difficulty, tee):
  """Drive the v7 setter conversation; returns (clue dict, messages)."""
  substitutions = {'word': word, 'difficulty': difficulty}
  messages = [{'role': 'system', 'content': _SETTER_SYSTEM}]
  for template, schema in [(_TURN_ANGLES, None), (_TURN_DRAFTS, None),
                           (_TURN_EDIT, None), (_TURN_EXTRACT, _CLUE_SCHEMA)]:
    messages.append({'role': 'user',
                     'content': template.format(**substitutions)})
    reply = _chat(model, messages, schema=schema)
    messages.append({'role': 'assistant', 'content': reply})
    tee(f'--- setter {template.splitlines()[0][:30]}...\n{reply}\n')
  return json.loads(messages[-1]['content']), messages


def _judge(model, word, clue_text, tee, label):
  prompt = (
    'Judge this one clue. In "analysis": name the sense used, write the '
    'substitution sentence, and name any flaws — before the verdict.\n\n'
    + json.dumps({'word': word, 'clue': clue_text})
  )
  content = _chat(
    model,
    [{'role': 'system', 'content': _JUDGE_SYSTEM},
     {'role': 'user', 'content': prompt}],
    schema=_JUDGE_SCHEMA,
  )
  verdict = json.loads(content)
  tee(f'--- judge[{label}] {verdict["verdict"]} ({verdict["difficulty"]}): '
      f'{verdict["analysis"][:160]}\n')
  return verdict


def _bank(word, clue, judge_difficulty, provenance):
  """Append an accepted clue, deduplicating on (word, clue text)."""
  existing = set()
  if _BANK.exists():
    for line in _BANK.read_text().splitlines():
      r = json.loads(line)
      existing.add((r['word'], r['clue']['clue'].lower()))
  if (word, clue['clue'].lower()) in existing:
    return False
  record = {
    'word': word,
    'clue': {'style': 'american', 'difficulty': judge_difficulty,
             'clue': clue['clue'], 'trap': clue['trap'],
             'confidence': clue['confidence']},
    'provenance': provenance,
    'ts': datetime.datetime.now(datetime.timezone.utc)
          .isoformat(timespec='seconds'),
  }
  with _BANK.open('a') as f:
    f.write(json.dumps(record) + '\n')
  return True


def _strip_unearned_mark(clue, analysis):
  """If the judge's complaint names the '?', return the clue with it
  stripped for a free re-judge; None when the tidy doesn't apply."""
  if not clue['clue'].endswith('?'):
    return None
  if 'question mark' not in analysis.lower():
    return None
  return {**clue, 'clue': clue['clue'][:-1].rstrip()}


def _process_word(word, cli, tee):
  """Setter -> screen -> (confirm) -> tidy/retry-once -> bank."""
  clue, messages = _run_setter(cli.setter_model, word, cli.difficulty, tee)
  attempt = 1
  was_tidied = False
  while True:
    screen = _judge(cli.judge_model, word, clue['clue'], tee,
                    f'screen a{attempt}')
    if screen['verdict'] == 'bankable':
      if cli.confirm_model:
        confirm = _judge(cli.confirm_model, word, clue['clue'], tee,
                         f'confirm a{attempt}')
        if confirm['verdict'] != 'bankable':
          screen = confirm
        else:
          verdict_path = 'screen+confirm'
          difficulty = confirm['difficulty']
      if not cli.confirm_model:
        verdict_path = 'screen-only'
        difficulty = screen['difficulty']
      if screen['verdict'] == 'bankable':
        banked = _bank(word, clue, difficulty, {
          'generator': cli.setter_model, 'prompt_version': 'v8',
          'judge': f'{cli.judge_model}'
                   + (f' + {cli.confirm_model}' if cli.confirm_model
                      else ''),
          'verdict': f'local-{verdict_path}', 'attempt': attempt,
          **({'fix': 'unearned ? stripped (mechanical tidy)'}
             if was_tidied else {}),
        })
        return f'BANKED ({verdict_path}, attempt {attempt})' if banked \
               else 'DUPLICATE'
    if screen['verdict'] == 'fixable' and not was_tidied:
      # A named ?-flaw is a one-character fix: strip and re-judge without
      # spending the setter retry.
      tidied = _strip_unearned_mark(clue, screen['analysis'])
      if tidied:
        clue = tidied
        was_tidied = True
        tee(f'--- tidy: stripped ? -> {clue["clue"]}\n')
        continue
    if screen['verdict'] == 'bad' or attempt >= 2:
      return f'DROPPED ({screen["verdict"]}, attempt {attempt})'
    messages.append({'role': 'user', 'content':
                     _TURN_RETRY.format(feedback=screen['analysis'])})
    reply = _chat(cli.setter_model, messages, schema=_CLUE_SCHEMA)
    messages.append({'role': 'assistant', 'content': reply})
    clue = json.loads(reply)
    tee(f'--- setter retry\n{reply}\n')
    attempt += 1


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--word', default=None)
  parser.add_argument('--words', default=None, help='file, one word/line')
  parser.add_argument('--limit', type=int, default=None)
  parser.add_argument('--difficulty', default='medium',
                      choices=['easy', 'medium', 'hard'])
  parser.add_argument('--setter-model', default='gemma4:26b-qat')
  parser.add_argument('--judge-model', default='gemma4:26b-qat')
  parser.add_argument('--confirm-model', default=None,
                      help='optional cascade confirm (e.g. gemma4:31b-qat)')
  parser.add_argument('--skip-banked', action='store_true',
                      help='skip words that already have any bank record')
  cli = parser.parse_args()

  if cli.word:
    words = [cli.word.upper()]
  else:
    words = [w.strip().upper()
             for w in pathlib.Path(cli.words).read_text().splitlines()
             if w.strip() and not w.startswith('#')]
  if cli.limit:
    words = words[:cli.limit]
  if cli.skip_banked and _BANK.exists():
    banked_words = {json.loads(line)['word']
                    for line in _BANK.read_text().splitlines() if line}
    words = [w for w in words if w not in banked_words]

  _LOG_DIR.mkdir(exist_ok=True)
  stamp = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
  log_path = _LOG_DIR / f'pipeline_{stamp}.log'
  with log_path.open('w') as log_file:
    def tee(text):
      log_file.write(text)
      log_file.flush()
    for word in words:
      tee(f'\n===== {word} =====\n')
      status = _process_word(word, cli, tee)
      print(f'{word}: {status}', flush=True)
      tee(f'{word}: {status}\n')
  print(f'log: {log_path}', file=sys.stderr)
