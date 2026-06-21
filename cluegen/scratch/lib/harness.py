# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Shared harness for probe scripts.

Exports `parse_args()`, `run_messages()`, and a convenience `run()` wrapper.
Per-task scripts call `parse_args()` to get resolved CLI arguments, build a
message list from `SystemTurn` and `UserTurn` values, and pass it to
`run_messages()`. The harness handles Ollama HTTP, tee logging, and per-turn
and cumulative timing output.

Single-turn usage (via convenience wrapper):

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from lib import harness

    harness.run('wordplay', _SYSTEM_PROMPT_TEMPLATE, _USER_PROMPT)

Multi-turn usage:

    args = harness.parse_args('quality-multi')
    turns = [
        harness.SystemTurn('...'),
        harness.UserTurn(f'Clue: {args.clue}\\nAnswer: {args.answer}\\n\\n{TURN_1}'),
        harness.UserTurn(TURN_2, json_schema=_SCHEMA),
    ]
    harness.run_messages('quality-multi', turns, args, temperature=1.0)
"""

import argparse
import contextlib
import dataclasses
import datetime
import json
import pathlib
import sys
import time
from collections.abc import Mapping, Sequence
from typing import IO

import httpx

_OLLAMA_CHAT_URL = 'http://localhost:11434/api/chat'
_DEFAULT_MODEL = 'gemma4:26b'
_DEFAULT_CLUE = 'Starts a fire?'
_DEFAULT_ANSWER = 'MATCH'

# Reference rates for normalized wall time — hardware-independent comparison.
_NORM_PREFILL_TPS: float = 50.0
_NORM_GEN_TPS: float = 4.0


@dataclasses.dataclass(frozen=True)
class ProbeArgs:
  """Parsed and resolved CLI arguments, ready for probe use."""

  clue: str
  answer: str
  model: str


@dataclasses.dataclass(frozen=True)
class SystemTurn:
  """A system-role message."""

  content: str


@dataclasses.dataclass(frozen=True)
class UserTurn:
  """A user-role message with optional JSON schema and thinking control."""

  content: str
  json_schema: Mapping[str, object] | None = None
  use_thinking: bool = True


@dataclasses.dataclass(frozen=True)
class SeedTurn:
  """A pre-established user/assistant exchange injected without an LLM call.

  Used to seed a conversation with context from a prior run — e.g., the
  solve-first analysis established in a separate conversation. Both messages
  are appended to history and logged, but no request is fired.
  """

  user_content: str
  assistant_content: str


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
  label: str = 'timing',
  cumulative_wall_seconds: float | None = None,
  cumulative_norm_wall_seconds: float | None = None,
) -> str:
  """Build a timing section string from native Ollama response fields.

  Durations from Ollama are in nanoseconds. The reasoning/content token
  split is estimated by character ratio — approximate but directionally
  useful for comparing prompt variants.

  When cumulative_wall_seconds / cumulative_norm_wall_seconds are provided,
  both the wall and norm-wall lines include running totals (multi-turn runs).
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

  rule = '─' * 60
  if cumulative_wall_seconds is not None:
    summary_content = (
      f'  {gen_tps:.1f} tok/s'
      f'     turn {wall_seconds:.0f}s'
      f'     total {cumulative_wall_seconds:.0f}s'
    )
  else:
    summary_content = f'  {gen_tps:.1f} tok/s     {wall_seconds:.0f}s'
  summary_line = f'{rule}\n{summary_content}\n{rule}\n'

  if cumulative_wall_seconds is not None:
    wall_line = (
      f'wall:       {wall_seconds:.1f} s'
      f'  (total: {cumulative_wall_seconds:.1f} s)\n'
    )
  else:
    wall_line = f'wall:       {wall_seconds:.1f} s\n'

  norm_wall_s = prefill_count / _NORM_PREFILL_TPS + gen_count / _NORM_GEN_TPS
  if cumulative_norm_wall_seconds is not None:
    norm_wall_line = (
      f'norm wall:  {norm_wall_s:.1f} s'
      f'  (total: {cumulative_norm_wall_seconds:.1f} s)\n'
    )
  else:
    norm_wall_line = f'norm wall:  {norm_wall_s:.1f} s\n'

  lines = [
    _section(label),
    summary_line,
    '\n',
    f'load:       {load_ns / 1e9:.1f} s\n',
    f'prefill:    {prefill_count} tok @ {prefill_tps:.0f} tok/s\n',
    f'generation: {gen_count} tok @ {gen_tps:.1f} tok/s\n',
    f'  ~reasoning: {reasoning_tok} tok (est.)\n',
    f'  ~content:   {content_tok} tok (est.)\n',
    f'overhead:   {overhead_s:.1f} s\n',
    wall_line,
    norm_wall_line,
  ]
  return ''.join(lines)


