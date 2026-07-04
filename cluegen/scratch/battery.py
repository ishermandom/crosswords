# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Eval battery: the window's uniform scorecard, with a replay cache.

Runs the production cascade (26B screen, 31B confirm on screen-bankables) over
the labeled sets and reports agreement with the Fable reference:

- tuning: `satisfaction_reference_verdicts.jsonl` (32 clues; the set judge
  iterations tune against)
- holdout: `fresh_validation_verdicts.jsonl` (17 clues; consulted at adoption
  decisions only)

Every judge call is cached in `cache/judge_cache.jsonl`, keyed by the full call
material (model, prompts, schema, temperature, clue, sample index). A re-run
after changing one stage replays the other stage from cache — that is what makes
many ideas testable inside the window. Sample `i` is drawn once ever and
replayed forever, so comparisons across runs hold the unchanged stage constant.

Usage: python battery.py [--sets tuning,holdout] [--samples K] [--only WORD]
                    [--screen-temp T] [--confirm-temp T] [--patch file.py]
                    [--tag label]

`--patch` execs a python file after imports (it monkeypatches pipeline_local
attributes — prompt variants without editing the pipeline). `--only` limits to
one word for rung-0 smoke runs.

A patch may also install `pipeline_local.CONFIRM_STAGE`, a callable
`(judge_turn, word, clue) -> verdict dict`, replacing the single-turn confirm
with a multi-turn procedure. `judge_turn(stage, system, protocol, schema)` runs
one cached single-shot turn and returns its parsed fields; the returned verdict
dict needs at least a `verdict` key.

