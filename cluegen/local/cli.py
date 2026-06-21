# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""CLI entry point.

Each run writes a timestamped DEBUG log to logs/ that captures all model
calls and the final result. Pass --verbose to also show DEBUG output on the
console (INFO is always shown).

Sample usage:

    clue-gen run --words words.txt --difficulty Thu --model gemma4:26b
    clue-gen generate --word ALPHA --difficulty Mon --model qwen2.5:0.5b
    clue-gen solvability --clue "Starts a fire?" --answer MATCH --difficulty Wed --model gemma4:26b
    clue-gen solvability --clues clues.txt --difficulty Wed --model gemma4:26b
    clue-gen quality --clue "Starts a fire?" --answer MATCH --difficulty Wed --model gemma4:26b
    clue-gen quality --clues clues.txt --difficulty Wed --model gemma4:26b
"""

import argparse
import dataclasses
import io
import json
import logging
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import NoReturn, TextIO

import openai

from cluegen.local.client import (
  ChatClient,
  GenerationError,
  Model,
  OllamaClient,
)
from cluegen.local.generator import ClueResult, generate_clue
from cluegen.local.input_parsing import ClueEntry, load_clue_entries, load_words
from cluegen.local.prompt import Difficulty
from cluegen.local.quality import QualityParseError, validate_quality
from cluegen.local.solvability import (
  DEFAULT_MAX_ANSWER_RANK,
  SolvabilityParseError,
  validate_solvability,
)

_logger = logging.getLogger(__name__)
_result_logger = logging.getLogger('cluegen.result_output')


def _section(label: str) -> str:
  """Format a dashes section header for log output (60 chars total)."""
  return f'\n--- {label} {"-" * max(0, 55 - len(label))}'


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


def _log_fatal(message: str) -> NoReturn:
  """Log an error and exit with a failure code."""
  _logger.error(message)
  sys.exit(1)


def _open_words_file(path: str) -> io.TextIOWrapper:
  """Open a word-list file; exit with an error message if not found."""
  try:
    return Path(path).open(encoding='utf-8')
  except FileNotFoundError:
    _log_fatal(f'file not found: {path}')


def _configure_logging(verbose: bool, logs_dir: Path | None) -> Path | None:
  """Set up console and file logging; return the log file path if created.

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
    # Wire _result_logger to the file handler only (no propagation) so that
    # _print_result output is captured in the log without appearing twice on
    # the terminal.
    _result_logger.propagate = False
    _result_logger.setLevel(logging.DEBUG)
    _result_logger.addHandler(file_handler)

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
  solvability_input = solvability_parser.add_mutually_exclusive_group(
    required=True
  )
  solvability_input.add_argument(
    '--clues',
    metavar='FILE',
    help=(
      'File with one "ANSWER clue text" entry per line; streams JSONL.'
      ' Use - for stdin.'
    ),
  )
  solvability_input.add_argument(
    '--clue', metavar='TEXT', help='Clue text to evaluate.'
  )
  solvability_parser.add_argument(
    '--answer',
    metavar='WORD',
    help='Target answer word (used to check guesses; withheld from the model).'
    ' Required with --clue.',
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
  quality_input = quality_parser.add_mutually_exclusive_group(required=True)
  quality_input.add_argument(
    '--clues',
    metavar='FILE',
    help=(
      'File with one "ANSWER clue text" entry per line; streams JSONL.'
      ' Use - for stdin.'
    ),
  )
  quality_input.add_argument(
    '--clue', metavar='TEXT', help='Clue text to evaluate.'
  )
  quality_parser.add_argument(
    '--answer',
    metavar='WORD',
    help='Target answer word. Required with --clue.',
  )
  _add_difficulty_arg(quality_parser)
  _add_model_arg(quality_parser)

  return parser.parse_args(argv)


def _generate_one(
  word: str,
  difficulty: Difficulty,
  client: ChatClient,
) -> ClueResult | None:
  """Call generate_clue; log the result and return None on failure."""
  try:
    result = generate_clue(word, difficulty, client)
  except openai.APIConnectionError:
    _logger.error(
      f'could not connect to Ollama (skipping {word!r}).'
      ' Is the server running? Try: ollama serve'
    )
    return None
  except GenerationError as error:
    _logger.error(f'error processing {word!r}: {error}')
    return None
  _logger.info(f'{result.word} → {result.clues[0]}')
  return result


def _print_result(data: object, output: TextIO) -> None:
  """The sole print path in the CLI — all stdout output must route here.

  Logs a section header via _logger (console + file in verbose mode), then
  prints to output, then logs the body via _result_logger (file only).
  This captures the full output in the log without duplicating it on the
  console.
  """
  _logger.debug(_section('result'))
  indent = 2 if getattr(output, 'isatty', lambda: False)() else None
  print(json.dumps(data, indent=indent), file=output)
  # The log is always for human review and never routed as tool input, so always
  # pretty-print.
  _result_logger.debug(f'\n{json.dumps(data, indent=2)}\n')


def _run_words(
  words: Sequence[str],
  difficulty: Difficulty,
  client: ChatClient,
  output: TextIO,
) -> None:
  """Generate clues for each word and write one JSONL result per word."""
  for word in words:
    result = _generate_one(word, difficulty, client)
    if result is None:
      _print_result({'error': f'failed to generate clue for {word!r}'}, output)
    else:
      _print_result(dataclasses.asdict(result), output)


def _load_clue_entries_input(clues: str, stdin: TextIO) -> list[ClueEntry]:
  """Load clue entries from a file path or from stdin when clues is '-'."""
  if clues == '-':
    return load_clue_entries(stdin)
  try:
    with Path(clues).open(encoding='utf-8') as f:
      return load_clue_entries(f)
  except FileNotFoundError:
    _log_fatal(f'file not found: {clues}')


def _check_solvability(
  clue_text: str,
  answer: str,
  difficulty: Difficulty,
  client: ChatClient,
  max_answer_rank: int,
  output: TextIO,
) -> None:
  """Run solvability check for one clue and write a compact JSON result."""
  try:
    result = validate_solvability(
      clue_text, answer, difficulty, client, max_answer_rank
    )
  except openai.APIConnectionError:
    _logger.error(
      'could not connect to Ollama. Is the server running? Try: ollama serve'
    )
    _print_result({'error': 'could not connect to Ollama'}, output)
    return
  except GenerationError as error:
    _logger.error(f'solvability check failed: {error}')
    _print_result({'error': str(error)}, output)
    return
  except SolvabilityParseError as error:
    _logger.error(f'solvability parse error: {error}')
    _print_result({'error': str(error)}, output)
    return
  _print_result({'is_solvable': result}, output)


def _run_quality(
  clue_text: str,
  answer: str,
  difficulty: Difficulty,
  client: ChatClient,
  output: TextIO,
) -> None:
  """Run quality evaluation for one clue and write a compact JSON result."""
  try:
    result = validate_quality(clue_text, answer, difficulty, client)
  except openai.APIConnectionError:
    _logger.error(
      'could not connect to Ollama. Is the server running? Try: ollama serve'
    )
    _print_result({'error': 'could not connect to Ollama'}, output)
    return
  except GenerationError as error:
    _logger.error(f'quality evaluation failed: {error}')
    _print_result({'error': str(error)}, output)
    return
  except QualityParseError as error:
    _logger.error(f'quality parse error: {error}')
    _print_result({'error': str(error)}, output)
    return
  _print_result(dataclasses.asdict(result), output)


def main(
  argv: list[str] | None = None,
  client: ChatClient | None = None,
  stdin: TextIO = sys.stdin,
  output: TextIO = sys.stdout,
  logs_dir: Path | None = Path(__file__).parent.parent / 'logs',
) -> None:
  """Entry point: dispatch to the appropriate subcommand handler."""
  args = _parse_args(argv)
  log_path = _configure_logging(args.verbose, logs_dir)
  _logger.info(f'command: {" ".join(sys.argv)}')
  _logger.info(f'model: {args.model}')
  if log_path:
    _logger.info(f'log: {log_path}')
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
    _run_words(words, args.difficulty, effective_client, output)
  elif args.subcommand == 'solvability':
    if args.clues:
      entries = _load_clue_entries_input(args.clues, stdin)
    else:
      if not args.answer:
        _log_fatal('--clue requires --answer')
      entries = [ClueEntry(answer=args.answer, clue_text=args.clue)]
    for entry in entries:
      _check_solvability(
        entry.clue_text,
        entry.answer,
        args.difficulty,
        effective_client,
        args.max_answer_rank,
        output,
      )
  elif args.subcommand == 'quality':
    if args.clues:
      entries = _load_clue_entries_input(args.clues, stdin)
    else:
      if not args.answer:
        _log_fatal('--clue requires --answer')
      entries = [ClueEntry(answer=args.answer, clue_text=args.clue)]
    for entry in entries:
      _run_quality(
        entry.clue_text, entry.answer, args.difficulty, effective_client, output
      )
