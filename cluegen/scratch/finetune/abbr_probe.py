# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Abbreviation-conditioning probe: has the model internalized the style rule
"an abbreviated answer gets an abbreviation-signaling clue, and only then"?

Case study for semantic style-rule learning generally (NYT style guide). The
signal is any abbreviated word in the clue (e.g. 'Sci.' cluing PHYS), with the
explicit ': Abbr.' tag as one special case — so two likelihood instruments:

- Swap cost (the general rule): for clues containing a lexicon word with an
  unambiguous abbreviated/expanded pair ('Sci.'/'Science'), score both forms
  under the true answer. D = NLL(abbreviated form) - NLL(expanded form). The
  intrinsic cost difference of the two surface forms is common to both answer
  groups, so the rule shows up as D(abbreviation answers) << D(full-word
  answers) — the diff-of-diffs.

- Marker cost (the tag special case): score the clue with and without a ':
  Abbr.' suffix; same diff-of-diffs logic.

Generation view: sample clues per answer and count abbreviation signals of any
kind (tag, 'for short'/'briefly', lexicon abbreviations, generic shortened words
like 'Wash.'). Rule internalized = high signal rate for abbreviation answers,
~zero for full-word answers.

Answer groups are drawn bank-wide from the Kaggle NYT CSV: abbreviation answers
are those that ever received a ': Abbr.'-tagged clue anywhere in the bank;
full-word answers are WordNet-known words. Every stage-1 train/valid answer
(possible memorization) and the panel/held-out words are excluded.

Compare base vs tuned to see what fine-tuning taught.

