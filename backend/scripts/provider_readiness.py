"""Check active judge catalogs; --live also validates small real judge calls."""
import argparse

import httpx

from dehalu.core.judges import judge_specs
from dehalu.core.settings import settings
from dehalu.providers.llm import JudgePool, build_judge_prompt

CATALOG_URLS = {
    'gemini': 'https://generativelanguage.googleapis.com/v1beta/models',
    'groq': 'https://api.groq.com/openai/v1/models',
    'mistral': 'https://api.mistral.ai/v1/models',
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Consume API quota to validate all three judge roles')
    args = parser.parse_args()
    if args.live and settings.allow_fake_llm:
        parser.error('--live requires DEHALU_ALLOW_FAKE_LLM=false')
    specs = judge_specs(settings)
    catalogs = {}
    for spec in specs:
        if spec.provider in catalogs:
            continue
        if not spec.key:
            catalogs[spec.provider] = 'Credentials missing'
            continue
        headers = {'x-goog-api-key': spec.key} if spec.provider == 'gemini' else {'Authorization': f'Bearer {spec.key}'}
        try:
            response = httpx.get(CATALOG_URLS[spec.provider], headers=headers, timeout=15)
            if response.is_success:
                data = response.json()
                ids = {item.get('id', item.get('name', '')).removeprefix('models/')
                       for item in data.get('data', data.get('models', []))}
                catalogs[spec.provider] = f'HTTP {response.status_code}; model {"listed" if spec.model in ids else "not listed"}'
            else:
                catalogs[spec.provider] = f'HTTP {response.status_code}; catalog unavailable'
        except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
            catalogs[spec.provider] = f'Catalog unavailable: {type(exc).__name__}'
    failed = False
    prompt = build_judge_prompt('Write a Python function that adds two numbers.', 'def add(a, b):\n    return a + b', [], [], {})
    pool = JudgePool(settings)
    for spec in specs:
        print(f'{spec.name}: role={spec.role} provider={spec.provider} model={spec.model}: {catalogs[spec.provider]}', flush=True)
        if args.live:
            result = pool._judge_one(spec.provider, spec.model, spec.key, spec.role, prompt, spec.name)
            detail = 'Validated schema, rubric and evidence references.' if result.status == 'ok' else result.explanation
            print(f'  status={result.status} verdict={result.verdict}: {detail}', flush=True)
            failed |= result.status != 'ok'
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
