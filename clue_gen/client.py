# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Ollama client wrapper using the OpenAI-compatible HTTP API."""

import enum
from dataclasses import dataclass

import openai
from openai.types.chat import ChatCompletionMessageParam

# Ollama exposes an OpenAI-compatible endpoint at this address.
_OLLAMA_BASE_URL = 'http://localhost:11434/v1'

# Alias so callers don't need to import from openai.types.chat directly.
Message = ChatCompletionMessageParam


class GenerationError(Exception):
  """Raised when the model returns output that cannot be used as a clue."""


class Model(enum.StrEnum):
  """Candidate models available in the local Ollama install."""

  GEMMA4_31B = 'gemma4:31b'  # dense model; slightly larger
  GEMMA4_26B = 'gemma4:26b'  # mixture-of-experts; more likely to fit in RAM
  QWEN25_0B5 = 'qwen2.5:0.5b'  # 398 MB; fast smoke-test model
  QWEN3_0B6 = 'qwen3:0.6b'  # fast smoke-test; low quality
  QWEN3_1B7 = 'qwen3:1.7b'  # fast smoke-test; low quality
  QWEN3_4B = 'qwen3:4b'  # smoke-test; balanced quality vs. speed
  QWEN3_8B = 'qwen3:8b'  # smoke-test; balanced quality vs. speed


@dataclass(frozen=True)
class ChatResult:
  """Return value of OllamaClient.chat."""

  reply: str
  messages: tuple[Message, ...]


class OllamaClient:
  """HTTP client for sending prompts to a locally running Ollama server."""

  def __init__(
    self,
    model: Model = Model.GEMMA4_26B,
    base_url: str = _OLLAMA_BASE_URL,
  ) -> None:
    # api_key must be non-empty to satisfy the openai client's validation,
    # but Ollama ignores its value.
    self._model = model
    self._client = openai.OpenAI(base_url=base_url, api_key='ollama')

  def chat(self, messages: tuple[Message, ...]) -> ChatResult:
    """Send a conversation and return the reply and updated messages tuple.

    The returned messages tuple is the input extended with the assistant's
    reply, ready for the next turn if continuing the conversation.

    Raises openai.APIConnectionError if the Ollama server is unreachable.
    Raises ValueError if the model returns no text content.
    """
    response = self._client.chat.completions.create(
      model=self._model,
      messages=messages,
    )
    content = response.choices[0].message.content if response.choices else None
    if not content:
      last = repr(messages[-1]) if messages else '<no messages>'
      raise GenerationError(
        f'Model {self._model!r} returned no text content. Last message: {last}'
      )
    updated: tuple[Message, ...] = messages + (
      {'role': 'assistant', 'content': content},
    )
    return ChatResult(reply=content, messages=updated)
