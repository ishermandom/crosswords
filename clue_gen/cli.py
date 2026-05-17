# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""CLI entry point."""

import argparse
import dataclasses
import json
import logging
import sys
from typing import NoReturn

import openai

from clue_gen.client import GenerationError, Model, OllamaClient
from clue_gen.generator import ClueResult, generate_clue
from clue_gen.prompt import Difficulty
from clue_gen.word_parser import load_words_file

_log = logging.getLogger(__name__)


def _log_fatal(msg: str, *args: object) -> NoReturn:
  """Log an error and exit with a failure code."""
  _log.error(msg, *args)
  sys.exit(1)


def _parse_args() -> argparse.Namespace:
  """Define and parse CLI arguments."""
  parser = argparse.ArgumentParser(
    description='Generate crossword clues via a local Ollama model.',
  )
  parser.add_argument(
    '--words',
    required=True,
    metavar='FILE',
    help='Plain-text file with one answer word or phrase per line.',
  )
  parser.add_argument(
    '--difficulty',
    type=Difficulty,
    choices=list(Difficulty),
    default=Difficulty.THU,
    metavar='{Mon,Tue,Wed,Thu,Fri,Sat}',
    help='NYT crossword difficulty level (default: Thu).',
  )
  parser.add_argument(
    '--model',
    type=Model,
    choices=list(Model),
    default=Model.GEMMA4_26B,
    metavar='{gemma4:31b,gemma4:26b,qwen2.5:0.5b}',
    help='Ollama model to use (default: gemma4:26b).',
  )
  return parser.parse_args()


def _load_words(path: str) -> list[str]:
  """Load words from path, exiting on missing file or empty list."""
  try:
    words = load_words_file(path)
  except FileNotFoundError:
    _log_fatal('file not found: %s', path)
  if not words:
    _log_fatal('word list is empty')
  return words


def _generate_clues(
  words: list[str],
  difficulty: Difficulty,
  client: OllamaClient,
) -> list[ClueResult]:
  """Run the generation pipeline for each word, exiting on hard errors."""
  results = []
  for word in words:
    try:
      result = generate_clue(word, difficulty, client)
      results.append(result)
      _log.info('%s → %s', result.word, result.clues[0])
    except openai.APIConnectionError:
      _log_fatal(
        'could not connect to Ollama. Is the server running? Try: ollama serve'
      )
    except GenerationError as e:
      _log_fatal('error processing %r: %s', word, e)
  return results


def main() -> None:
  """Entry point: parse args, generate clues, and print JSON to stdout."""
  logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
  # httpx (used internally by the openai package) logs every request at INFO.
  logging.getLogger('httpx').setLevel(logging.WARNING)
  args = _parse_args()
  words = _load_words(args.words)
  results = _generate_clues(words, args.difficulty, OllamaClient(args.model))
  print(json.dumps([dataclasses.asdict(r) for r in results], indent=2))
