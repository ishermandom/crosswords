# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""End-to-end local pipeline prototype: setter -> judge -> bank.

v9 (eval-panel round, 2026-07-02): the setter's edit turn carries the judge's
earned-? calibration pair; extraction returns every KEEP; a 31B fixer repairs
screen-fixable clues in place of the old setter retry (45% measured conversion).
Work runs in model-batched phases — all 26B setter+screen work, then the 31B
confirm/repair block, then repair re-screens, then their confirms — because a
gemma4 model switch drains and rewires wired memory. Accepted clues append to
cluegen/local/clue_bank.jsonl with full provenance.

Self-contained per the prototyping independence rule: prompts and HTTP are local
to this file.

Usage: python cluegen/scratch/pipeline_local.py --word SUE python
cluegen/scratch/pipeline_local.py --words words.txt --limit 10
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
reason. Plain unformatted text.

Two calibration examples from the downstream editor, to apply during the
question-mark check:
- "A large body of salt water?" for OCEAN: the ? is unearned — a straight
  definition wearing a question mark. Strip the mark or cut the draft.
- "Bank deposit?" for SILT: the ? is earned — "bank" pivots from finance
  to riverbank.
Also re-verify the referent: the clue must define the answer ITSELF,
never a person, place, or thing merely associated with it."""

_TURN_EXTRACT = """\
Return EVERY clue you marked KEEP, ordered strongest first, as JSON:
"clues", a list where each item has "clue" (exact print text),
"difficulty" (your honest calibration of that clue, which may differ from
the {difficulty} target), "trap" (one sentence naming the specific wrong
answer or wrong reading the surface invites; null if the clue is
straight), and "confidence" (honest). If every draft was cut, return the
single strongest draft anyway with "confidence": "low" — never an empty
list."""

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

# minItems guards the constrained decode: without it, the trivially valid
# '{"clues": []}' is an escape hatch the model takes often.
_CLUES_SCHEMA = {
  'type': 'object',
  'properties': {
    'clues': {'type': 'array', 'items': _CLUE_SCHEMA, 'minItems': 1}
  },
  'required': ['clues'],
}

_FIXER_SYSTEM = """\
You are an expert editor of American-style crossword clues. You receive a
clue for a given answer word together with an independent editor's
critique naming its flaw. Produce ONE corrected clue: fix exactly the
named flaw while keeping what the clue does well. The draft's angle —
its image, misdirection, or trap — IS what the clue does well: repair
around it and carry it into the corrected clue's "trap" field. If the
named flaw cannot be fixed without discarding the angle, find a fresh
angle instead — an accurate-but-flat correction is a failure. When the
critique names flatness itself, rephrasing is no fix: the corrected
clue needs a genuine angle (an image, a pivot, a surprising fact). The
clue must not contain the answer word or a trivial inflection of it."""

# ---
#
# Judge (J4 config: per-clue, few-shot, doubt-rule) ---

_JUDGE_SYSTEM = """\
You are a demanding editor for an American-style crossword clue bank. A
mediocre bank is worse than a smaller good one; accepting a flawed clue is
the costly error.

Judge each clue's TEXT ONLY, on:
- Accuracy: the clue could substitute for the answer in a sentence — part
  of speech, tense, number, register all match; every content word is true
  of the answer in the clued sense; the clue defines the answer itself,
  never a person or thing merely associated with it, and never a sense
  that exists only inside a longer idiom. Test every qualifier and
  comparative literally against the fact: a modifier that overclaims,
  falsely implies, or leaves several answers fitting equally well is an
  accuracy flaw — and a charming surface does not excuse it.
- Natural surface: reads like something a person would actually say or
  write.
- Economy: every word earns its place. Padding hides behind charm too:
  a filler word or a spelled-out role where a tighter phrase does the
  same misdirecting work is a flaw worth naming.
