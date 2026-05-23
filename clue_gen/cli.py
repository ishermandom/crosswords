# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""CLI entry point.

Each run writes a timestamped DEBUG log to logs/. Pass --verbose to also show
DEBUG output on the console (INFO is always shown).

Sample usage:

    clue-gen run --words words.txt --difficulty Thu --model gemma4:26b
    clue-gen generate --word ALPHA --difficulty Mon --model qwen2.5:0.5b
    clue-gen solvability --clue "Starts a fire?" --answer MATCH --difficulty Wed --model gemma4:26b
    clue-gen quality --clue "Starts a fire?" --answer MATCH --difficulty Wed --model gemma4:26b
"""

import argparse
import dataclasses
import io
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import NoReturn, TextIO

import openai

from clue_gen.client import ChatClient, GenerationError, Model, OllamaClient
from clue_gen.generator import ClueResult, generate_clue
from clue_gen.prompt import Difficulty
from clue_gen.quality import QualityParseError, validate_quality
from clue_gen.solvability import (
  DEFAULT_MAX_ANSWER_RANK,
  SolvabilityParseError,
  validate_solvability,
)
from clue_gen.word_parser import load_words

_logger = logging.getLogger(__name__)


def _add_difficulty_arg(parser: argparse.ArgumentParser) -> None:
  """Add the shared --difficulty argument to a subcommand parser."""
  parser.add_argument(
    '--difficulty',
    type=Difficulty,
    choices=list(Difficulty),
    default=Difficulty.THU,
    metavar='{Mon,Tue,Wed,Thu,Fri,Sat}',
    help='NYT crossword difficulty level (default: Thu).',
  )


def _add_model_arg(parser: argparse.ArgumentParser) -> None:
  """Add the shared --model argument to a subcommand parser."""
  parser.add_argument(
    '--model',
    type=Model,
    choices=list(Model),
    default=Model.GEMMA4_26B,
    metavar='{gemma4:31b,gemma4:26b,qwen2.5:0.5b}',
    help='Ollama model to use (default: gemma4:26b).',
  )


def _log_fatal(message: str, *args: object) -> NoReturn:
  """Log an error and exit with a failure code."""
  _logger.error(message, *args)
  sys.exit(1)


def _open_words_file(path: str) -> io.TextIOWrapper:
  """Open a word-list file; exit with an error message if not found."""
  try:
    return open(path, encoding='utf-8')
  except FileNotFoundError:
    _log_fatal('file not found: %s', path)


def _configure_logging(verbose: bool, logs_dir: Path | None) -> Path | None:
  """Set up console and file logging; return the log file path, or None.

  The console handler respects --verbose (DEBUG when set, INFO otherwise).
  When logs_dir is provided, a file handler always captures DEBUG with
  timestamps so every run has a complete record regardless of verbosity.
  Pass logs_dir=None to skip file logging (e.g. in tests).
  """
  root = logging.getLogger()
  root.setLevel(logging.DEBUG)

  console = logging.StreamHandler()
  console.setLevel(logging.DEBUG if verbose else logging.INFO)
  console.setFormatter(logging.Formatter('%(levelname)s %(name)s: %(message)s'))
  root.addHandler(console)

  log_path: Path | None = None
  if logs_dir is not None:
    logs_dir.mkdir(exist_ok=True)
    log_path = logs_dir / f'{datetime.now().strftime("%Y-%m-%dT%H-%M-%S")}.log'
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
      logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    )
    root.addHandler(file_handler)

  for name in ('httpx', 'httpcore', 'openai._base_client'):
    logging.getLogger(name).setLevel(logging.WARNING)

  return log_path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
  """Define and parse CLI arguments across all subcommands."""
  parser = argparse.ArgumentParser(
    description='Generate and evaluate crossword clues via a local Ollama model.',
  )
  parser.add_argument(
    '--verbose',
    action='store_true',
    help='Show DEBUG output on the console (file logs always capture DEBUG).',
  )
  subparsers = parser.add_subparsers(dest='subcommand', required=True)

  # --- run: full pipeline ---
  run_parser = subparsers.add_parser(
    'run',
    help='Run the full pipeline (clue generation + validation).',
  )
  run_input = run_parser.add_mutually_exclusive_group(required=True)
  run_input.add_argument(
    '--word',
    metavar='WORD',
    help='Single answer word; prints one JSON object.',
  )
  run_input.add_argument(
    '--words',
    metavar='FILE',
    help='Plain-text file with one word per line; streams JSONL. Use - for stdin.',
  )
  _add_difficulty_arg(run_parser)
  _add_model_arg(run_parser)

  # --- generate: clue generation only (no validation) ---
  generate_parser = subparsers.add_parser(
    'generate',
    help='Generate a clue without running validation.',
  )
  generate_input = generate_parser.add_mutually_exclusive_group(required=True)
  generate_input.add_argument(
    '--word',
    metavar='WORD',
    help='Single answer word; prints one JSON object.',
  )
  generate_input.add_argument(
    '--words',
    metavar='FILE',
    help='Plain-text file with one word per line; streams JSONL. Use - for stdin.',
  )
  _add_difficulty_arg(generate_parser)
  _add_model_arg(generate_parser)

  # --- solvability: blind solvability call only ---
  solvability_parser = subparsers.add_parser(
    'solvability', help='Run the blind solvability check on a clue.'
  )
  solvability_parser.add_argument(
    '--clue', required=True, metavar='TEXT', help='Clue text to evaluate.'
  )
  solvability_parser.add_argument(
    '--answer',
    required=True,
    metavar='WORD',
    help='Target answer word (used to check guesses; withheld from the model).',
  )
  _add_difficulty_arg(solvability_parser)
  _add_model_arg(solvability_parser)
  solvability_parser.add_argument(
    '--max-answer-rank',
    type=int,
    default=DEFAULT_MAX_ANSWER_RANK,
    metavar='N',
    help=f'Pass threshold: answer must appear within top N guesses (default: {DEFAULT_MAX_ANSWER_RANK}).',
  )

  # --- quality: answer-aware quality call only ---
  quality_parser = subparsers.add_parser(
    'quality', help='Run the answer-aware quality evaluation on a clue.'
  )
  quality_parser.add_argument(
    '--clue', required=True, metavar='TEXT', help='Clue text to evaluate.'
  )
  quality_parser.add_argument(
    '--answer', required=True, metavar='WORD', help='Target answer word.'
  )
  _add_difficulty_arg(quality_parser)
  _add_model_arg(quality_parser)

  return parser.parse_args(argv)


def _generate_one(
  word: str,
  difficulty: Difficulty,
  client: ChatClient,
) -> ClueResult | None:
  """Call generate_clue; log errors and return None on failure."""
  try:
    return generate_clue(word, difficulty, client)
  except openai.APIConnectionError:
    _logger.error(
      'could not connect to Ollama (skipping %r). Is the server running? Try: ollama serve',
      word,
    )
    return None
  except GenerationError as error:
    _logger.error('error processing %r: %s', word, error)
    return None


def _check_solvability(
  clue_text: str,
  answer: str,
  difficulty: Difficulty,
  client: ChatClient,
  max_answer_rank: int,
  output: TextIO,
) -> None:
  """Run solvability check for one clue and write the JSON result to output."""
  try:
    result = validate_solvability(
      clue_text, answer, difficulty, client, max_answer_rank
    )
  except openai.APIConnectionError:
    _logger.error(
      'could not connect to Ollama. Is the server running? Try: ollama serve'
    )
    print(
      json.dumps({'error': 'could not connect to Ollama'}, indent=2),
      file=output,
    )
    return
  except GenerationError as error:
    _logger.error('solvability check failed: %s', error)
    print(json.dumps({'error': str(error)}, indent=2), file=output)
    return
  except SolvabilityParseError as error:
    _logger.error('solvability parse error: %s', error)
    print(json.dumps({'error': str(error)}, indent=2), file=output)
    return
  print(json.dumps({'is_solvable': result}, indent=2), file=output)


def _run_quality(
  clue_text: str,
  answer: str,
  difficulty: Difficulty,
  client: ChatClient,
  output: TextIO,
) -> None:
  """Run quality evaluation for one clue and write the JSON result to output."""
  try:
    result = validate_quality(clue_text, answer, difficulty, client)
  except openai.APIConnectionError:
    _logger.error(
      'could not connect to Ollama. Is the server running? Try: ollama serve'
    )
    print(
      json.dumps({'error': 'could not connect to Ollama'}, indent=2),
      file=output,
    )
    return
  except GenerationError as error:
    _logger.error('quality evaluation failed: %s', error)
    print(json.dumps({'error': str(error)}, indent=2), file=output)
    return
  except QualityParseError as error:
    _logger.error('quality parse error: %s', error)
    print(json.dumps({'error': str(error)}, indent=2), file=output)
    return
  print(json.dumps(dataclasses.asdict(result), indent=2), file=output)


def main(
  argv: list[str] | None = None,
  client: ChatClient | None = None,
  stdin: TextIO = sys.stdin,
  output: TextIO = sys.stdout,
  logs_dir: Path | None = Path('logs'),
) -> None:
  """Entry point: dispatch to the appropriate subcommand handler."""
  args = _parse_args(argv)
  log_path = _configure_logging(args.verbose, logs_dir)
  _logger.info('command: %s', ' '.join(sys.argv))
  if log_path is not None:
    _logger.info('log: %s', log_path)
  if model := getattr(args, 'model', None):
    _logger.info('model: %s', model)
  effective_client = client or OllamaClient(args.model)
  if args.subcommand in ('run', 'generate'):
    if args.word:
      words: list[str] = [args.word]
    elif args.words == '-':
      words = load_words(stdin)
    else:
      with _open_words_file(args.words) as f:
        words = load_words(f)
      if not words:
        _log_fatal('word list is empty')
    for word in words:
      result = _generate_one(word, args.difficulty, effective_client)
      if result is None:
        print(
          json.dumps({'error': f'failed to generate clue for {word!r}'}),
          file=output,
        )
      else:
        _logger.info('%s → %s', result.word, result.clues[0])
        print(json.dumps(dataclasses.asdict(result)), file=output)
  elif args.subcommand == 'solvability':
    _check_solvability(
      args.clue,
      args.answer,
      args.difficulty,
      effective_client,
      args.max_answer_rank,
      output,
    )
  elif args.subcommand == 'quality':
    _run_quality(
      args.clue,
      args.answer,
      args.difficulty,
      effective_client,
      output,
    )
