# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Shared harness for probe scripts.

Exports a single `run()` function. Per-task scripts supply the mode name,
system prompt template (with a {day} placeholder), and user prompt text;
the harness handles CLI parsing, Ollama HTTP, tee logging, and output.

Usage in a per-task script:

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from lib import harness

    harness.run('wordplay', _SYSTEM_PROMPT_TEMPLATE, _USER_PROMPT)
"""

import argparse
import datetime
import json
import pathlib
import sys
import time
from collections.abc import Mapping
from typing import IO

import httpx

_OLLAMA_CHAT_URL = 'http://localhost:11434/api/chat'
_DEFAULT_MODEL = 'gemma4:26b'
_DEFAULT_CLUE = 'Starts a fire?'
_DEFAULT_ANSWER = 'MATCH'
_DEFAULT_DAY = 'wed'

_DAY_DESCRIPTIONS: dict[str, str] = {
  'mon': (
    'Monday — the most accessible day. Clues are direct and unambiguous, '
    'with little or no misdirection and common vocabulary. Wordplay is '
    'acceptable when the mechanism is obvious.'
  ),
  'tue': (
    'Tuesday — one step up from Monday. Mild misdirection or wordplay is '
    'acceptable, but clues should resolve easily for a practiced solver. '
    'Vocabulary and references remain broadly accessible.'
  ),
  'wed': (
    'Wednesday — mid-week difficulty. Deliberate misdirection or wordplay is '
    'expected. References may be moderately niche. A practiced solver should '
    'need to consider multiple interpretations before the answer clicks.'
  ),
  'thu': (
    'Thursday — one of the hardest days. Strong misdirection and multi-layer '
    'wordplay are expected. References may be moderately specialized. Novice '
    'solvers should struggle; experienced solvers should enjoy the aha moment.'
  ),
  'fri': (
    'Friday — among the hardest. Strong misdirection, complex wordplay, and '
    'mid-range reference knowledge. Clues reward lateral thinking and '
    'persistence.'
  ),
  'sat': (
    'Saturday — the hardest themeless day. Strong misdirection, complex '
    'wordplay, and references that may be niche or specialist. Solvers expect '
    'to be genuinely challenged.'
  ),
}


class _Tee:
  """Write to multiple text streams simultaneously."""

  def __init__(self, *streams: IO[str]) -> None:
    self._streams = streams

  def write(self, text: str) -> None:
    """Write text to all streams, flushing each immediately."""
    for stream in self._streams:
      stream.write(text)
      stream.flush()


def _section(label: str) -> str:
  """Format a dashes section header for log readability (60 chars wide)."""
  return f'\n--- {label} {"-" * max(0, 55 - len(label))}\n\n'


def _as_int(value: object) -> int:
  """Return value as int if it's numeric, else 0."""
  return int(value) if isinstance(value, (int, float)) else 0


def _timing_section(
  data: Mapping[str, object],
  reasoning: str | None,
  content: str | None,
  wall_seconds: float,
) -> str:
  """Build the timing section string from native Ollama response fields.

  Durations from Ollama are in nanoseconds. The reasoning/content token
  split is estimated by character ratio — approximate but directionally
  useful for comparing prompt variants.
  """
  load_ns = _as_int(data.get('load_duration'))
  prefill_count = _as_int(data.get('prompt_eval_count'))
  prefill_ns = _as_int(data.get('prompt_eval_duration'))
  gen_count = _as_int(data.get('eval_count'))
  gen_ns = _as_int(data.get('eval_duration'))
  total_ns = _as_int(data.get('total_duration'))

  prefill_tps = prefill_count / prefill_ns * 1e9 if prefill_ns > 0 else 0.0
  gen_tps = gen_count / gen_ns * 1e9 if gen_ns > 0 else 0.0
  overhead_s = (total_ns - load_ns - prefill_ns - gen_ns) / 1e9

  reasoning_chars = len(reasoning) if reasoning else 0
  content_chars = len(content) if content else 0
  total_chars = reasoning_chars + content_chars
  if total_chars > 0 and gen_count > 0:
    reasoning_tok = round(gen_count * reasoning_chars / total_chars)
    content_tok = gen_count - reasoning_tok
  else:
    reasoning_tok = 0
    content_tok = gen_count

  lines = [
    _section('timing'),
    f'load:       {load_ns / 1e9:.1f} s\n',
    f'prefill:    {prefill_count} tok @ {prefill_tps:.0f} tok/s\n',
    f'generation: {gen_count} tok @ {gen_tps:.1f} tok/s\n',
    f'  ~reasoning: {reasoning_tok} tok (est.)\n',
    f'  ~content:   {content_tok} tok (est.)\n',
    f'overhead:   {overhead_s:.1f} s\n',
    f'wall:       {wall_seconds:.1f} s\n',
  ]
  return ''.join(lines)


