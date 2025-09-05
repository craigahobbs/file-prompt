# Licensed under the MIT License
# https://github.com/craigahobbs/ctxkit/blob/main/LICENSE

"""
Grok API utilities
"""

import itertools
import json
import os

import urllib3


# Initialize urllib3 PoolManager
POOL_MANAGER = urllib3.PoolManager()

# Load environment variables
XAI_API_KEY = os.getenv('XAI_API_KEY')

# API endpoint
XAI_URL = 'https://api.x.ai/v1/chat/completions'


def grok_chat(model, prompt, temperature=1.0):
    # Make POST request with streaming
    response = POOL_MANAGER.request(
        method='POST',
        url=XAI_URL,
        headers={
            'Authorization': f'Bearer {XAI_API_KEY}',
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream'
        },
        json={
            'model': model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': temperature,
            'stream': True
        },
        preload_content=False,
        retries=0
    )
    try:
        if response.status != 200:
            raise urllib3.exceptions.HTTPError(f'POST {model} failed with status {response.status}')

        # Process the streaming response
        line_prefix = None
        for line in itertools.chain.from_iterable(line.decode('utf-8').splitlines() for line in response.read_chunked()):
            # Combine with previous partial line
            if line_prefix:
                line = line_prefix + line
                line_prefix = None

            # Parse the data chunk
            if not line.startswith('data: '):
                continue
            data = line[6:]
            if data == '[DONE]':
                break
            try:
                chunk = json.loads(data)
            except:
                line_prefix = line
                continue

            # Yield the chunk content
            for choice in chunk['choices']:
                content = choice['delta'].get('content')
                if content:
                    yield content

    finally:
        response.close()
