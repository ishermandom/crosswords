import collections.abc

import httpx
import openai
from openai.types.shared_params import ResponseFormatJSONSchema

original_send: collections.abc.Callable[..., httpx.Response] = httpx.Client.send


def debug_send(
  self: httpx.Client,
  request: httpx.Request,
  *args: object,
  **kwargs: object,
) -> httpx.Response:
  print('\n=== REQUEST BODY ===')
  print(request.content.decode())
  return original_send(self, request, *args, **kwargs)


client = openai.OpenAI(
  base_url='http://localhost:11434/v1',
  api_key='ollama',
)

setattr(httpx.Client, 'send', debug_send)

schema = ResponseFormatJSONSchema(
  type='json_schema',
  json_schema={
    'name': 'test',
    'strict': True,
    'schema': {
      'type': 'object',
      'properties': {
        'animal': {'type': 'string'},
      },
      'required': ['animal'],
      'additionalProperties': False,
    },
  },
)

# response = client.chat.completions.create(
#     model="gemma4:31b-mlx",
#     messages=[
#         {
#             "role": "user",
#             "content": "Return the animal cat.",
#         }
#     ],
#     extra_body={
#         "format": {
#             "type": "object",
#             "properties": {
#                 "animal": {"type": "string"}
#             },
#             "required": ["animal"],
#             "additionalProperties": False,
#         }
#     },
#     temperature=0,
#     reasoning_effort='none',
# )

print(httpx.get('http://localhost:11434/api/version').json())
response = httpx.post(
  'http://localhost:11434/api/chat',
  json={
    'model': 'qwen3.5:4b-mlx',
    'messages': [
      {
        'role': 'user',
        'content': 'Say hi',
      }
    ],
    'stream': False,
    'format': {
      'type': 'object',
      'properties': {'animal': {'type': 'string'}},
      'required': ['animal'],
      'additionalProperties': False,
    },
    # "think": False,
  },
  timeout=300,
)
print(response.json())
raise SystemExit(0)

print('=== RAW RESPONSE ===')
print(response.model_dump_json(indent=2))

print('\n=== CONTENT ===')
print(response.choices[0].message.content)