def _run_user_turn(
  turn: UserTurn,
  history: list[dict[str, object]],
  args: ProbeArgs,
  temperature: float,
  tee: _Tee,
  turn_label: str,
  cumulative_wall_before: float | None,
  cumulative_norm_wall_before: float | None,
) -> tuple[str | None, int, float, float]:
  """Fire one LLM call for a user turn, update history, and log output.

  Args:
    turn: The user turn to execute.
    history: Conversation history, mutated in place.
    args: Resolved CLI arguments (model name, etc.).
    temperature: Sampling temperature for this call.
    tee: Log/stdout writer.
    turn_label: Label suffix for section headers (e.g. ' turn 1' or '').
    cumulative_wall_before: Running wall total before this turn, or None to
      omit cumulative stats from the timing section.
    cumulative_norm_wall_before: Running norm-wall total before this turn.

  Returns:
    (response_text, gen_tokens, wall_s, norm_wall_s) for the caller to
    accumulate into running totals.
  """
  history.append({'role': 'user', 'content': turn.content})
  tee.write(f'{_section(f"user{turn_label}")}{turn.content}\n')

  request_body: dict[str, object] = {
    'model': args.model,
    'messages': history,
    'stream': False,
    'keep_alive': '30m',
    'think': turn.use_thinking,
    'options': {
      'num_ctx': 8192,
      'temperature': temperature,
      'frequency_penalty': 0.2,
      'top_k': 40,
      'top_p': 0.9,
      'repeat_penalty': 1.1,
      'num_gpu': -1,
    },
  }
  if turn.json_schema is not None:
    request_body['format'] = turn.json_schema

  start = time.perf_counter()
  http_response = httpx.post(_OLLAMA_CHAT_URL, json=request_body, timeout=600.0)
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

  history.append({'role': 'assistant', 'content': content or ''})

  if reasoning:
    tee.write(f'{_section(f"reasoning{turn_label}")}{reasoning}\n')

  display_content = content or '<no response>'
  if turn.json_schema is not None and content:
    with contextlib.suppress(json.JSONDecodeError):
      display_content = json.dumps(json.loads(content), indent=2)
  tee.write(f'{_section(f"response{turn_label}")}{display_content}\n')

  norm_wall = (
    _as_int(data.get('prompt_eval_count')) / _NORM_PREFILL_TPS
    + _as_int(data.get('eval_count')) / _NORM_GEN_TPS
  )
  cumulative_wall = (
    (cumulative_wall_before + elapsed)
    if cumulative_wall_before is not None
    else None
  )
  cumulative_norm_wall = (
    (cumulative_norm_wall_before + norm_wall)
    if cumulative_norm_wall_before is not None
    else None
  )
  tee.write(
    _timing_section(
      data,
      reasoning,
      content,
      elapsed,
      label=f'timing{turn_label}',
      cumulative_wall_seconds=cumulative_wall,
      cumulative_norm_wall_seconds=cumulative_norm_wall,
    )
  )
  return content, _as_int(data.get('eval_count')), elapsed, norm_wall


def parse_args(mode: str) -> ProbeArgs:
  """Parse standard CLI args and return resolved probe arguments."""
  parser = argparse.ArgumentParser(
    description=f'Probe the {mode!r} prompt against a local Ollama model.'
  )
  parser.add_argument('--clue', default=_DEFAULT_CLUE)
  parser.add_argument('--answer', default=_DEFAULT_ANSWER)
  parser.add_argument('--model', default=_DEFAULT_MODEL)
  arguments = parser.parse_args()
  return ProbeArgs(
    clue=arguments.clue,
    answer=arguments.answer,
    model=arguments.model,
  )


