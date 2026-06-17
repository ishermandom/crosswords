# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Ollama client wrapper using the OpenAI-compatible HTTP API."""

import dataclasses
import enum
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

import openai
from openai.types.chat import ChatCompletionMessageParam
from openai.types.shared_params import ResponseFormatJSONSchema

_log = logging.getLogger(__name__)


def _section(label: str) -> str:
  """Format a dashes section header for log output (60 chars total)."""
  return f'\n--- {label} {"-" * max(0, 55 - len(label))}'


def _format_messages(
  messages: Sequence[Message], *, stub_assistant: bool
) -> str:
  """Format messages as labeled plain-text blocks for log output.

  When stub_assistant is True, assistant messages are replaced with a
  character-count stub — used for incremental prompt logs where the
  assistant's reply was already written to the log by the caller.
  """
  blocks = []
  for message in messages:
    if not isinstance(message, dict):
      # Unexpected message type — log unformatted so no output is lost.
      blocks.append(str(message))
      continue
    role = str(message.get('role', 'unknown'))
    content = str(message.get('content') or '')
    if stub_assistant and role == 'assistant':
      blocks.append(f'[{role}]\n<{len(content)} chars — see above>')
    else:
      blocks.append(f'[{role}]\n{content}')
  return '\n\n'.join(blocks)


# Ollama exposes an OpenAI-compatible endpoint at this address.
_OLLAMA_BASE_URL = 'http://localhost:11434/v1'

# Alias so callers don't need to import from openai.types.chat directly.
Message = ChatCompletionMessageParam


class GenerationError(Exception):
  """Raised when the model returns output that cannot be used as a clue."""


@dataclass(frozen=True)
class ChatResult:
  """Return value of a ChatClient.chat call."""

  reply: str
  messages: Sequence[Message]


class ChatClient(Protocol):
  """Structural protocol for any chat model client."""

  def chat(
    self,
    messages: Sequence[Message],
    response_format: ResponseFormatJSONSchema | None = None,
  ) -> ChatResult: ...


@dataclass(frozen=True)
class ModelOptions:
  """Ollama generation parameters.

  Top-level OpenAI params (temperature, max_tokens, frequency_penalty) are
  passed directly to chat.completions.create(). Ollama-specific params
  (num_ctx, keep_alive, top_k, top_p, repeat_penalty, num_gpu) go inside
  extra_body['options']. think is a top-level extra_body field that disables
  chain-of-thought on Qwen3/Qwen3.5 reasoning variants.
  """

  # --- OpenAI top-level params ---
  # 0.7 for creative brainstorm generation; Phase 3 may lower this to
  # 0.1–0.2 for the deterministic validation call.
  temperature: float = 0.7
  # None = uncapped. Set low during debugging to bound output length.
  max_tokens: int | None = None
  # Mild penalty reduces rambling without affecting clue quality much.
  frequency_penalty: float = 0.0

  # --- Ollama options ---
  # Ollama's built-in default is 2048 and it truncates silently — set
  # explicitly so long brainstorm conversations don't lose early context.
  num_ctx: int = 8192
  # How long Ollama keeps the model loaded after the last request.
  keep_alive: str = '5m'
  # min_p=0.05 was the original sampler here; it reportedly outperforms
  # top_p for local models at higher temperatures. Switched to top_k/top_p
  # to match Ollama's conventional defaults — revisit if clue quality suffers.
  top_k: int = 40
  top_p: float = 0.9
  # Reduces token repetition within a response (1.0 = off).
  repeat_penalty: float = 1.0
  # -1 = use all available GPU layers.
  num_gpu: int = -1

  # --- Thinking mode ---
  # None omits the field, letting each model use its own default (thinking
  # enabled for gemma4 and Qwen3/Qwen3.5). 'none' disables chain-of-thought;
  # other values: 'low', 'medium', 'high'.
  # WARNING: 'none' breaks response_format schema enforcement on qwen3.5 —
  # Ollama defers the grammar mask until the end-of-thinking token, which never
  # arrives. gemma4 is unaffected. https://github.com/ollama/ollama/issues/14645
  reasoning_effort: Literal['none', 'low', 'medium', 'high'] | None = None


# Tuned for fast iteration: small context window, low temperature, model kept
# resident for 30 minutes between calls.
DEBUG_OPTIONS = ModelOptions(
  temperature=0.2,
  # TODO: set an explicit cap once typical completion sizes are known from logs.
  max_tokens=None,
  frequency_penalty=0.2,
  num_ctx=2048,
  keep_alive='30m',
  top_k=40,
  top_p=0.9,
  repeat_penalty=1.1,
  num_gpu=-1,
  reasoning_effort=None,
)


