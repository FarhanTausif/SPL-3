"""Measurements from provider token probabilities; never synthesize missing data."""
import math


def summarize_logprobs(records: list[dict], generated_tokens: int | None = None):
    entropies = []
    samples = []
    for record in records:
        sample = record.get('logprob')
        if isinstance(sample, (int, float)) and math.isfinite(sample) and sample <= 0:
            samples.append({'token': record.get('token', ''), 'logprob': sample})
        top = record.get('top_logprobs')
        if not isinstance(top, list) or not top or len(top) > 5:
            continue
        values = [item.get('logprob') for item in top if isinstance(item, dict)]
        if len(values) != len(top) or any(not isinstance(v, (int, float)) or not math.isfinite(v) or v > 0 for v in values):
            continue
        probabilities = [math.exp(value) for value in values]
        mass = sum(probabilities)
        if mass > 1 + 1e-5: continue
        if mass > 1: probabilities = [p / mass for p in probabilities]
        probabilities.append(max(0, 1 - sum(probabilities)))
        entropies.append(-sum(p * math.log(p) for p in probabilities if p > 0))
    common = {'source': 'ollama', 'method': 'top5_plus_remaining_mass', 'measured_tokens': len(entropies),
              'generated_tokens': generated_tokens, 'coverage': min(1, len(entropies) / generated_tokens) if generated_tokens else None,
              'scope': 'full_generated_response', 'full_distribution': False}
    entropy = {**common, 'available': bool(entropies)}
    if entropies:
        mean = sum(entropies) / len(entropies)
        entropy.update(mean_nats=mean, score=min(1, mean / math.log(6)), reason='Top-token entropy estimate; remaining probability mass is grouped, giving a lower bound.')
    else:
        entropy['reason'] = 'The provider returned no valid top-token probability distributions.'
    return entropy, {'source': 'ollama', 'available': bool(samples), 'tokens': samples, 'mean_logprob': sum(s['logprob'] for s in samples) / len(samples) if samples else None}
