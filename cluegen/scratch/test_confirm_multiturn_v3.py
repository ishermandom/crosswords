"""Offline checks for confirm_multiturn_v2e: panel majority, no model calls."""

import pathlib
import sys

SCRATCH = pathlib.Path('/Users/Shared/code/crosswords-local-ceiling/cluegen/scratch')
sys.path.insert(0, str(SCRATCH))

import pipeline_local  # noqa: E402

variant_path = SCRATCH / 'variants' / 'confirm_multiturn_v3.py'
exec(compile(variant_path.read_text(), str(variant_path), 'exec'))

assert hasattr(pipeline_local, 'CONFIRM_STAGE'), 'hook not installed'
stage = pipeline_local.CONFIRM_STAGE

CLEAN_ECONOMY = {'analysis': 'x', 'bloat_evidence': [], 'is_bloated': False}


def run(clue, economy_panel=None, **overrides):
  """Drive the stage with canned fields; economy_panel is a 3-item list."""
  turns = {
    'confirm.substitution': {
      'sentence_with_answer': 'x',
      'sentence_with_clue': 'x',
      'analysis': 'x',
      'points_at': 'answer',
      'other_object_name': '',
    },
    'confirm.truth': {'analysis': 'x', 'failing_qualifiers': []},
    'confirm.sense': {
      'analysis': 'x',
      'is_usable_sense': True,
      'is_commonly_known': True,
    },
    'confirm.liveliness': {
      'analysis': 'x',
      'basis': 'elegance',
      'has_wordplay': False,
      'difficulty': 'medium',
    },
  }
  for stage_name, fields in overrides.items():
    turns['confirm.' + stage_name].update(fields)
  panel_queue = list(economy_panel or [CLEAN_ECONOMY] * 3)

  def fake_judge_turn(stage_name, system, protocol, schema):
    del system, protocol, schema
    if stage_name == 'confirm.economy':
      return panel_queue.pop(0)
    return turns[stage_name]

  result = stage(fake_judge_turn, 'WORD', clue)
  assert not panel_queue, 'panel not fully consumed'
  return result


def vote(evidence):
  return {'analysis': 'x', 'bloat_evidence': evidence, 'is_bloated': True}


# --- majority gating ---
r = run('Night watchman on patrol')
assert r['verdict'] == 'bankable' and not r['advisories'], r

r = run('Night watchman on patrol',
        economy_panel=[vote(['on patrol']), CLEAN_ECONOMY, CLEAN_ECONOMY])
assert r['verdict'] == 'bankable', r
assert r['advisories'] == ['economy (minority): on patrol'], r

# Two of three is no longer enough — unanimity gates.
r = run('Night watchman on patrol',
        economy_panel=[vote(['on patrol']), vote(['watchman']), CLEAN_ECONOMY])
assert r['verdict'] == 'bankable', r
assert r['advisories'] == ['economy (minority): on patrol',
                           'economy (minority): watchman'], r

r = run('Night watchman on patrol',
        economy_panel=[vote(['on patrol'])] * 3)
assert r['verdict'] == 'fixable', r
assert r['flaws'] == ['economy: on patrol'], r

# A vote whose evidence quotes nothing from the clue does not count,
# so this unanimous-looking panel is really 2 of 3.
r = run('Night watchman on patrol',
        economy_panel=[vote(['the second half']), vote(['on patrol']),
                       vote(['on patrol'])])
assert r['verdict'] == 'bankable', r
assert r['advisories'] == ['economy (minority): on patrol'], r

# --- bad short-circuits skip the panel entirely ---
r = run('One who delivers your letters',
        economy_panel=[vote(['letters'])] * 3,
        substitution={'points_at': 'other_object',
                      'other_object_name': 'mail carrier'})
assert r['verdict'] == 'bad' and len(r['flaws']) == 1, r

# --- panel stacks onto an existing fixable ---
r = run('Old night watchman on patrol',
        economy_panel=[vote(['on patrol'])] * 3,
        truth={'failing_qualifiers': ['"Old" overclaims']})
assert r['verdict'] == 'fixable' and len(r['flaws']) == 2, r

# --- junk truth flags still filtered ---
r = run('A primary color', truth={'failing_qualifiers': ['A']})
assert r['verdict'] == 'bankable', r

# --- liveliness gates ---
r = run('Second planet from the sun', liveliness={'basis': 'none'})
assert r['verdict'] == 'fixable', r
assert r['flaws'] == ['liveliness: flat gloss, no basis'], r

r = run('Large wind machine?', liveliness={'basis': 'aha',
                                           'has_wordplay': False})
assert r['verdict'] == 'fixable', r
assert r['flaws'] == ['liveliness: unearned question mark'], r

r = run('Big fan?', liveliness={'basis': 'aha', 'has_wordplay': True})
assert r['verdict'] == 'bankable', r

r = run('Only planet that spins backward',
        liveliness={'basis': 'prize_fact'})
assert r['verdict'] == 'bankable', r

print('all v3 checks pass')
