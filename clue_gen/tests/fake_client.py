# Copyright 2026 Ilya Sherman (ishermandom@)
# SPDX-License-Identifier: MIT

"""Scripted stand-in for ChatClient used in unit tests."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from clue_gen.client import ChatResult, Message


@dataclass
class FakeChatClient:
  """Scripted stand-in for any ChatClient.

  Always use as a context manager — `__exit__` asserts that all scripted
  replies were consumed, catching tests that script more calls than the code
  actually makes.

  Replies are consumed front-to-back; each call pops the next reply and
  appends the messages argument to calls. Raises AssertionError if called
  more times than scripted.

  Typical usage:

    with FakeChatClient(['brainstorm', '["Clue"]', '{"valid": true, ...}']) as fake:
        result = generate_clue('WORD', Difficulty.MON, fake)
    assert result.clues == ['Clue']
  """

  replies: list[str]
  calls: list[Sequence[Message]] = field(default_factory=list)

  def __enter__(self) -> 'FakeChatClient':
    """Enables use in a `with` block; `__exit__` validates reply exhaustion."""
    return self

  def __exit__(self, exception_type: object, exception_value: object, traceback: object) -> None:
    """Assert all scripted replies were consumed, unless an exception is propagating."""
    # Skip the check when a test is already failing to avoid masking the
    # real error with a confusing secondary assertion.
    if not exception_type and self.replies:
      raise AssertionError(
        f'FakeChatClient has {len(self.replies)} unconsumed reply(ies)'
      )

  def chat(self, messages: Sequence[Message]) -> ChatResult:
    """Return the next scripted reply, recording the messages argument."""
    self.calls.append(messages)
    if not self.replies:
      raise AssertionError(
        f'FakeChatClient exhausted after {len(self.calls)} call(s)'
      )
    reply = self.replies.pop(0)
    return ChatResult(
      reply=reply,
      messages=[*messages, {'role': 'assistant', 'content': reply}],
    )