Verdict distributions print as b:f:x (bankable:fixable:bad) counts over the K
samples. A clue scores as held/killed only on a strict majority; ties count
against whichever success metric applies.
"""

import argparse
import collections
import datetime
import functools
import hashlib
import json
import pathlib
import sys
import time

import pipeline_local

_SCRATCH = pathlib.Path(__file__).parent
_SETS = {
  'tuning': _SCRATCH / 'satisfaction_reference_verdicts.jsonl',
  'holdout': _SCRATCH / 'fresh_validation_verdicts.jsonl',
  # Reject-bank records use the nested clue-dict schema; _load_set flattens them
  # and drops the 14 backfills that duplicate the tuning set.
  'rejects': _SCRATCH.parent / 'local' / 'reject_bank.jsonl',
  # Chunk-1 kills that Fable accepts — false-kill targets, probed explicitly
  # (not in the default sets).
  'losses': _SCRATCH / 'recall_loss_verdicts.jsonl',
  # Fable-generated graded fun-vs-flat pairs (idea 8 probe set; invented clues,
  # so usable for tuning without touching eval items).
  'funcal': _SCRATCH / 'fun_calibration_verdicts.jsonl',
  # The ~92-row expanded set (`#eval-expansion`, expansion_gen.py): invented
  # graded pairs over ten failure-taxonomy buckets, split pairs-atomic and
  # bucket-stratified (seed 7). Tune freely on gentune; genhold is consulted at
  # adoption decisions only, like holdout.
  'gentune': _SCRATCH / 'expansion_tune_verdicts.jsonl',
  'genhold': _SCRATCH / 'expansion_holdout_verdicts.jsonl',
}
_CACHE_PATH = _SCRATCH / 'cache' / 'judge_cache.jsonl'
_LOG_DIR = _SCRATCH / 'logs'

_SCREEN_MODEL = 'gemma4:26b-qat'
_CONFIRM_MODEL = 'gemma4:31b-qat'

# Fable verdicts and local-cascade verdicts use different vocabularies; this
# maps the reference onto the local scale for the agreement check.
_FABLE_TO_LOCAL = {'accept': 'bankable', 'revise': 'fixable', 'reject': 'bad'}


def _load_cache():
  """Cache-key → record dict, loaded from the append-only cache file."""
  cache = {}
  if _CACHE_PATH.exists():
    for line in _CACHE_PATH.read_text().splitlines():
      if line:
        record = json.loads(line)
        cache[record['key']] = record
  return cache


def _call_key(
  model, word, clue, sample, temperature, system, protocol, schema=None
):
  """Hash of everything that determines a judge call's distribution.

  `schema` defaults to the shared judge schema so single-turn keys stay
  byte-identical with the existing cache; multi-turn callers pass each turn's
  own schema.
  """
  material = json.dumps(
    {
      'model': model,
      'word': word,
      'clue': clue,
      'sample': sample,
      'temperature': temperature,
      'system': system,
      'protocol': protocol,
      'schema': pipeline_local._JUDGE_SCHEMA if schema is None else schema,
    },
    sort_keys=True,
  )
  return hashlib.sha256(material.encode()).hexdigest()


def _cached_judge(
  cache, stage, model, word, clue, sample, temperature, system, protocol
):
  """One judge verdict, from cache when the identical call was made before.

  Returns (verdict, was_cached).
  """
  key = _call_key(model, word, clue, sample, temperature, system, protocol)
  if key in cache:
    return cache[key]['verdict'], True
  pipeline_local.SCHEMA_TEMPERATURE = temperature
  started = time.time()
  verdict = pipeline_local._judge(
    model,
    word,
    clue,
    lambda text: None,
    stage,
    system=system,
    protocol=protocol,
  )
  record = {
    'key': key,
    'stage': stage,
    'model': model,
    'word': word,
    'clue': clue,
    'sample': sample,
    'temperature': temperature,
    'seconds': round(time.time() - started, 1),
    'ts': datetime.datetime.now(datetime.UTC).isoformat(timespec='seconds'),
    'verdict': verdict,
  }
  _CACHE_PATH.parent.mkdir(exist_ok=True)
  with _CACHE_PATH.open('a') as cache_file:
    cache_file.write(json.dumps(record) + '\n')
  cache[key] = record
  return verdict, False


def _cached_turn(
  cache,
  counts,
  model,
  word,
  clue,
  sample,
  temperature,
  stage,
  system,
  protocol,
  schema,
):
  """One turn of a multi-turn stage: a fresh single-shot call, cached.

  Unlike `_cached_judge`, the JSON schema is per-turn and the parsed reply is
  returned whole — a turn reports fields for the caller to aggregate, not a
  verdict. Cached under the same record shape, with the turn's fields in the
  `verdict` slot and the turn name (e.g. `confirm.substitution`) as `stage`.

  Parameter order puts the per-clue identity first so battery can bind it with
  `functools.partial` and hand variants a `judge_turn(stage, system, protocol,
  schema)` callable.
  """
  key = _call_key(
    model, word, clue, sample, temperature, system, protocol, schema
  )
  if key in cache:
    counts['hits'] += 1
    return cache[key]['verdict']
  pipeline_local.SCHEMA_TEMPERATURE = temperature
  started = time.time()
  prompt = protocol + json.dumps({'word': word, 'clue': clue})
  reply = pipeline_local._chat(
    model,
    [
      {'role': 'system', 'content': system},
      {'role': 'user', 'content': prompt},
    ],
    schema=schema,
  )
  fields = json.loads(reply)
  record = {
    'key': key,
    'stage': stage,
    'model': model,
    'word': word,
    'clue': clue,
    'sample': sample,
    'temperature': temperature,
    'seconds': round(time.time() - started, 1),
    'ts': datetime.datetime.now(datetime.UTC).isoformat(timespec='seconds'),
    'verdict': fields,
  }
  _CACHE_PATH.parent.mkdir(exist_ok=True)
  with _CACHE_PATH.open('a') as cache_file:
    cache_file.write(json.dumps(record) + '\n')
  cache[key] = record
  counts['calls'] += 1
  return fields


def _distribution(verdicts):
  """b:f:x count string over a list of verdict dicts (or Nones)."""
  counts = collections.Counter(
    verdict['verdict'] for verdict in verdicts if verdict
  )
  return f'{counts["bankable"]}:{counts["fixable"]}:{counts["bad"]}'


def _load_set(set_name):
  """Labeled records for one set, flattened to the reference schema."""
  records = []
  for line in _SETS[set_name].read_text().splitlines():
    if not line:
      continue
    record = json.loads(line)
    if set_name == 'rejects':
      record = {
        'word': record['word'],
        'clue': record['clue']['clue'],
        'verdict': record['label']['verdict'],
        'basis': record['label']['basis'],
        'source': record['source'],
      }
    record['eval_set'] = set_name
    records.append(record)
  if set_name == 'rejects':
    tuning_keys = {(r['word'], r['clue'].lower()) for r in _load_set('tuning')}
    records = [
      r for r in records if (r['word'], r['clue'].lower()) not in tuning_keys
    ]
  return records


def _majority(verdict_names):
  """The strict-majority verdict name, or 'split' on a tie."""
  ranked = collections.Counter(verdict_names).most_common()
  if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
    return 'split'
  return ranked[0][0]


def main():
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument('--sets', default='tuning,holdout,rejects')
  parser.add_argument('--samples', type=int, default=1)
  parser.add_argument(
    '--only', default=None, help='comma-separated words, rung-0/1 probes'
  )
  parser.add_argument(
    '--screen-temp', type=float, default=pipeline_local.SCHEMA_TEMPERATURE
  )
  parser.add_argument(
    '--confirm-temp', type=float, default=pipeline_local.SCHEMA_TEMPERATURE
  )
  parser.add_argument(
    '--patch',
    default=None,
    help="python file exec'd to monkeypatch pipeline_local",
  )
  parser.add_argument('--tag', default='battery')
  args = parser.parse_args()

  if args.patch:
    # The patch runs in its own namespace: functions it defines (e.g. a
    # CONFIRM_STAGE) then resolve the patch's module-level names through that
    # namespace. A bare exec here would scatter them into main's locals, where
    # deferred calls can't see them.
    patch_namespace = {}
    exec(
      compile(pathlib.Path(args.patch).read_text(), args.patch, 'exec'),
      patch_namespace,
    )

  records = []
  for set_name in args.sets.split(','):
    records.extend(_load_set(set_name))
  if args.only:
    wanted = set(args.only.split(','))
    records = [r for r in records if r['word'] in wanted]
    if not records:
      sys.exit(f'no records for words {args.only!r}')

  cache = _load_cache()
  screen_system = pipeline_local._JUDGE_SYSTEM
  screen_protocol = pipeline_local._SCREEN_PROMPT
  confirm_system = pipeline_local._CONFIRM_SYSTEM
  confirm_protocol = pipeline_local._CONFIRM_PROMPT
  confirm_stage = getattr(pipeline_local, 'CONFIRM_STAGE', None)
  counts = collections.Counter()
  started = time.time()

  # Pass 1 (26B): screen everything, K samples per clue.
  for record in records:
    record['screens'] = []
    for sample in range(args.samples):
      verdict, was_cached = _cached_judge(
        cache,
        'screen',
        _SCREEN_MODEL,
        record['word'],
        record['clue'],
        sample,
        args.screen_temp,
        screen_system,
        screen_protocol,
      )
      record['screens'].append(verdict)
      counts['hits'] += was_cached
      counts['calls'] += not was_cached
    print(
      f'screen {_distribution(record["screens"]):6s} '
      f'{record["word"]}: "{record["clue"]}"',
      flush=True,
    )

  # Pass 2 (31B): confirm sample i only where screen sample i was bankable, as
  # production routes.
  for record in records:
    record['confirms'] = []
    record['cascade'] = []
    for sample in range(args.samples):
      if record['screens'][sample]['verdict'] != 'bankable':
        record['confirms'].append(None)
        record['cascade'].append(record['screens'][sample]['verdict'])
        continue
      if confirm_stage:
        judge_turn = functools.partial(
          _cached_turn,
          cache,
          counts,
          _CONFIRM_MODEL,
          record['word'],
          record['clue'],
          sample,
          args.confirm_temp,
        )
        verdict = confirm_stage(judge_turn, record['word'], record['clue'])
      else:
        verdict, was_cached = _cached_judge(
          cache,
          'confirm',
          _CONFIRM_MODEL,
          record['word'],
          record['clue'],
          sample,
          args.confirm_temp,
          confirm_system,
          confirm_protocol,
        )
        counts['hits'] += was_cached
        counts['calls'] += not was_cached
      record['confirms'].append(verdict)
      record['cascade'].append(verdict['verdict'])
    if any(record['confirms']):
      print(
        f'confirm {_distribution(record["confirms"]):6s} '
        f'{record["word"]}: "{record["clue"]}"',
        flush=True,
      )

  stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
  log_path = _LOG_DIR / f'{args.tag}_{stamp}.jsonl'
  with log_path.open('w') as log:
    for record in records:
      log.write(json.dumps(record) + '\n')

  # Scorecard: per-set table, then the summary counts. Distributions are b:f:x
  # (bankable:fixable:bad) over the K samples.
  for set_name in args.sets.split(','):
    set_records = [r for r in records if r['eval_set'] == set_name]
    if not set_records:
      continue
    print(
      f'\n[{set_name}]\n'
      f'{"word":12s} {"fable":22s} {"screen":8s} {"cascade":8s} '
      f'{"majority":9s} agree?'
    )
    accepts_held = accepts_total = kills = nonaccepts_total = 0
    for record in set_records:
      majority = _majority(record['cascade'])
      fable_as_local = _FABLE_TO_LOCAL[record['verdict']]
      if record['verdict'] == 'accept':
        accepts_total += 1
        is_match = majority == 'bankable'
        accepts_held += is_match
      else:
        nonaccepts_total += 1
        is_match = majority not in ('bankable', 'split')
        kills += is_match
      fable_label = f'{record["verdict"]} ({record["basis"] or "-"})'
      cascade_counts = collections.Counter(record['cascade'])
      cascade_distribution = (
        f'{cascade_counts["bankable"]}:{cascade_counts["fixable"]}:'
        f'{cascade_counts["bad"]}'
      )
      print(
        f'{record["word"]:12s} {fable_label:22s} '
        f'{_distribution(record["screens"]):8s} {cascade_distribution:8s} '
        f'{majority:9s} {"yes" if is_match else "NO"}  "{record["clue"]}"'
      )
    print(
      f'{set_name}: accepts held {accepts_held}/{accepts_total}, '
      f'revises/rejects killed {kills}/{nonaccepts_total}'
    )

  minutes = (time.time() - started) / 60
  print(
    f'\n{counts["calls"]} model calls, {counts["hits"]} cache hits, '
    f'{minutes:.1f} min wall',
  )
  print(f'log: {log_path}', file=sys.stderr)


if __name__ == '__main__':
  main()