Usage: python abbr_probe.py [--adapter DIR] [--skip-generate]
"""

import argparse
import csv
import datetime
import json
import random
import re
from pathlib import Path

import wn

from loss_gaps import MODEL_REPO, WORDNET_DATA, response_loss
from optiq.mlx_lm_patches._register import register
from prompts import PROMPT_TEMPLATE

CSV_PATH = Path('/Users/Shared/data/kaggle-nyt/nytcrosswords.csv')
DATA_DIR = Path(__file__).parent / 'data' / 'data_stage1'

MARKER = ': Abbr.'
MARKER_SUFFIX = re.compile(r':\s*Abbr\.$', re.IGNORECASE)
MARKER_ANYWHERE = re.compile(r'\bAbbr\b')
MOJIBAKE_MARKERS = ('â€', 'Â', '�')

# Clue-frequent abbreviations whose expansion is unambiguous in either
# direction, chosen from a bank-wide frequency survey of dotted words in
# abbreviation-answer clues (2026-07-04). Deliberately omits: ambiguous forms
# (St., Dr., Fr., No., Mo.) and content-level signals whose expansion still
# announces an abbreviated answer ('abbr.', 'inits.').
ABBREVIATION_EXPANSIONS = (
    ('Sci.', 'Science'),
    ('Univ.', 'University'),
    ('Dept.', 'Department'),
    ('Org.', 'Organization'),
    ('Orgs.', 'Organizations'),
    ('Assn.', 'Association'),
    ('Natl.', 'National'),
    ('Amer.', 'American'),
    ('Corp.', 'Corporation'),
    ('Ave.', 'Avenue'),
    ('Mt.', 'Mount'),
    ('Mts.', 'Mountains'),
    ('Hosp.', 'Hospital'),
    ('Mag.', 'Magazine'),
    ('Bldg.', 'Building'),
    ('Mil.', 'Military'),
    ('Grp.', 'Group'),
    ('Grps.', 'Groups'),
    ('Sch.', 'School'),
    ('Subj.', 'Subject'),
    ('Fig.', 'Figure'),
    ('Figs.', 'Figures'),
    ('Agcy.', 'Agency'),
    ('Govt.', 'Government'),
    ('Meas.', 'Measure'),
    ('Amt.', 'Amount'),
    ('Amts.', 'Amounts'),
    ('Hrs.', 'Hours'),
    ('Med.', 'Medical'),
    ('Deg.', 'Degree'),
    ('Brit.', 'British'),
    ('Coll.', 'College'),
    ('Dir.', 'Direction'),
    ('Inc.', 'Incorporated'),
)


def _form_pattern(word: str) -> re.Pattern:
  """Word-boundary pattern for one lexicon form (dotted forms end at the
  period).
  """
  boundary = r'\b' if word[-1] != '.' else ''
  return re.compile(r'\b' + re.escape(word) + boundary, re.IGNORECASE)


ABBREVIATED_PATTERNS = tuple(
    _form_pattern(abbreviated) for abbreviated, _ in ABBREVIATION_EXPANSIONS)
EXPANDED_PATTERNS = tuple(
    _form_pattern(expanded) for _, expanded in ABBREVIATION_EXPANSIONS)


def has_single_form(clue: str) -> bool:
  """True if the clue's lexicon words are all abbreviated or all expanded — the
  swap must flip the whole clue to the opposite form, not mix forms.
  """
  has_abbreviated = any(p.search(clue) for p in ABBREVIATED_PATTERNS)
  has_expanded = any(p.search(clue) for p in EXPANDED_PATTERNS)
  return has_abbreviated != has_expanded

# Textual signals that mark an abbreviated answer without an abbreviated word.
PHRASE_SIGNALS = re.compile(r'\bAbbr\b|for short|briefly|in brief',
                            re.IGNORECASE)

# A shortened word: 2-6 letters then a period. Single letters (initialism chains
# like 'A.T.M.') intentionally don't match — initialisms in a clue don't signal
# an abbreviated answer.
GENERIC_ABBREVIATION = re.compile(r'\b[A-Za-z]{2,6}\.')

# Common non-signaling dotted words: Latin tags and titles.
NON_SIGNALING = {'e.g.', 'i.e.', 'etc.', 'mr.', 'mrs.', 'ms.', 'dr.', 'st.',
                 'jr.', 'sr.', 'vs.'}

# Panel + held-out answers (build_stage1_slice.py EXCLUDED_ANSWERS): reserved
# for evals, keep them out of instrument data too.
RESERVED_ANSWERS = {
    'SCORE', 'DAISY', 'GRANT', 'CHECK', 'GASP', 'AMBER',
    'TWENTY', 'GROSS', 'PAIR', 'VIOLET', 'ROBIN', 'STOCK',
    'COURT', 'SUE', 'HAZEL', 'SECOND', 'ZED', 'FORTY', 'DOZEN', 'NINETEEN',
}


def is_signaled(clue: str) -> bool:
  """True if the clue carries any abbreviation signal."""
  if PHRASE_SIGNALS.search(clue):
    return True
  for token in GENERIC_ABBREVIATION.findall(clue):
    if (token + '.').lower() not in NON_SIGNALING:
      return True
  return False


def swap_forms(clue: str) -> str | None:
  """The clue with every lexicon word flipped to its paired form, or None if no
  lexicon word occurs.
  """
  swapped = clue
  for abbreviated, expanded in ABBREVIATION_EXPANSIONS:
    for source, target in ((abbreviated, expanded), (expanded, abbreviated)):
      boundary = r'\b' + re.escape(source) + (r'\b' if source[-1] != '.'
                                              else '')
      pattern = re.compile(boundary, re.IGNORECASE)

      def match_case(match: re.Match) -> str:
        # Preserve the matched word's leading-letter case.
        if match.group(0)[0].islower():
          return target[0].lower() + target[1:]
        return target

      swapped = pattern.sub(match_case, swapped)
  return swapped if swapped != clue else None


def stage1_answers() -> set[str]:
  """Every answer in the stage-1 train/valid sets (their clues may be memorized,
  which would contaminate likelihood scores).
  """
  answers = set()
  for name in ('train.jsonl', 'valid.jsonl'):
    for line in (DATA_DIR / name).open():
      content = json.loads(line)['messages'][0]['content']
      answers.add(content.rsplit(': ', 1)[1])
  return answers


def bank_clues() -> tuple[dict[str, tuple[datetime.date, str]], set[str],
                          dict[str, set[str]]]:
  """(most-recent clean clue per answer, answers ever tagged ': Abbr.', every
  distinct tag-stripped clue per tagged answer).

  The pooled third element exists because tagged answers are rare: their swap
  instrument needs every historical clue, not just the latest.
  """
  latest: dict[str, tuple[datetime.date, str]] = {}
  tagged: set[str] = set()
  pooled: dict[str, set[str]] = {}
  with CSV_PATH.open(encoding='latin-1') as file:
    for row in csv.DictReader(file):
      answer, clue = row['Word'].strip(), row['Clue'].strip()
      if not answer or not clue:
        continue
      if any(marker in clue for marker in MOJIBAKE_MARKERS):
        continue
      if MARKER_SUFFIX.search(clue):
        tagged.add(answer)
      date = datetime.datetime.strptime(row['Date'], '%m/%d/%Y').date()
      if answer not in latest or date > latest[answer][0]:
        latest[answer] = (date, clue)
      pooled.setdefault(answer, set()).add(
          MARKER_SUFFIX.sub('', clue).strip())
  pooled = {answer: clues for answer, clues in pooled.items()
            if answer in tagged}
  return latest, tagged, pooled


def build_groups(group_size: int, seed: int) -> dict[str, dict[str, list]]:
  """Instrument items: groups['swap'|'marker']['abbreviation'|'full_word'].

  Swap items carry both clue forms; marker items carry a bare clue. Answer
  membership: 'abbreviation' = ever ': Abbr.'-tagged bank-wide; 'full_word' =
  WordNet-known, clue free of any abbreviation signal.
  """
  wn.config.data_directory = WORDNET_DATA
  excluded = stage1_answers() | RESERVED_ANSWERS
  latest, tagged, pooled = bank_clues()

  def swap_item(answer: str, bare: str) -> dict | None:
    """A swap candidate, or None if the clue can't host a clean swap.

    Quoted clues are rejected: a lexicon word inside a title ("American Dad!")
    can't change form without corrupting the reference.
    """
    if '"' in bare or MARKER_ANYWHERE.search(bare):
      return None
    if not has_single_form(bare):
      return None
    swapped = swap_forms(bare)
    if swapped is None:
      return None
    # The expanded variant must be signal-free: any dotted word or phrase signal
    # it still carries ('Geom. figure', 'Agency issuance, in brief') would sit
    # in BOTH variants and dampen the swap contrast.
    is_original_abbreviated = any(
        pattern.search(bare) for pattern in ABBREVIATED_PATTERNS)
    expanded_variant = swapped if is_original_abbreviated else bare
    if is_signaled(expanded_variant):
      return None
    return {'answer': answer, 'original': bare, 'swapped': swapped}

  candidates: dict[str, dict[str, list]] = {
      'swap': {'abbreviation': [], 'full_word': []},
      'marker': {'abbreviation': [], 'full_word': []},
  }

  # Abbreviation answers are rare, so their swap cell pools every historical
  # clue, grouped per answer for distinct-answer-first sampling below.
  swap_pool: dict[str, list[dict]] = {}
  for answer, clues in pooled.items():
    if answer in excluded or not answer.isalpha():
      continue
    items = [item for bare in sorted(clues)
             if (item := swap_item(answer, bare)) is not None]
    if items:
      swap_pool[answer] = items

  for answer, (date, clue) in latest.items():
    if answer in excluded or not answer.isalpha():
      continue
    is_abbreviation = answer in tagged
    is_full_word = (not is_abbreviation and 4 <= len(answer) <= 8
                    and bool(wn.synsets(answer.lower())))
    if not is_abbreviation and not is_full_word:
      continue
    group = 'abbreviation' if is_abbreviation else 'full_word'
    bare = MARKER_SUFFIX.sub('', clue).strip()

    if is_full_word:
      item = swap_item(answer, bare)
      if item is not None:
        candidates['swap']['full_word'].append(item)

    # Marker instrument: bare clue must carry no other signal, so the appended
    # tag is the only variable.
    if not is_signaled(bare) and ':' not in bare:
      candidates['marker'][group].append({'answer': answer, 'clue': bare})

  # Distinct answers first; a second clue from the same answer only if the pool
  # of answers runs out before group_size.
  pool_rng = random.Random(seed)
  answers_shuffled = sorted(swap_pool)
  pool_rng.shuffle(answers_shuffled)
  for round_index in range(2):
    for answer in answers_shuffled:
      if len(candidates['swap']['abbreviation']) >= group_size:
        break
      items = swap_pool[answer]
      if round_index < len(items):
        candidates['swap']['abbreviation'].append(
            items[round_index] if round_index == 0
            else pool_rng.choice(items[1:]))

  rng = random.Random(seed)
  groups: dict[str, dict[str, list]] = {}
  for instrument, by_group in candidates.items():
    groups[instrument] = {}
    for group, items in by_group.items():
      if len(items) < group_size:
        print(f'note: {instrument}/{group} has only {len(items)} candidates')
      groups[instrument][group] = rng.sample(
          items, min(group_size, len(items)))
  return groups


def clue_messages(answer: str, clue: str) -> list[dict]:
  """Prompt/response pair in the training shape, at medium difficulty."""
  content = PROMPT_TEMPLATE.format(difficulty='medium', answer=answer)
  return [{'role': 'user', 'content': content},
          {'role': 'assistant', 'content': clue}]


def abbreviated_first(item: dict) -> tuple[str, str]:
  """(abbreviated-form clue, expanded-form clue) for a swap item."""
  original_has_abbreviation = any(
      pattern.search(item['original']) for pattern in ABBREVIATED_PATTERNS)
  if original_has_abbreviation:
    return item['original'], item['swapped']
  return item['swapped'], item['original']


def score_swap_cost(model, tokenizer, by_group: dict) -> None:
  """D = NLL(abbreviated form) - NLL(expanded form), per answer group."""
  means = {}
  for group, items in by_group.items():
    if not items:
      continue
    costs = []
    for item in items:
      abbreviated, expanded = abbreviated_first(item)
      abbreviated_nll, _ = response_loss(
          model, tokenizer, clue_messages(item['answer'], abbreviated))
      expanded_nll, _ = response_loss(
          model, tokenizer, clue_messages(item['answer'], expanded))
      costs.append(abbreviated_nll - expanded_nll)
    means[group] = sum(costs) / len(costs)
    prefer_abbreviated = sum(1 for c in costs if c < 0) / len(costs)
    print(f'swap {group:>14}: abbreviated-form cost {means[group]:+.3f} nats '
          f'(n={len(costs)}, prefers abbreviated {prefer_abbreviated:.0%})')
  if len(means) == 2:
    print(f'swap {"diff-of-diffs":>14}: '
          f'{means["full_word"] - means["abbreviation"]:+.3f} '
          '(rule internalized => strongly positive)')


def score_marker_cost(model, tokenizer, by_group: dict) -> None:
  """Delta = NLL(clue + ': Abbr.') - NLL(clue), per answer group."""
  means = {}
  for group, items in by_group.items():
    if not items:
      continue
    deltas = []
    for item in items:
      bare_nll, _ = response_loss(
          model, tokenizer, clue_messages(item['answer'], item['clue']))
      marked_nll, _ = response_loss(
          model, tokenizer,
          clue_messages(item['answer'], item['clue'] + MARKER))
      deltas.append(marked_nll - bare_nll)
    means[group] = sum(deltas) / len(deltas)
    prefer_marked = sum(1 for d in deltas if d < 0) / len(deltas)
    print(f'marker {group:>12}: tag cost {means[group]:+.3f} nats '
          f'(n={len(deltas)}, prefers tagged {prefer_marked:.0%})')
  if len(means) == 2:
    print(f'marker {"diff-of-diffs":>12}: '
          f'{means["full_word"] - means["abbreviation"]:+.3f} '
          '(rule internalized => strongly positive)')


def sample_generations(model, tokenizer, by_group: dict, per_group: int,
                       samples: int) -> None:
  """Abbreviation-signal rate in sampled clues, per answer group."""
  from mlx_lm import generate
  from mlx_lm.sample_utils import make_sampler

  for group, items in by_group.items():
    signaled = 0
    examples = []
    for item in items[:per_group]:
      content = PROMPT_TEMPLATE.format(difficulty='medium',
                                       answer=item['answer'])
      prompt = tokenizer.apply_chat_template(
          [{'role': 'user', 'content': content}], add_generation_prompt=True)
      for _ in range(samples):
        text = generate(model, tokenizer, prompt=prompt,
                        sampler=make_sampler(temp=1.0), max_tokens=25)
        if is_signaled(text):
          signaled += 1
          examples.append(f'{item["answer"]}: {text!r}')
    total = min(per_group, len(items)) * samples
    print(f'generation {group:>14}: signal rate {signaled}/{total} '
          f'({signaled / total:.0%})')
    for example in examples[:5]:
      print(f'                {example}')


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--adapter', default=None)
  parser.add_argument('--model', default=MODEL_REPO)
  parser.add_argument('--group-size', type=int, default=40)
  parser.add_argument('--generate-count', type=int, default=20)
  parser.add_argument('--samples', type=int, default=3)
  parser.add_argument('--seed', type=int, default=20260704)
  parser.add_argument('--skip-generate', action='store_true')
  parser.add_argument('--swap-only', action='store_true',
                      help='score only the swap instrument (rerun mode)')
  args = parser.parse_args()

  groups = build_groups(args.group_size, args.seed)
  for instrument, by_group in groups.items():
    for group, items in by_group.items():
      example = items[0] if items else None
      print(f'{instrument}/{group}: {len(items)} items, e.g. {example}')

  register()
  from mlx_lm import load
  model, tokenizer = load(args.model, adapter_path=args.adapter)
  print(f'model: {args.model}  adapter: {args.adapter or "base"}')

  score_swap_cost(model, tokenizer, groups['swap'])
  if not args.swap_only:
    score_marker_cost(model, tokenizer, groups['marker'])
  if not args.skip_generate and not args.swap_only:
    sample_generations(model, tokenizer, groups['marker'],
                       args.generate_count, args.samples)


if __name__ == '__main__':
  main()