- Liveliness: name what the clue makes a solver feel — an aha, elegance,
  fair resistance, a prize fact, or fun. A dictionary-flat clue is not
  bankable, however accurate; neither is recognition dressed up as fun —
  a clue that merely fuses the answer's stock associations or plainly
  states a fact everyone knows. A fact earns its keep by surprise or
  specificity; a relation to another quantity needs a pivot. The
  gradient cuts both ways: familiarity of the subject does NOT flatten a
  clue. A remark-worthy or specific fact needs no pivot on top of it,
  and a genuine sense pivot or misleading surface is an aha even when
  its subject is well known. Flatness is the absence of any pivot,
  surprise, or specificity — never the presence of common knowledge.
  Judge the surface before the fact: what does a solver first picture,
  and what shifts when the answer clicks? Misdirection, imagery, and
  register live in the surface — a clue can earn its basis entirely
  there, whatever the fact's familiarity.
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
genuine doubt, verdict "fixable", never "bankable" — but doubt means a
concrete flaw named in the analysis. If the analysis names no flaw, the
verdict is "bankable": vague unease is not a flaw.

The "basis" field commits your liveliness call: "none" means the clue
is a flat gloss and caps the verdict at "fixable"; a named basis with
no named flaw means "bankable". A named basis never excuses a flaw:
the substitution test and every other check still gate the verdict —
a charming pivot cannot rescue a definition that fails them.

Calibration examples — where the boundaries sit:

- "Spinal Tap amp's top setting" -> ELEVEN: bankable (medium; basis:
  prize-fact). A number is legitimately defined by what it counts, and
  this count is remark-worthy.
- "Innings in a standard ballgame" -> NINE: fixable. The same mechanism
  at its flat end: an accurate count everyone already knows, plainly
  stated. Liveliness grades the fact, not the mechanism.
- "Old enough to order a drink" -> TWENTYONE: fixable. Fuses the
  answer's stock associations — recognition, not surprise.
- "Corner piece?" -> ROOK: bankable (medium; basis: aha). The chess
  fact is schoolchild-familiar, but the surface points at a jigsaw
  puzzle — the pivot makes the leap, and the leap is the liveliness. A
  familiar domain does not flatten a clue whose surface misleads.
- "Castle-shaped chess piece" -> ROOK: fixable. The same familiar domain
  with no leap — a picture-dictionary entry.
- "Current affairs?" -> EELS: fixable. The pivot on "current" delights,
  but "affairs" defines nothing about eels — the substitution test
  fails, and no basis rescues a definition that fails it.
- "Heads down!" -> DUCK: bankable (easy; basis: fun). No pivot and no
  trap — the surface's own wit earns the bank. Fun or elegance in the
  image or register is a full basis, without misdirection.
- "Like a snowbird's November flight" -> SOUTHWARD: bankable (easy;
  basis: elegance). A straight description whose image does the work —
  an evocative picture of the answer's ordinary sense is a full basis,
  even with no wordplay at all.
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
    'basis': {
      'type': 'string',
      'enum': ['aha', 'elegance', 'resistance', 'prize-fact', 'fun', 'none'],
    },
    'difficulty': {'type': 'string', 'enum': ['easy', 'medium', 'hard']},
    'verdict': {'type': 'string', 'enum': ['bankable', 'fixable', 'bad']},
  },
  'required': ['analysis', 'basis', 'difficulty', 'verdict'],
}


def _chat(model, messages, schema=None, think=False):
  body = {
    'model': model,
    'messages': messages,
    'stream': False,
    'think': think,
    'keep_alive': '30m',
    'options': {
      'num_ctx': 16384,
      'temperature': 1.0 if schema is None else 0.2,
    },
  }
  if schema is not None:
    body['format'] = schema
  response = httpx.post(_OLLAMA_CHAT_URL, json=body, timeout=900.0)
  response.raise_for_status()
  return response.json()['message']['content']


def _run_setter(model, word, difficulty, tee):
  """Drive the setter conversation; returns the extracted KEEP clues."""
  substitutions = {'word': word, 'difficulty': difficulty}
  messages = [{'role': 'system', 'content': _SETTER_SYSTEM}]
  for template, schema in [
    (_TURN_ANGLES, None),
    (_TURN_DRAFTS, None),
    (_TURN_EDIT, None),
    (_TURN_EXTRACT, _CLUES_SCHEMA),
  ]:
    messages.append(
      {'role': 'user', 'content': template.format(**substitutions)}
    )
    reply = _chat(model, messages, schema=schema)
    messages.append({'role': 'assistant', 'content': reply})
    tee(f'--- setter {template.splitlines()[0][:30]}...\n{reply}\n')
  return json.loads(messages[-1]['content'])['clues']


