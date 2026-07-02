# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Two-tier eval loop for setter-prompt variants.

Tier 1 (cheap iteration): run a variant over a fixed 12-word panel x N
runs, screen-only (26B judge), and report screen-pass rate + generated
tokens + seconds. The headline efficiency metric is minutes of generated
compute per screen-bankable clue — the local proxy for the campaign's
minutes-per-banked-clue objective.

Tier 2 (adoption gate): run the 31B confirm judge over a tier-1 result
file's screen-bankable clues. Only tier-2-confirmed wins get adopted into
pipeline_local.py. Confirmed clues are real inventory under the bank-shape
goal, so --bank appends them to the clue bank with eval provenance.

Replay: each tier-1 run archives the full setter conversation. When a
variant only changes later turns (rendered prompt text identical up to
turn k), --replay-from reuses the archived replies for the common prefix —
a paired comparison that cuts both compute and run-to-run noise.

Usage:
  python eval_panel.py --variant baseline --runs 3
  python eval_panel.py --variant edit-cap --runs 3 \
      --replay-from evals/eval_baseline_<stamp>.jsonl
  python eval_panel.py --report evals/eval_*.jsonl
  python eval_panel.py --tier2 evals/eval_edit-cap_<stamp>.jsonl [--bank]
"""

import argparse
import datetime
import glob
import json
import pathlib
import statistics

import httpx

import pipeline_local as pl

_RESULTS_DIR = pathlib.Path(__file__).parent / 'evals'

_SETTER_MODEL = 'gemma4:26b-qat'
_SCREEN_MODEL = 'gemma4:26b-qat'
_CONFIRM_MODEL = 'gemma4:31b-qat'
_DIFFICULTY = 'medium'

# Fixed iteration panel: 6 words with pipeline history + 6 fresh, mixing
# friendly categories with known-hard ones (TWENTY, GROSS, SCORE, PAIR
# carry number senses). Held-out words stay reserved for final evals.
_PANEL = ['SCORE', 'DAISY', 'GRANT', 'CHECK', 'GASP', 'AMBER',
          'TWENTY', 'GROSS', 'PAIR', 'VIOLET', 'ROBIN', 'STOCK']

# --- Variant definitions -------------------------------------------------
# A variant is: system prompt, ordered turns of (template, schema, extra
# ollama options), and the index of the edit turn (for runaway stats).
# The 2026-07-02 round's variants (edit-cap, align-quest, every-keep,
# align-keep, no-difficulty) were adopted into pipeline_local v9 or
# killed; their definitions live in git history.

_VARIANTS = {
  # Current pipeline prompts (v9): the reference point.
  'baseline': {
    'system': pl._SETTER_SYSTEM,
    'turns': [(pl._TURN_ANGLES, None, {}), (pl._TURN_DRAFTS, None, {}),
              (pl._TURN_EDIT, None, {}), (pl._TURN_EXTRACT,
                                          pl._CLUES_SCHEMA, {})],
    'edit_index': 2,
  },
}


# --- Tier-1 runner -------------------------------------------------------

def _chat_full(model, messages, schema=None, options=None):
  """Ollama chat returning the full envelope (content + token counts +
  duration), unlike pipeline_local._chat which returns content only."""
  body = {
    'model': model, 'messages': messages, 'stream': False, 'think': False,
    'keep_alive': '30m',
    'options': {'num_ctx': 16384,
                'temperature': 1.0 if schema is None else 0.2,
                **(options or {})},
  }
  if schema is not None:
    body['format'] = schema
  response = httpx.post(pl._OLLAMA_CHAT_URL, json=body, timeout=900.0)
  response.raise_for_status()
  return response.json()


def _turn_stats(envelope):
  return {
    'prompt_tokens': envelope.get('prompt_eval_count', 0),
    'output_tokens': envelope.get('eval_count', 0),
    'seconds': round(envelope.get('total_duration', 0) / 1e9, 1),
  }


def _load_replay(path):
  """Archived runs keyed by (word, run index) for prefix reuse."""
  archive = {}
  for line in pathlib.Path(path).read_text().splitlines():
    record = json.loads(line)
    archive[(record['word'], record['run'])] = record
  return archive


def _screen(word, clue_text):
  """Screen judge with token accounting (same contract as pl._judge)."""
  prompt = (
    'Judge this one clue. In "analysis": name the sense used, write the '
    'substitution sentence, and name any flaws — before the verdict.\n\n'
    + json.dumps({'word': word, 'clue': clue_text})
  )
  envelope = _chat_full(
    _SCREEN_MODEL,
    [{'role': 'system', 'content': pl._JUDGE_SYSTEM},
     {'role': 'user', 'content': prompt}],
    schema=pl._JUDGE_SCHEMA,
  )
  verdict = json.loads(envelope['message']['content'])
  return verdict, _turn_stats(envelope)


def _run_one(variant, word, run_index, archived):
  """One panel word-run: setter turns (with prefix replay) + screen."""
  substitutions = {'word': word, 'difficulty': _DIFFICULTY}
  messages = [{'role': 'system', 'content': variant['system']}]
  turns = []
  replay_live = archived is not None

  for turn_index, (template, schema, options) in enumerate(variant['turns']):
    prompt = template.format(**substitutions)
    messages.append({'role': 'user', 'content': prompt})

    archived_turn = (archived['turns'][turn_index]
                     if replay_live and turn_index < len(archived['turns'])
                     else None)
    # Prefix replay stays valid only while the rendered prompt matches;
    # first divergence switches to live generation for the rest.
    if archived_turn and archived_turn['prompt'] == prompt:
      reply = archived_turn['reply']
      stats = {'prompt_tokens': 0, 'output_tokens': 0, 'seconds': 0.0,
               'replayed': True}
    else:
      replay_live = False
      envelope = _chat_full(_SETTER_MODEL, messages, schema=schema,
                            options=options)
      reply = envelope['message']['content']
      stats = _turn_stats(envelope)

    messages.append({'role': 'assistant', 'content': reply})
    turns.append({'prompt': prompt, 'reply': reply, **stats})

  try:
    extracted = json.loads(turns[-1]['reply'])
    clues = extracted['clues'] if 'clues' in extracted else [extracted]
  except (json.JSONDecodeError, TypeError):
    clues = []

  screens = []
  for clue in clues:
    if not isinstance(clue, dict) or not clue.get('clue'):
      continue
    verdict, stats = _screen(word, clue['clue'])
    screens.append({'clue': clue, **verdict, 'judge_stats': stats})

  return {'word': word, 'run': run_index, 'turns': turns,
          'screens': screens,
          'status': 'ok' if clues else 'extract_failed'}


def _run_tier1(variant_name, runs, replay_path):
  variant = _VARIANTS[variant_name]
  archive = _load_replay(replay_path) if replay_path else {}
  _RESULTS_DIR.mkdir(exist_ok=True)
  stamp = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
  out_path = _RESULTS_DIR / f'eval_{variant_name}_{stamp}.jsonl'

  for word in _PANEL:
    for run_index in range(runs):
      record = _run_one(variant, word, run_index,
                        archive.get((word, run_index)))
      record['variant'] = variant_name
      with out_path.open('a') as f:
        f.write(json.dumps(record) + '\n')
      verdicts = ','.join(s['verdict'] for s in record['screens']) or '-'
      print(f'{word} r{run_index}: {record["status"]} [{verdicts}]',
            flush=True)

  print(f'results: {out_path}')
  _report([str(out_path)])


# --- Reporting -----------------------------------------------------------

def _report(paths):
  """Scorecard per result file: pass rates, compute, edit-turn shape."""
  for pattern in paths:
    for path in sorted(glob.glob(pattern)):
      records = [json.loads(line)
                 for line in pathlib.Path(path).read_text().splitlines()]
      if not records:
        continue
      variant = records[0]['variant']
      # Retired variants stay reportable; every round so far kept the
      # edit turn at index 2.
      edit_index = _VARIANTS.get(variant, {}).get('edit_index', 2)

      n = len(records)
      extract_failed = sum(r['status'] == 'extract_failed' for r in records)
      screens = [s for r in records for s in r['screens']]
      bankable = sum(s['verdict'] == 'bankable' for s in screens)
      fixable = sum(s['verdict'] == 'fixable' for s in screens)
      bad = sum(s['verdict'] == 'bad' for s in screens)
      runs_with_pass = sum(
        any(s['verdict'] == 'bankable' for s in r['screens'])
        for r in records)

      gen_seconds = sum(t['seconds'] for r in records for t in r['turns'])
      gen_seconds += sum(s['judge_stats']['seconds'] for s in screens)
      gen_tokens = sum(t['output_tokens']
                       for r in records for t in r['turns'])
      replayed = sum(t.get('replayed', False)
                     for r in records for t in r['turns'])

      edit_chars = [len(r['turns'][edit_index]['reply']) for r in records
                    if not r['turns'][edit_index].get('replayed')]
      edit_line = (
        f'  edit-turn chars: median {statistics.median(edit_chars):.0f} '
        f'max {max(edit_chars)} over4k {sum(c > 4000 for c in edit_chars)}'
        if edit_chars else '  edit-turn chars: (all replayed)')

      minutes = gen_seconds / 60
      per_pass = f'{minutes / bankable:.1f}' if bankable else 'inf'
      print(f'== {variant}  ({pathlib.Path(path).name})')
      print(f'  word-runs {n}  extract-failed {extract_failed}  '
            f'clues {len(screens)}')
      print(f'  screen: {bankable} bankable / {fixable} fixable / '
            f'{bad} bad  ->  {runs_with_pass}/{n} runs '
            f'({100 * runs_with_pass / n:.0f}% of runs pass)')
      print(f'  compute: {minutes:.1f} generated min, {gen_tokens} output '
            f'tokens, {replayed} turns replayed')
      print(f'  minutes per screen-bankable clue: {per_pass}')
      print(edit_line)


# --- Dense-as-fixer: 31B repairs screen-fixable clues --------------------

_FIXER_SYSTEM = """\
You are an expert editor of American-style crossword clues. You receive a
clue for a given answer word together with an independent editor's
critique naming its flaw. Produce ONE corrected clue: fix exactly the
named flaw while keeping what the clue does well. Keep the surface
natural and vivid — an accurate-but-flat correction is a failure. The
clue must not contain the answer word or a trivial inflection of it."""


def _run_fixer(path):
  """Have the dense model repair each screen-fixable clue from a tier-1
  result file, then re-screen the repairs: measures how many fixables the
  demand-driven fixer converts to screen-bankable.

  Two batched phases (all 31B repairs, then all 26B re-screens): a gemma4
  model switch drains and rewires wired memory, so interleaving per clue
  would pay that cost twice per fixable."""
  records = [json.loads(line)
             for line in pathlib.Path(path).read_text().splitlines()]
  variant = records[0]['variant']
  fixables = [(r['word'], s) for r in records
              for s in r['screens'] if s['verdict'] == 'fixable']
  print(f'{variant}: {len(fixables)} screen-fixable clues to repair')

  seconds = 0.0
  repairs = []
  for word, screen in fixables:
    prompt = (
      f'Answer word: {word}\n'
      f'Clue: {screen["clue"]["clue"]}\n'
      f'Critique: {screen["analysis"]}\n\n'
      'Return the corrected clue as JSON: "clue" (exact print text), '
      '"difficulty" (honest calibration), "trap" (one sentence, or null '
      'if straight), "confidence" (honest).'
    )
    envelope = _chat_full(
      _CONFIRM_MODEL,
      [{'role': 'system', 'content': _FIXER_SYSTEM},
       {'role': 'user', 'content': prompt}],
      schema=pl._CLUE_SCHEMA,
    )
    seconds += _turn_stats(envelope)['seconds']
    try:
      repaired = json.loads(envelope['message']['content'])
    except json.JSONDecodeError:
      print(f'  {word}: repair parse failed', flush=True)
      continue
    if repaired['clue'].strip().lower() == \
       screen['clue']['clue'].strip().lower():
      print(f'  {word}: "{repaired["clue"]}" -> unchanged, skipped',
            flush=True)
      continue
    repairs.append((word, screen['clue']['clue'], repaired))

  converted = 0
  for word, original, repaired in repairs:
    verdict, stats = _screen(word, repaired['clue'])
    seconds += stats['seconds']
    if verdict['verdict'] == 'bankable':
      converted += 1
    print(f'  {word}: "{original}" -> "{repaired["clue"]}" '
          f'-> {verdict["verdict"]}', flush=True)

  rate = f'{100 * converted / len(fixables):.0f}%' if fixables else 'n/a'
  print(f'fixer: {converted}/{len(fixables)} converted to '
        f'screen-bankable ({rate}), {seconds / 60:.1f} minutes')


# --- Tier 2: confirm cascade on screen-passes ----------------------------

def _run_tier2(path, do_bank):
  """31B confirm over a result file's screen-bankable clues; optionally
  bank confirmed ones (they are real inventory, panel or not)."""
  records = [json.loads(line)
             for line in pathlib.Path(path).read_text().splitlines()]
  variant = records[0]['variant']
  candidates = [(r['word'], s['clue']) for r in records
                for s in r['screens'] if s['verdict'] == 'bankable']
  # A clue text can pass in multiple runs; confirm each pair only once.
  seen, unique = set(), []
  for word, clue in candidates:
    key = (word, clue['clue'].lower())
    if key not in seen:
      seen.add(key)
      unique.append((word, clue))

  print(f'{variant}: {len(unique)} unique screen-bankable clues to confirm')
  confirmed = 0
  seconds = 0.0
  for word, clue in unique:
    prompt = (
      'Judge this one clue. In "analysis": name the sense used, write the '
      'substitution sentence, and name any flaws — before the verdict.\n\n'
      + json.dumps({'word': word, 'clue': clue['clue']})
    )
    envelope = _chat_full(
      _CONFIRM_MODEL,
      [{'role': 'system', 'content': pl._JUDGE_SYSTEM},
       {'role': 'user', 'content': prompt}],
      schema=pl._JUDGE_SCHEMA,
    )
    verdict = json.loads(envelope['message']['content'])
    seconds += _turn_stats(envelope)['seconds']
    status = verdict['verdict']
    if status == 'bankable':
      confirmed += 1
      if do_bank:
        banked = pl._bank(word, clue, verdict['difficulty'], {
          'generator': _SETTER_MODEL, 'prompt_version': f'eval-{variant}',
          'judge': f'{_SCREEN_MODEL} + {_CONFIRM_MODEL}',
          'verdict': 'local-screen+confirm', 'source': 'eval-panel',
        })
        status += ' BANKED' if banked else ' duplicate'
    print(f'  {word}: "{clue["clue"]}" -> {status}', flush=True)

  rate = f'{100 * confirmed / len(unique):.0f}%' if unique else 'n/a'
  print(f'{variant}: {confirmed}/{len(unique)} confirmed ({rate}), '
        f'{seconds / 60:.1f} confirm-minutes')


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--variant', choices=sorted(_VARIANTS))
  parser.add_argument('--runs', type=int, default=3)
  parser.add_argument('--replay-from', default=None,
                      help='tier-1 results file to replay prefixes from')
  parser.add_argument('--report', nargs='+', default=None,
                      help='result files/globs to summarize')
  parser.add_argument('--tier2', default=None,
                      help='result file whose screen-passes to confirm')
  parser.add_argument('--bank', action='store_true',
                      help='with --tier2: bank confirmed clues')
  parser.add_argument('--fixer', default=None,
                      help='result file whose screen-fixables to repair')
  cli = parser.parse_args()

  if cli.report:
    _report(cli.report)
  elif cli.tier2:
    _run_tier2(cli.tier2, cli.bank)
  elif cli.fixer:
    _run_fixer(cli.fixer)
  elif cli.variant:
    _run_tier1(cli.variant, cli.runs, cli.replay_from)
  else:
    parser.error('pick one of --variant, --report, --tier2, --fixer')
