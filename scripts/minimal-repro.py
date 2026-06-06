import httpx

SCHEMA = {
  'type': 'object',
  'properties': {
    'animal': {'type': 'string'},
  },
  'required': ['animal'],
  'additionalProperties': False,
}

PROMPT = 'Say hi'

MODELS = [
  'qwen3.5:4b',
  'qwen3.5:4b-mlx',
  # Uncomment if you want a second model family:
  'gemma4:31b',
  'gemma4:31b-mlx',
]


def run_model(model: str) -> None:
  response = httpx.post(
    'http://localhost:11434/api/chat',
    json={
      'model': model,
      'messages': [
        {
          'role': 'user',
          'content': PROMPT,
        }
      ],
      'stream': False,
      'format': SCHEMA,
    },
    timeout=900,
  )

  response.raise_for_status()
  payload = response.json()

  print(f'\nModel: {model}')
  print(f'Output: {payload["message"]["content"]}')


def main() -> None:
  version = httpx.get('http://localhost:11434/api/version').json()
  print(f'Ollama version: {version["version"]}')
  print(f'\nPrompt: "{PROMPT}"')
  print(f'\nSchema:\n{SCHEMA}')

  for model in MODELS:
    run_model(model)


if __name__ == '__main__':
  main()