def _judge(model, word, clue_text, tee, label):
  prompt = (
    'Judge this one clue. In "analysis", in order: (1) name the sense '
    'used and write the substitution sentence; (2) say what a solver '
    'first pictures on reading the surface, and what shifts when the '
    'answer clicks; (3) name the basis of satisfaction that moment '
    'earns, or "none"; (4) name any flaws. Then commit the basis in '
    'the "basis" field.\n\n' + json.dumps({'word': word, 'clue': clue_text})
  )
  content = _chat(
    model,
    [
      {'role': 'system', 'content': _JUDGE_SYSTEM},
      {'role': 'user', 'content': prompt},
    ],
    schema=_JUDGE_SCHEMA,
  )
  verdict = json.loads(content)
  tee(
    f'--- judge[{label}] {verdict["verdict"]} '
    f'({verdict["difficulty"]}, {verdict["basis"]}): '
    f'{verdict["analysis"][:160]}\n'
  )
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
    'clue': {
      'style': 'american',
      'difficulty': judge_difficulty,
      'clue': clue['clue'],
      'trap': clue['trap'],
      'confidence': clue['confidence'],
    },
    'provenance': provenance,
    'ts': datetime.datetime.now(datetime.UTC).isoformat(timespec='seconds'),
  }
  with _BANK.open('a') as f:
    f.write(json.dumps(record) + '\n')
  return True


def _strip_unearned_mark(clue, analysis):
  """If the judge's complaint names the '?', return the clue with it stripped
  for a free re-judge; None when the tidy doesn't apply.
  """
  if not clue['clue'].endswith('?'):
    return None
  if 'question mark' not in analysis.lower():
    return None
  return {**clue, 'clue': clue['clue'][:-1].rstrip()}


def _phase_generate_and_screen(words, cli, tee):
  """Phase A (26B): setter + per-clue screen for every word; the free mechanical
  ?-tidy fires here. Returns screen-bankable candidates and fixables (with the
  judge's critique) for the 31B phases.
  """
  candidates = []
  fixables = []
  for word in words:
    tee(f'\n===== {word} =====\n')
    clues = _run_setter(cli.setter_model, word, cli.difficulty, tee)
    for clue in clues:
      if not clue.get('clue'):
        continue
      screen = _judge(cli.judge_model, word, clue['clue'], tee, 'screen')
      if screen['verdict'] == 'fixable':
        # A named ?-flaw is a one-character fix: strip and re-judge.
        tidied = _strip_unearned_mark(clue, screen['analysis'])
        if tidied:
          clue = tidied
          tee(f'--- tidy: stripped ? -> {clue["clue"]}\n')
          screen = _judge(
            cli.judge_model, word, clue['clue'], tee, 'screen tidy'
          )
      if screen['verdict'] == 'bankable':
        candidates.append((word, clue))
      elif screen['verdict'] == 'fixable':
        fixables.append((word, clue, screen['analysis']))
      print(f'{word}: screen {screen["verdict"]} "{clue["clue"]}"', flush=True)
  return candidates, fixables


def _phase_confirm(candidates, cli, tee, provenance_extra):
  """Phase B/D (31B): confirm screen-bankables; bank the passes.

  Returns (bank count, confirm-fixables) — the latter carry the judge's critique
  so they can join the repair queue.
  """
  banked_count = 0
  fixables = []
  for word, clue in candidates:
    confirm = _judge(cli.confirm_model, word, clue['clue'], tee, 'confirm')
    if confirm['verdict'] != 'bankable':
      if confirm['verdict'] == 'fixable':
        fixables.append((word, clue, confirm['analysis']))
      print(
        f'{word}: confirm {confirm["verdict"]} "{clue["clue"]}"', flush=True
      )
      continue
    banked = _bank(
      word,
      clue,
      confirm['difficulty'],
      {
        'generator': cli.setter_model,
        'prompt_version': 'v9',
        'judge': f'{cli.judge_model} + {cli.confirm_model}',
        'verdict': 'local-screen+confirm',
        **provenance_extra,
      },
    )
    banked_count += banked
    print(
      f'{word}: {"BANKED" if banked else "duplicate"} "{clue["clue"]}"',
      flush=True,
    )
  return banked_count, fixables


