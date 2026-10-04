"""Inspect configured provider catalogs without printing credentials."""
import httpx
from dehalu.core.settings import settings
specs = [
 ('gemini', 'https://generativelanguage.googleapis.com/v1beta/models', {'x-goog-api-key': settings.gemini_api_key or ''}),
 ('groq', 'https://api.groq.com/openai/v1/models', {'Authorization': f'Bearer {settings.groq_api_key or ""}'}),
 ('mistral', 'https://api.mistral.ai/v1/models', {'Authorization': f'Bearer {settings.mistral_api_key or ""}'}),
]
for name, url, headers in specs:
    try:
        response = httpx.get(url, headers=headers, timeout=15)
        print(name, response.status_code)
        if response.is_success:
            data = response.json()
            ids = [item.get('id', item.get('name')) for item in data.get('data', data.get('models', []))]
            print(ids[:40] if name == 'groq' else [model for model in ids if any(part in model for part in ('2.5-flash', 'small', 'medium', 'large'))][:25])
    except httpx.HTTPError as exc: print(name, type(exc).__name__)