def run_messages(
  mode: str,
  turns: Sequence[SystemTurn | SeedTurn | UserTurn],
  args: ProbeArgs,
  temperature: float = 0.2,
) -> str | None:
  """Execute a single conversation and write the log.

  Each UserTurn fires one Ollama request; the assistant response is appended
  to the conversation history before the next turn. SeedTurns inject a
  pre-established exchange into history without firing a request. Per-turn
  timing is logged after each assistant response. When there are multiple
  UserTurns, a cumulative timing section appears at the end.

  Args:
    mode: Short label for the probe (e.g. 'wordplay'). Used as the log
      filename prefix and printed in the run header.
    turns: Ordered sequence of turn values. At least one UserTurn is required.
    args: Resolved CLI arguments from parse_args().
    temperature: Sampling temperature. Gemma4's native default is 1.0;
      thinking models generally need >= 0.6 to avoid repetition loops.

  Returns:
    The last assistant response text, or None if no UserTurn produced output.
  """
  timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
  log_directory = pathlib.Path('logs/probe')
  log_directory.mkdir(parents=True, exist_ok=True)
  log_path = log_directory / f'{mode}_{timestamp}.log'

  user_turn_count = sum(1 for t in turns if isinstance(t, UserTurn))
  is_multi_turn = user_turn_count > 1

  with log_path.open('w') as log_file:
    tee = _Tee(sys.stdout, log_file)
    tee.write(
      f'=== {timestamp}'
      f' mode={mode}'
      f' model={args.model}'
      f' temp={temperature}'
      f' clue={args.clue!r}'
      f' answer={args.answer}'
      f' ===\n'
    )

    history: list[dict[str, object]] = []
    total_gen_tokens = 0
    total_wall_s = 0.0
    total_norm_wall_s = 0.0
    user_turn_index = 0
    last_response: str | None = None

    for turn in turns:
      if isinstance(turn, SystemTurn):
        history.append({'role': 'system', 'content': turn.content})
        tee.write(f'{_section("system")}{turn.content}\n')
      elif isinstance(turn, SeedTurn):
        history.append({'role': 'user', 'content': turn.user_content})
        history.append({'role': 'assistant', 'content': turn.assistant_content})
        tee.write(f'{_section("seed user")}{turn.user_content}\n')
        tee.write(f'{_section("seed assistant")}{turn.assistant_content}\n')
      else:
        user_turn_index += 1
        suffix = f' turn {user_turn_index}' if is_multi_turn else ''
        cum_wall = total_wall_s if is_multi_turn else None
        cum_norm = total_norm_wall_s if is_multi_turn else None
        response, gen_tokens, wall_s, norm_wall_s = _run_user_turn(
          turn, history, args, temperature, tee, suffix, cum_wall, cum_norm
        )
        last_response = response
        total_gen_tokens += gen_tokens
        total_wall_s += wall_s
        total_norm_wall_s += norm_wall_s

    if is_multi_turn:
      tee.write(_section('cumulative timing'))
      tee.write(f'turns:      {user_turn_count}\n')
      tee.write(f'generation: {total_gen_tokens} tok\n')
      tee.write(f'wall:       {total_wall_s:.1f} s\n')
      tee.write(f'norm wall:  {total_norm_wall_s:.1f} s\n')

  print(f'Log: {log_path}', file=sys.stderr)
  return last_response


