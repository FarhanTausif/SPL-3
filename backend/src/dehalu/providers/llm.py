from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

import httpx

from dehalu.api.schemas import JudgeResult
from dehalu.core.settings import Settings


@dataclass(frozen=True)
class LLMStreamChunk:
    text: str = ""
    done: bool = False
    metadata: dict[str, Any] | None = None


def extract_code_block(text: str) -> tuple[str, str]:
    match = re.search(r"```(?:[a-zA-Z0-9_+-]+)?\n(?P<code>.*?)```", text, re.DOTALL)
    if match:
        code = match.group("code").strip()
        explanation = (text[: match.start()] + text[match.end() :]).strip()
        return code, explanation
    return text.strip(), ""


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, prompt: str) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
        if self.settings.allow_fake_llm:
            return self._fake_generation(prompt)

        payload = {"model": self.settings.ollama_model, "prompt": prompt, "stream": False}
        try:
            response = httpx.post(
                f"{self.settings.ollama_base_url.rstrip('/')}/api/generate",
                json=payload,
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # pragma: no cover - network dependent
            raise RuntimeError(f"Ollama generation failed: {exc}") from exc

        code, explanation = extract_code_block(str(data.get("response", "")))
        metadata = {
            "model": data.get("model", self.settings.ollama_model),
            "total_duration": data.get("total_duration"),
            "eval_count": data.get("eval_count"),
        }
        return code, explanation, {"available": False, "source": "ollama"}, metadata

    def repair(self, prompt: str) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
        return self.generate(prompt)

    def stream_generate(self, prompt: str):
        if self.settings.allow_fake_llm:
            code, _explanation, entropy, metadata = self._fake_generation(prompt)
            for index in range(0, len(code), 16):
                yield LLMStreamChunk(text=code[index : index + 16])
            yield LLMStreamChunk(done=True, metadata={"entropy": entropy, "logprob": metadata})
            return

        payload = {"model": self.settings.ollama_model, "prompt": prompt, "stream": True}
        final_metadata: dict[str, Any] = {}
        try:
            with httpx.stream(
                "POST",
                f"{self.settings.ollama_base_url.rstrip('/')}/api/generate",
                json=payload,
                timeout=self.settings.request_timeout_seconds,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    text = str(data.get("response", ""))
                    if text:
                        yield LLMStreamChunk(text=text)
                    if data.get("done"):
                        final_metadata = {
                            "model": data.get("model", self.settings.ollama_model),
                            "total_duration": data.get("total_duration"),
                            "eval_count": data.get("eval_count"),
                        }
                        yield LLMStreamChunk(
                            done=True,
                            metadata={
                                "entropy": {"available": False, "source": "ollama"},
                                "logprob": final_metadata,
                            },
                        )
        except Exception as exc:  # pragma: no cover - network dependent
            raise RuntimeError(f"Ollama streaming failed: {exc}") from exc

    def stream_repair(self, prompt: str):
        yield from self.stream_generate(prompt)

    def _fake_generation(self, prompt: str) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
        lower = prompt.lower()
        if "fake" in lower or "nonexistent" in lower:
            code = "import fake_lib_404\n\nresult = fake_lib_404.magic_call(data)\n"
        elif "unsafe" in lower or "delete" in lower:
            code = "import os\n\ndef cleanup(path):\n    os.system('rm -rf ' + path)\n"
        elif "javascript" in lower:
            code = "function add(a, b) {\n  return a + b;\n}\n"
        else:
            code = "def add(a, b):\n    return a + b\n"
        return code, "Fake provider response for local tests.", {"available": False}, {"fake": True}


class JudgePool:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def judge(self, full_prompt: str, fallback_score: float) -> list[JudgeResult]:
        judges = [
            ("gemini", self.settings.gemini_model, self.settings.gemini_api_key),
            ("groq", self.settings.groq_model, self.settings.groq_api_key),
            ("mistral", self.settings.mistral_model, self.settings.mistral_api_key),
        ]
        return [
            self._judge_one(name, model, key, full_prompt, fallback_score)
            for name, model, key in judges
        ]

    def _judge_one(
        self,
        name: str,
        model: str,
        api_key: str | None,
        prompt: str,
        fallback_score: float,
    ) -> JudgeResult:
        if not api_key or self.settings.allow_fake_llm:
            verdict = "pass" if fallback_score < 0.35 else "fail" if fallback_score > 0.7 else "warn"
            return JudgeResult(
                judge_name=name,
                judge_model=model,
                verdict=verdict,
                score=round(1.0 - fallback_score, 3),
                rubric_json={
                    "requirement_alignment": 1.0 - fallback_score,
                    "functional_logic": 1.0 - fallback_score,
                    "quality_safety": 1.0 - fallback_score,
                    "provider_configured": bool(api_key),
                },
                explanation=f"{name} used deterministic fallback because provider access is not configured.",
            )
        try:
            content = self._call_provider(name, model, api_key, prompt)
            parsed = _parse_judge_json(content)
            return JudgeResult(
                judge_name=name,
                judge_model=model,
                verdict=parsed.get("verdict", "warn"),
                score=float(parsed.get("score", max(0.0, 1.0 - fallback_score))),
                rubric_json=parsed.get("rubric_json", {}),
                explanation=parsed.get("explanation", content[:500]),
            )
        except Exception as exc:  # pragma: no cover - network dependent
            verdict = "pass" if fallback_score < 0.35 else "fail" if fallback_score > 0.7 else "warn"
            return JudgeResult(
                judge_name=name,
                judge_model=model,
                verdict=verdict,
                score=round(1.0 - fallback_score, 3),
                rubric_json={"provider_configured": True, "fallback_due_to_error": type(exc).__name__},
                explanation=f"{name} live judging failed, so deterministic fallback was used: {exc}",
            )

    def _call_provider(self, name: str, model: str, api_key: str, prompt: str) -> str:
        system = (
            "Return only JSON with keys verdict, score, rubric_json, explanation. "
            "Verdict must be pass, warn, or fail. Score is 0.0 to 1.0 where higher is better."
        )
        if name == "gemini":
            response = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": api_key, "content-type": "application/json"},
                json={
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": f"{system}\n\n{prompt}"}],
                        }
                    ]
                },
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        if name == "groq":
            return self._call_openai_compatible(
                "https://api.groq.com/openai/v1/chat/completions", api_key, model, system, prompt
            )
        if name == "mistral":
            return self._call_openai_compatible(
                "https://api.mistral.ai/v1/chat/completions", api_key, model, system, prompt
            )
        raise ValueError(f"Unsupported judge provider: {name}")

    def _call_openai_compatible(self, url: str, api_key: str, model: str, system: str, prompt: str) -> str:
        response = httpx.post(
            url,
            headers={"authorization": f"Bearer {api_key}", "content-type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
            },
            timeout=self.settings.request_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def build_judge_prompt(
    user_prompt: str,
    code: str,
    claims: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> str:
    return json.dumps(
        {
            "task": "Judge generated code for requirement alignment, functional logic, quality/safety, unsupported assumptions, dependency/API plausibility, and hallucination risk.",
            "user_prompt": user_prompt,
            "code": code,
            "claims": claims,
            "static_findings": findings,
            "metrics": metrics,
            "output_schema": {
                "verdict": "pass|warn|fail",
                "score": "0.0-1.0",
                "rubric_json": "per-category scores",
                "explanation": "short evidence-grounded explanation",
            },
        },
        indent=2,
    )


def _parse_judge_json(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    fenced = re.search(r"```(?:json)?\n(?P<body>.*?)```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group("body").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        data = json.loads(match.group(0)) if match else {}
    if not isinstance(data, dict):
        return {}
    if data.get("verdict") not in {"pass", "warn", "fail"}:
        data["verdict"] = "warn"
    data["score"] = max(0.0, min(1.0, float(data.get("score", 0.5))))
    return data
