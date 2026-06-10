# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Subprocess wrapper around `claude -p` for fresh-context LLM calls.

Each call is a brand-new non-interactive CLI invocation, so every batch
gets a clean context. The wrapper enforces a timeout, retries once on
transport-level failure (nonzero exit, empty or invalid output), and
surfaces plan rate limits as a distinct exception so the pipeline can
stop gracefully and rely on resumability.

Calls use `--output-format json` so each response carries token usage
(including prompt-cache reads and writes) alongside the model text —
the raw data for deciding whether prompt caching can cut quota cost.
"""

import json
import os
import re
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

# Phrases the CLI emits when the plan's usage window is exhausted.
RATE_LIMIT_PATTERN = re.compile(
  r'usage limit|rate limit|limit reached|out of extra usage', re.I
)

# Long-lived OAuth token minted via `claude setup-token`, used because
# su-based claude-sandbox sessions cannot unlock the login keychain that
# the CLI reads credentials from by default.
OAUTH_TOKEN_PATH = Path.home() / '.claude' / 'oauth-token'

OUTPUT_EXCERPT_LENGTH = 400


class TransportFailure(RuntimeError):
  """The CLI call failed twice at the transport level."""


class RateLimited(RuntimeError):
  """The plan's usage limit stopped the call; resume in a later session."""


class MalformedEnvelope(RuntimeError):
  """The CLI's stdout was not a well-formed JSON result envelope."""


@dataclass(frozen=True)
class CallUsage:
  """Token counts the CLI reports for one call (API usage field names)."""

  input_tokens: int
  output_tokens: int
  cache_read_input_tokens: int
  cache_creation_input_tokens: int


@dataclass(frozen=True)
class CliResponse:
  """One parsed `--output-format json` envelope from the CLI."""

  text: str
  is_error: bool
  usage: CallUsage | None
  session_id: str | None
  cost_usd: float | None


def _parse_usage(value: object) -> CallUsage | None:
  """Token counts from the envelope's usage object; None if unusable."""
  if not isinstance(value, Mapping):
    return None

  def count_of(key: str) -> int:
    field = value.get(key, 0)
    return field if isinstance(field, int) else 0

  return CallUsage(
    input_tokens=count_of('input_tokens'),
    output_tokens=count_of('output_tokens'),
    cache_read_input_tokens=count_of('cache_read_input_tokens'),
    cache_creation_input_tokens=count_of('cache_creation_input_tokens'),
  )


def parse_response_envelope(stdout: str) -> CliResponse:
  """Parse the JSON envelope `claude -p --output-format json` prints.

  Usage metadata is best-effort (None when absent or unusable), but the
  result text is load-bearing: raises MalformedEnvelope when stdout is
  not a JSON object carrying one.
  """
  excerpt = stdout.strip()[:OUTPUT_EXCERPT_LENGTH]
  try:
    envelope = json.loads(stdout)
  except json.JSONDecodeError as error:
    raise MalformedEnvelope(
      f'CLI output is not JSON ({error}): {excerpt}'
    ) from error
  if not isinstance(envelope, dict):
    raise MalformedEnvelope(f'CLI output is not a JSON object: {excerpt}')

  text = envelope.get('result')
  if not isinstance(text, str):
    raise MalformedEnvelope(f'CLI envelope has no result text: {excerpt}')

  session_id = envelope.get('session_id')
  cost = envelope.get('total_cost_usd')
  return CliResponse(
    text=text,
    is_error=bool(envelope.get('is_error')),
    usage=_parse_usage(envelope.get('usage')),
    session_id=session_id if isinstance(session_id, str) else None,
    cost_usd=float(cost) if isinstance(cost, (int, float)) else None,
  )


def describe_usage(label: str, response: CliResponse) -> str:
  """One log line summarizing a call's token usage."""
  usage = response.usage
  if usage is None:
    return f'[usage] {label}: unavailable'
  cost = (
    f' cost=${response.cost_usd:.4f}' if response.cost_usd is not None else ''
  )
  return (
    f'[usage] {label}: input={usage.input_tokens}'
    f' output={usage.output_tokens}'
    f' cache_read={usage.cache_read_input_tokens}'
    f' cache_write={usage.cache_creation_input_tokens}{cost}'
  )


def _subprocess_environment() -> dict[str, str]:
  """The child environment, with the OAuth token injected if present."""
  environment = dict(os.environ)
  if OAUTH_TOKEN_PATH.exists():
    token = OAUTH_TOKEN_PATH.read_text().strip()
    if token:
      environment['CLAUDE_CODE_OAUTH_TOKEN'] = token
  return environment


class ClaudeCli:
  """Runs prompts through the `claude` CLI in non-interactive mode."""

  def __init__(
    self,
    timeout_seconds: float,
    model: str | None = None,
    executable: str = 'claude',
    environment: Mapping[str, str] | None = None,
  ) -> None:
    """Configure the wrapper; environment overrides are for tests.

    model is passed through as `claude --model`; None uses the CLI
    account's configured default.
    """
    self.timeout_seconds = timeout_seconds
    self.model = model
    self.executable = executable
    self.environment = (
      dict(environment)
      if environment is not None
      else _subprocess_environment()
    )

  def complete(
    self,
    prompt: str,
    is_valid: Callable[[str], bool] = lambda output: True,
  ) -> CliResponse:
    """Run one prompt to completion, retrying once on failure.

    Returns the parsed response envelope: model text plus usage
    metadata. is_valid receives the response text and lets callers
    treat content-level garbage (e.g. zero parseable JSON lines) as a
    transport failure worth one retry. Raises RateLimited or
    TransportFailure.
    """
    command = [self.executable, '-p', '--output-format', 'json']
    if self.model:
      command += ['--model', self.model]

    failure_details = []
    for attempt in (1, 2):
      try:
        result = subprocess.run(
          command,
          input=prompt,
          capture_output=True,
          text=True,
          timeout=self.timeout_seconds,
          env=self.environment,
        )
      except subprocess.TimeoutExpired:
        failure_details.append(
          f'attempt {attempt}: timed out after {self.timeout_seconds}s'
        )
        continue

      combined = result.stdout + '\n' + result.stderr
      if RATE_LIMIT_PATTERN.search(combined):
        raise RateLimited(combined.strip()[:OUTPUT_EXCERPT_LENGTH])

      if result.returncode != 0:
        failure_details.append(
          f'attempt {attempt}: exit {result.returncode}:'
          f' {result.stderr.strip()[:OUTPUT_EXCERPT_LENGTH]}'
        )
        continue
      if not result.stdout.strip():
        failure_details.append(f'attempt {attempt}: empty output')
        continue
      try:
        response = parse_response_envelope(result.stdout)
      except MalformedEnvelope as error:
        failure_details.append(f'attempt {attempt}: {error}')
        continue
      if response.is_error:
        failure_details.append(
          f'attempt {attempt}: CLI reported an error:'
          f' {response.text.strip()[:OUTPUT_EXCERPT_LENGTH]}'
        )
        continue
      if not is_valid(response.text):
        failure_details.append(
          f'attempt {attempt}: invalid output:'
          f' {response.text.strip()[:OUTPUT_EXCERPT_LENGTH]}'
        )
        continue
      return response

    raise TransportFailure('; '.join(failure_details))