class Session:
  """A probe run spanning multiple conversations with a shared log and timing.

  Each call to run_conversation() fires one independent LLM conversation.
  All conversations write to the same log file and contribute to combined
  timing totals. Use as a context manager to ensure the log is closed and
  cumulative stats are written even if a conversation raises.

  Usage:
    with harness.Session('quality-multi', args, temperature=1.0) as session:
        response = session.run_conversation([SystemTurn(...), UserTurn(...)])
        session.run_conversation([SystemTurn(...), SeedTurn(..., response), ...])
  """

  def __init__(
    self, mode: str, args: ProbeArgs, temperature: float = 0.2
  ) -> None:
    """Open the log file and write the run header."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    log_directory = pathlib.Path(__file__).parent.parent / 'logs'
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / f'{mode}_{timestamp}.log'
    self._log_file = log_path.open('w')
    self._tee = _Tee(sys.stdout, self._log_file)
    self._args = args
    self._temperature = temperature
    self._conversation_count = 0
    self._total_user_turns = 0
    self._total_gen_tokens = 0
    self._total_wall_s = 0.0
    self._total_norm_wall_s = 0.0
    self._tee.write(
      f'=== {timestamp}'
      f' mode={mode}'
      f' model={args.model}'
      f' temp={temperature}'
      f' clue={args.clue!r}'
      f' answer={args.answer}'
      f' ===\n'
    )
    print(f'Log: {log_path}', file=sys.stderr)

  def run_conversation(
    self,
    turns: Sequence[SystemTurn | SeedTurn | UserTurn],
  ) -> str | None:
    """Run one conversation, log its turns, and return the last response text.

    Conversation history is fresh for each call — conversations are
    independent. SeedTurns inject prior context without firing a request.
    Per-turn cumulative timing reflects the running total across all
    conversations in this session.
    """
    self._conversation_count += 1
    self._tee.write(f'\n=== Conversation {self._conversation_count} ===\n')

    history: list[dict[str, object]] = []
    user_turn_index = 0
    last_response: str | None = None

    for turn in turns:
      if isinstance(turn, SystemTurn):
        history.append({'role': 'system', 'content': turn.content})
        self._tee.write(f'{_section("system")}{turn.content}\n')
      elif isinstance(turn, SeedTurn):
        history.append({'role': 'user', 'content': turn.user_content})
        history.append({'role': 'assistant', 'content': turn.assistant_content})
        self._tee.write(f'{_section("seed user")}{turn.user_content}\n')
        self._tee.write(
          f'{_section("seed assistant")}{turn.assistant_content}\n'
        )
      else:
        user_turn_index += 1
        label = f' turn {user_turn_index}'
        response, gen_tokens, wall_s, norm_wall_s = _run_user_turn(
          turn,
          history,
          self._args,
          self._temperature,
          self._tee,
          label,
          self._total_wall_s,
          self._total_norm_wall_s,
        )
        last_response = response
        self._total_user_turns += 1
        self._total_gen_tokens += gen_tokens
        self._total_wall_s += wall_s
        self._total_norm_wall_s += norm_wall_s

    return last_response

  def close(self) -> None:
    """Write combined timing stats and close the log."""
    self._tee.write(_section('cumulative timing'))
    self._tee.write(f'conversations: {self._conversation_count}\n')
    self._tee.write(f'turns:         {self._total_user_turns}\n')
    self._tee.write(f'generation:    {self._total_gen_tokens} tok\n')
    self._tee.write(f'wall:          {self._total_wall_s:.1f} s\n')
    self._tee.write(f'norm wall:     {self._total_norm_wall_s:.1f} s\n')
    self._log_file.close()

  def __enter__(self) -> 'Session':
    """Return self for use as a context manager."""
    return self

  def __exit__(self, *_: object) -> None:
    """Close the session on exit, writing cumulative stats."""
    self.close()


def run(
  mode: str,
  system_prompt: str,
  user_prompt: str,
  json_schema: Mapping[str, object] | None = None,
  temperature: float = 0.2,
) -> None:
  """Parse standard CLI args, fire the probe request, and write the log.

  Convenience wrapper around parse_args() + run_messages() for single-turn
  probes. Multi-turn probes should call those functions directly.

  Args:
    mode: Short label for the probe (e.g. 'wordplay'). Used as the log
      filename prefix and printed in the run header.
    system_prompt: System prompt text.
    user_prompt: Text appended after "Clue: X\\nAnswer: Y\\n\\n" in the
      user turn.
    json_schema: Optional JSON Schema dict constraining the model reply.
      Passed as the native Ollama `format` key. When set, the response is
      pretty-printed as JSON in the log.
    temperature: Sampling temperature. Gemma4's native default is 1.0;
      thinking models generally need >= 0.6 to avoid repetition loops.
  """
  args = parse_args(mode)
  turns: list[SystemTurn | UserTurn] = [
    SystemTurn(system_prompt),
    UserTurn(
      f'Clue: {args.clue}\nAnswer: {args.answer}\n\n{user_prompt}',
      json_schema=json_schema,
    ),
  ]
  run_messages(mode, turns, args, temperature=temperature)