def _phase_repair(fixables, cli, tee):
  """Phase B (31B): the fixer repairs each screen-fixable clue given the judge's
  critique. Returns repaired clues for phase-C re-screening.
  """
  repairs = []
  for word, clue, analysis in fixables:
    prompt = (
      f'Answer word: {word}\n'
      f'Clue: {clue["clue"]}\n'
      f'Critique: {analysis}\n\n'
      'Return the corrected clue as JSON: "clue" (exact print text), '
      '"difficulty" (honest calibration), "trap" (one sentence, or null '
      'if straight), "confidence" (honest).'
    )
    reply = _chat(
      cli.confirm_model,
      [
        {'role': 'system', 'content': _FIXER_SYSTEM},
        {'role': 'user', 'content': prompt},
      ],
      schema=_CLUE_SCHEMA,
    )
    repaired = json.loads(reply)
    tee(f'--- fixer[{word}] {clue["clue"]} -> {repaired["clue"]}\n')
    if repaired['clue'].strip().lower() == clue['clue'].strip().lower():
      continue
    repairs.append((word, repaired))
  return repairs


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--word', default=None)
  parser.add_argument('--words', default=None, help='file, one word/line')
  parser.add_argument('--limit', type=int, default=None)
  parser.add_argument(
    '--difficulty', default='medium', choices=['easy', 'medium', 'hard']
  )
  parser.add_argument('--setter-model', default='gemma4:26b-qat')
  parser.add_argument('--judge-model', default='gemma4:26b-qat')
  parser.add_argument(
    '--confirm-model',
    default='gemma4:31b-qat',
    help='dense confirm + fixer model',
  )
  parser.add_argument(
    '--skip-banked',
    action='store_true',
    help='skip words that already have any bank record',
  )
  cli = parser.parse_args()

  if cli.word:
    words = [cli.word.upper()]
  else:
    words = [
      w.strip().upper()
      for w in pathlib.Path(cli.words).read_text().splitlines()
      if w.strip() and not w.startswith('#')
    ]
  if cli.limit:
    words = words[: cli.limit]
  if cli.skip_banked and _BANK.exists():
    banked_words = {
      json.loads(line)['word']
      for line in _BANK.read_text().splitlines()
      if line
    }
    words = [w for w in words if w not in banked_words]

  _LOG_DIR.mkdir(exist_ok=True)
  stamp = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
  log_path = _LOG_DIR / f'pipeline_{stamp}.log'
  with log_path.open('w') as log_file:

    def tee(text):
      log_file.write(text)
      log_file.flush()

    # Model-batched phases: 26B, then 31B, then 26B, then 31B — three switches
    # per run regardless of word count.
    candidates, fixables = _phase_generate_and_screen(words, cli, tee)
    print(
      f'phase A: {len(candidates)} candidates, '
      f'{len(fixables)} fixables from {len(words)} words',
      flush=True,
    )
    banked, confirm_fixables = _phase_confirm(candidates, cli, tee, {})
    repairs = _phase_repair(fixables + confirm_fixables, cli, tee)
    rescreened = [
      (word, clue)
      for word, clue in repairs
      if _judge(cli.judge_model, word, clue['clue'], tee, 'screen repair')[
        'verdict'
      ]
      == 'bankable'
    ]
    print(
      f'fixer: {len(repairs)} repairs, {len(rescreened)} screen-bankable',
      flush=True,
    )
    # Repairs get one confirm shot; their fixables don't loop back.
    repair_banked, _ = _phase_confirm(
      rescreened, cli, tee, {'fix': 'fixer repair (31B)'}
    )
    banked += repair_banked
    print(f'banked {banked} clues from {len(words)} words', flush=True)
  print(f'log: {log_path}', file=sys.stderr)