class Model(enum.StrEnum):
  """Candidate models available in the local Ollama install."""

  GEMMA4_31B = 'gemma4:31b'  # dense model; slightly larger
  GEMMA4_26B = 'gemma4:26b'  # mixture-of-experts; more likely to fit in RAM
  GEMMA4_26B_MLX = 'gemma4:26b-mlx'  # MLX-optimised build for Apple Silicon
  QWEN25_0B5 = 'qwen2.5:0.5b'  # 398 MB; fast smoke-test model
  QWEN3_0B6 = 'qwen3:0.6b'  # fast smoke-test; low quality
  QWEN3_1B7 = 'qwen3:1.7b'  # fast smoke-test; low quality
  QWEN3_4B = 'qwen3:4b'  # smoke-test; balanced quality vs. speed
  QWEN3_8B = 'qwen3:8b'  # smoke-test; balanced quality vs. speed
  QWEN35_0B8 = 'qwen3.5:0.8b'  # fast smoke-test; low quality
  QWEN35_2B = (
    'qwen3.5:2b'  # default smoke-test model; good quality/speed tradeoff
  )
  QWEN35_4B = 'qwen3.5:4b'
  QWEN35_9B = 'qwen3.5:9b'
  QWEN35_27B = 'qwen3.5:27b'
  QWEN35_35B_A3B = 'qwen3.5:35b-a3b'
  QWEN36_27B_MLX = 'qwen3.6:27b-mlx'  # MLX-optimised build for Apple Silicon
  QWEN36_35B_MLX = 'qwen3.6:35b-mlx'  # MLX-optimised build for Apple Silicon


class OllamaClient:
  """HTTP client for sending prompts to a locally running Ollama server."""

  def __init__(
    self,
    model: Model = Model.GEMMA4_26B,
    base_url: str = _OLLAMA_BASE_URL,
    # TODO: switch to ModelOptions() once prompt tuning is complete.
    options: ModelOptions = DEBUG_OPTIONS,
  ) -> None:
    # api_key must be non-empty to satisfy the openai client's validation,
    # but Ollama ignores its value.
    self._model = model
    # qwen3.5 breaks schema enforcement with reasoning_effort='none' — upgrade
    # to 'low' so the grammar mask fires. https://github.com/ollama/ollama/issues/14645
    if options.reasoning_effort == 'none' and str(model).startswith('qwen3.5:'):
      options = dataclasses.replace(options, reasoning_effort='low')
    self._options = options
    self._client = openai.OpenAI(base_url=base_url, api_key='ollama')
    # Tracks messages logged so far this session to avoid duplicating context
    # that already appears earlier in the log file.
    self._logged_messages: list[Message] = []

  def chat(
    self,
    messages: Sequence[Message],
    response_format: ResponseFormatJSONSchema | None = None,
  ) -> ChatResult:
    """Send a conversation and return the reply and updated messages list.

    The returned messages list is the input extended with the assistant's
    reply, ready for the next turn if continuing the conversation.

    response_format constrains the reply to the given JSON schema.

    Raises openai.APIConnectionError if the Ollama server is unreachable.
    Raises GenerationError if the model returns no text content.
    """
    # Find the longest prefix already logged, then log only the new tail.
    prefix_len = 0
    for message, logged in zip(messages, self._logged_messages):
      if message == logged:
        prefix_len += 1
      else:
        break
    new_messages = list(messages)[prefix_len:]
    stub = prefix_len > 0
    formatted = _format_messages(new_messages, stub_assistant=stub)
    if prefix_len == 0:
      label = f'prompt ({len(messages)} messages)'
    else:
      label = f'prompt (+{len(new_messages)} new, {len(messages)} total)'
    _log.debug(f'{_section(label)}\n\n{formatted}\n')
    self._logged_messages = list(messages)
    t0 = time.perf_counter()
    extra_body: dict[str, object] = {
      'options': {
        'num_ctx': self._options.num_ctx,
        'keep_alive': self._options.keep_alive,
        'top_k': self._options.top_k,
        'top_p': self._options.top_p,
        'repeat_penalty': self._options.repeat_penalty,
        'num_gpu': self._options.num_gpu,
      },
    }
    response = self._client.chat.completions.create(
      model=self._model,
      messages=messages,
      temperature=self._options.temperature,
      frequency_penalty=self._options.frequency_penalty,
      reasoning_effort=self._options.reasoning_effort or openai.omit,
      max_tokens=self._options.max_tokens,
      response_format=response_format or openai.omit,
      extra_body=extra_body,
    )
    elapsed = time.perf_counter() - t0

    usage = response.usage
    if usage:
      prompt_tok = usage.prompt_tokens
      completion_tok = usage.completion_tokens
      tok_per_sec = completion_tok / elapsed if elapsed > 0 else 0
      _log.debug(
        f'chat {elapsed:.1f}s'
        f' | prompt={prompt_tok} completion={completion_tok}'
        f' | {tok_per_sec:.1f} tok/s'
      )
      if (
        self._options.max_tokens is not None
        and completion_tok >= self._options.max_tokens
      ):
        _log.warning(
          f'completion hit max_tokens={self._options.max_tokens}'
          ' — output may be truncated'
        )
    else:
      _log.debug(f'chat {elapsed:.1f}s (no usage data)')

    content = response.choices[0].message.content if response.choices else None
    reasoning = (
      (response.choices[0].message.model_extra or {}).get('reasoning')
      if response.choices
      else None
    )
    if reasoning:
      # Token count is estimated (~4 chars/token); Ollama does not report
      # reasoning and content tokens separately in the usage object.
      estimated_tokens = len(reasoning) // 4
      _log.debug(
        f'{_section(f"reasoning (~{estimated_tokens} tokens)")}'
        f'\n\n{reasoning}\n'
      )
    if not content:
      last = repr(messages[-1]) if messages else '<no messages>'
      raise GenerationError(
        f'Model {self._model!r} returned no text content. Last message: {last}'
      )
    return ChatResult(
      reply=content,
      messages=[*messages, {'role': 'assistant', 'content': content}],
    )
