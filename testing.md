# Testing LLM-Dependent Code Without a Live Model

_Companion to `plan.md`. Covers the approach for unit-testing `generate_clue`
and similar pipeline code in isolation from Ollama._

---

## The problem

`generate_clue` calls `client.chat()` several times — brainstorm, extract,
validate — and interprets the text replies to assemble a `ClueResult`. Testing
the pipeline logic (call sequence, JSON parsing, fallback behaviour) requires
controlling those replies precisely. Hitting a real Ollama server is slow,
non-deterministic, and requires the server to be running.

## The pattern: protocol-based fake

`load_words(stream: TextIO)` works because it's typed against the abstract
protocol, not `open()`. Tests pass `io.StringIO` — same interface, no
filesystem. The same move applies here.

`generate_clue` currently accepts `client: OllamaClient` (the concrete class).
Loosening the type to a `ChatClient` protocol lets tests pass a fake that
returns scripted replies — same interface, no HTTP.

## Protocol definition

Add to `clue_gen/client.py`:

```python
from typing import Protocol

class ChatClient(Protocol):
    def chat(self, messages: tuple[Message, ...]) -> ChatResult: ...
```

Change `generate_clue`'s signature to:

```python
def generate_clue(word: str, difficulty: Difficulty, client: ChatClient) -> ClueResult:
```

`OllamaClient` satisfies the protocol structurally — no changes to the
production class are needed.

## FakeChatClient

Lives in `clue_gen/tests/fake_client.py`. It holds a list of reply strings
consumed in order, and records every `messages` argument so tests can assert
on call sequence and content.

```python
from dataclasses import dataclass, field
from clue_gen.client import ChatResult, Message

@dataclass
class FakeChatClient:
    """Scripted stand-in for any ChatClient.

    replies is consumed front-to-back; each call pops the next reply and
    records the messages argument in calls. Raises AssertionError if called
    more times than scripted.
    """
    replies: list[str]
    calls: list[tuple[Message, ...]] = field(default_factory=list)

    def chat(self, messages: tuple[Message, ...]) -> ChatResult:
        self.calls.append(messages)
        if not self.replies:
            raise AssertionError(
                f'FakeChatClient exhausted after {len(self.calls)} call(s)'
            )
        reply = self.replies.pop(0)
        updated: tuple[Message, ...] = messages + (
            {'role': 'assistant', 'content': reply},
        )
        return ChatResult(reply=reply, messages=updated)
```

## Usage

A complete validation-passes test, showing how call content and result
assembly are verified together:

```python
from clue_gen.tests.fake_client import FakeChatClient
from clue_gen.generator import generate_clue
from clue_gen.prompt import Difficulty

def test_uses_validator_clue_field():
    fake = FakeChatClient(replies=[
        # call 1: brainstorm reply (content checked but not parsed)
        'Here are some candidate clues...',
        # call 2: extract turn — model returns a JSON list
        '["Raw candidate clue"]',
        # call 3: validation — model accepts and lightly edits the clue
        '{"valid": true, "clue": "Edited clue", "answer": "ALPHA"}',
    ])
    result = generate_clue('ALPHA', Difficulty.MON, fake)
    assert result.clues == ['Edited clue']   # validator's rewrite, not raw
    assert len(fake.calls) == 3
    # Brainstorm message should include the answer word
    assert 'ALPHA' in fake.calls[0][-1]['content']
    # Validation message should NOT include the answer word (blind solver)
    assert 'ALPHA' not in fake.calls[2][0]['content']
```

For the fallback path (all validation fails), script the validation reply
with `"valid": false` — no exception injection needed, because
`_extract_json_object` raises `GenerationError` on malformed JSON, and the
loop catches it:

```python
def test_falls_back_to_first_candidate_when_validation_fails():
    fake = FakeChatClient(replies=[
        'Brainstorm reply',
        '["Candidate A", "Candidate B"]',
        '{"valid": false, "issues": ["ambiguous"]}',  # candidate A rejected
        '{"valid": false, "issues": ["too hard"]}',   # candidate B rejected
    ])
    result = generate_clue('BRAVO', Difficulty.MON, fake)
    assert result.clues == ['Candidate A']
```

## Limitations and TODOs

The simple fake covers the primary paths. Two scenarios it cannot reach
without extension:

- **Exception injection**: `generate_clue` does not catch `GenerationError`
  from the brainstorm or extract calls — those propagate to the caller. To
  test that propagation, a call would need to raise rather than return. A
  `raises_on: dict[int, Exception]` parameter on `FakeChatClient` would
  cover this without restructuring the fake.

- **`APIConnectionError` propagation**: raised by `OllamaClient` when Ollama
  is unreachable; caught in the CLI entry point. The fake has no concept of
  a connection, so testing this path requires either exception injection or
  a real Ollama integration test.