def run(
  mode: str,
  system_prompt_template: str,
  user_prompt: str,
  json_schema: Mapping[str, object] | None = None,
) -> None:
  """Parse standard CLI args, fire the probe request, and write the log.

  Args:
    mode: Short label for the probe (e.g. 'wordplay'). Used as the log
      filename prefix and printed in the run header.
    system_prompt_template: System prompt with a {day} placeholder that is
      filled from the --day argument.
    user_prompt: Text appended after "Clue: X\\nAnswer: Y\\n\\n" in the
      user turn.
    json_schema: Optional JSON Schema dict constraining the model reply.
      Passed as the native Ollama `format` key. When set, the response is
      pretty-printed as JSON in the log.
  """
  parser = argparse.ArgumentParser(
    description=f'Probe the {mode!r} prompt against a local Ollama model.'
  )
  parser.add_argument('--clue', default=_DEFAULT_CLUE)
  parser.add_argument('--answer', default=_DEFAULT_ANSWER)
  parser.add_argument('--model', default=_DEFAULT_MODEL)
  parser.add_argument(
    '--day',
    choices=list(_DAY_DESCRIPTIONS),
    default=_DEFAULT_DAY,
    metavar='{mon,tue,wed,thu,fri,sat}',
    help='Target difficulty day (default: wed).',
  )
  arguments = parser.parse_args()

  system_prompt = system_prompt_template.format(
    day=_DAY_DESCRIPTIONS[arguments.day]
  )
  user_content = (
    f'Clue: {arguments.clue}\nAnswer: {arguments.answer}\n\n{user_prompt}'
  )
  messages: list[dict[str, str]] = [
    {'role': 'system', 'content': system_prompt},
    {'role': 'user', 'content': user_content},
  ]

  timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
  log_directory = pathlib.Path('logs/probe')
  log_directory.mkdir(parents=True, exist_ok=True)
  log_path = log_directory / f'{mode}_{timestamp}.log'

  with log_path.open('w') as log_file:
    tee = _Tee(sys.stdout, log_file)
    tee.write(
      f'=== {timestamp}'
      f' mode={mode}'
      f' model={arguments.model}'
      f' clue={arguments.clue!r}'
      f' answer={arguments.answer}'
      f' ===\n'
    )
    tee.write(f'{_section("system")}{system_prompt}\n')
    tee.write(f'{_section("user")}{user_content}\n')
    # Prompts are flushed above before the request fires, so a crash mid-run
    # still leaves an attributable record.

    request_body: dict[str, object] = {
      'model': arguments.model,
      'messages': messages,
      'stream': False,
      'keep_alive': '30m',
      'options': {
        'num_ctx': 8192,
        'temperature': 0.2,
        'frequency_penalty': 0.2,
        'top_k': 40,
        'top_p': 0.9,
        'repeat_penalty': 1.1,
        'num_gpu': -1,
      },
    }
    if json_schema is not None:
      request_body['format'] = json_schema

    start = time.perf_counter()
    http_response = httpx.post(
      _OLLAMA_CHAT_URL, json=request_body, timeout=600.0
    )
    elapsed = time.perf_counter() - start
    http_response.raise_for_status()
    data: dict[str, object] = http_response.json()

    raw_message = data.get('message')
    message: dict[str, object] = (
      raw_message if isinstance(raw_message, dict) else {}
    )
    thinking_raw = message.get('thinking')
    content_raw = message.get('content')
    reasoning = thinking_raw if isinstance(thinking_raw, str) else None
    content = content_raw if isinstance(content_raw, str) else None

    if reasoning:
      tee.write(f'{_section("reasoning")}{reasoning}\n')

    display_content = content or '<no response>'
    if json_schema is not None and content:
      try:
        display_content = json.dumps(json.loads(content), indent=2)
      except json.JSONDecodeError:
        pass
    tee.write(f'{_section("response")}{display_content}\n')
    tee.write(f'\n({elapsed:.0f}s)\n')

    tee.write(_timing_section(data, reasoning, content, elapsed))

  print(f'Log: {log_path}', file=sys.stderr)
