# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""CLI entry point.

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
from typing import NoReturn, TextIO

import openai

from clue_gen.client import ChatClient, GenerationError, Model, OllamaClient
from clue_gen.generator import ClueResult, generate_clue
from clue_gen.prompt import Difficulty
from clue_gen.solvability import DEFAULT_MAX_ANSWER_RANK, validate_solvability
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


def _configure_logging(verbose: bool) -> None:
  """Set up root logger and suppress HTTP stack noise."""
  log_level = logging.DEBUG if verbose else logging.INFO
  logging.basicConfig(
    level=log_level, format='%(levelname)s %(name)s: %(message)s'
  )
  for name in ('httpx', 'httpcore', 'openai._base_client'):
    logging.getLogger(name).setLevel(logging.WARNING)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
  """Define and parse CLI arguments across all subcommands."""
  parser = argparse.ArgumentParser(
    description='Generate and evaluate crossword clues via a local Ollama model.',
  )
  parser.add_argument(
    '--verbose',
    action='store_true',
    help='Enable DEBUG logging (per-call timing, token counts, and call details).',
  )
  subparsers = parser.add_subparsers(dest='subcommand', required=True)

  # --- run: full batch pipeline ---
  run_parser = subparsers.add_parser(
    'run',
    help='Run the full pipeline (clue generation + validation) on a word list.',
  )
  run_parser.add_argument(
    '--words',
    required=True,
    metavar='FILE',
    help='Plain-text file with one answer word or phrase per line.',
  )
  _add_difficulty_arg(run_parser)
  _add_model_arg(run_parser)

  # --- generate: clue generation only (no validation) ---
  generate_parser = subparsers.add_parser(
    'generate',
    help='Generate a clue for a single word without running validation.',
  )
  generate_parser.add_argument(
    '--word',
    required=True,
    metavar='WORD',
    help='Answer word to generate a clue for.',
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


def _run_pipeline(
  words_input: io.TextIOBase,
  difficulty: Difficulty,
  client: ChatClient,
  output: TextIO,
) -> None:
  """Run the batch pipeline: read words, generate clues, write JSON."""
  words = load_words(words_input)
  if not words:
    _log_fatal('word list is empty')
  results = _generate_clues(words, difficulty, client)
  print(
    json.dumps([dataclasses.asdict(r) for r in results], indent=2), file=output
  )


def _generate_clues(
  words: list[str],
  difficulty: Difficulty,
  client: ChatClient,
) -> list[ClueResult]:
  """Run the generation pipeline for each word, exiting on hard errors."""
  results = []
  for word in words:
    try:
      result = generate_clue(word, difficulty, client)
      results.append(result)
      _logger.info('%s → %s', result.word, result.clues[0])
    except openai.APIConnectionError:
      _logger.error(
        'could not connect to Ollama (skipping %r). Is the server running? Try: ollama serve',
        word,
      )
    except GenerationError as e:
      _logger.error('error processing %r: %s', word, e)
  return results


def _run_generate(args: argparse.Namespace) -> None:
  """Generate a clue for a single word and print JSON to stdout."""
  # TODO: call generate_clue(args.word, args.difficulty, OllamaClient(args.model))
  # TODO: print JSON result to stdout
  raise NotImplementedError


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
  print(json.dumps({'is_solvable': result}, indent=2), file=output)


def _run_quality(args: argparse.Namespace) -> None:
  """Run the quality evaluation on a single clue and print JSON to stdout."""
  # TODO: call validate_quality(args.clue, args.answer, args.difficulty,
  #   OllamaClient(args.model))
  # TODO: print JSON result to stdout (conventions, scale scores, pass/fail)
  raise NotImplementedError


def main(
  argv: list[str] | None = None,
  client: ChatClient | None = None,
  output: TextIO = sys.stdout,
) -> None:
  """Entry point: dispatch to the appropriate subcommand handler."""
  args = _parse_args(argv)
  _configure_logging(args.verbose)
  if args.subcommand == 'run':
    try:
      with open(args.words, encoding='utf-8') as f:
        _run_pipeline(
          f, args.difficulty, client or OllamaClient(args.model), output
        )
    except FileNotFoundError:
      _log_fatal('file not found: %s', args.words)
  elif args.subcommand == 'generate':
    _run_generate(args)
  elif args.subcommand == 'solvability':
    _check_solvability(
      args.clue,
      args.answer,
      args.difficulty,
      client or OllamaClient(args.model),
      args.max_answer_rank,
      output,
    )
  elif args.subcommand == 'quality':
    _run_quality(args)
