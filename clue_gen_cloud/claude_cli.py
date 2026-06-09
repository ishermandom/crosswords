# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT
"""Subprocess wrapper around `claude -p` for fresh-context LLM calls.

Each call is a brand-new non-interactive CLI invocation, so every batch
gets a clean context. The wrapper enforces a timeout, retries once on
transport-level failure (nonzero exit, empty or invalid output), and
surfaces plan rate limits as a distinct exception so the pipeline can
stop gracefully and rely on resumability.
"""

import os
import re
import subprocess
from collections.abc import Callable, Mapping
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
  ) -> str:
    """Run one prompt to completion, retrying once on failure.

    is_valid lets callers treat content-level garbage (e.g. zero
    parseable JSON lines) as a transport failure worth one retry.
    Raises RateLimited or TransportFailure.
    """
    command = [self.executable, '-p']
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
      if not is_valid(result.stdout):
        failure_details.append(
          f'attempt {attempt}: invalid output:'
          f' {result.stdout.strip()[:OUTPUT_EXCERPT_LENGTH]}'
        )
        continue
      return result.stdout

    raise TransportFailure('; '.join(failure_details))
