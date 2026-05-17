# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Tests for clue_gen.cli._generate_clues error handling."""

from collections.abc import Sequence
from unittest.mock import MagicMock

import openai
import pytest

from clue_gen.cli import _generate_clues
from clue_gen.client import ChatResult, Message
from clue_gen.prompt import Difficulty
from clue_gen.tests.fake_client import FakeChatClient


class _ConnectionErrorClient:
  """Stub ChatClient that always raises APIConnectionError on chat()."""

  def chat(self, messages: Sequence[Message]) -> ChatResult:
    raise openai.APIConnectionError(message='connection refused', request=MagicMock())


def test_exits_on_api_connection_error():
  with pytest.raises(SystemExit) as exception_info:
    _generate_clues(['ALPHA'], Difficulty.MON, _ConnectionErrorClient())
  assert exception_info.value.code == 1


def test_exits_on_generation_error():
  # An empty candidate list causes generate_clue to raise GenerationError,
  # which _generate_clues catches and exits on.
  with FakeChatClient(['brainstorm reply', '[]']) as fake:
    with pytest.raises(SystemExit) as exception_info:
      _generate_clues(['ALPHA'], Difficulty.MON, fake)
  assert exception_info.value.code == 1
