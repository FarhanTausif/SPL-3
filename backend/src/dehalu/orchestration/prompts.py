from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

from dehalu.schemas import (
    CoderOutput,
    ExtractedClaim,
    JudgeResult,
    NormalizedRequest,
    PolicyDecision,
    SandboxResult,
    StaticFinding,
)


_FALLBACK_TEMPLATES = {
    "version": "v1",
    "roles": {
        "clarification": {
            "default": {
                "system": "You clarify software requests before generation.",
                "tone": "Return strict JSON only.",
            }
        },
        "generation": {
            "default": {
                "system": "You are a coding model inside a verification gateway.",
                "tone": "Return only code.",
            }
        },
        "judge": {
            "default": {
                "system": "You are a code hallucination judge.",
                "tone": "Return strict JSON only.",
            }
        },
        "cove": {
            "default": {
                "system": "You are a Chain-of-Verification checker for generated code.",
                "tone": "Return strict JSON only.",
            }
        },
        "repair": {
            "default": {
                "system": "You repair generated source code after hallucination detection.",
                "tone": "Return corrected code only.",
            }
        },
    },
}


@dataclass(frozen=True, slots=True)
class PromptRender:
    system_instruction: str
    prompt: str
    version: str
    role: str
    provider_name: str


@lru_cache
def _load_templates() -> dict:
    try:
        raw = resources.files("dehalu.orchestration").joinpath("prompt_templates.json").read_text(encoding="utf-8")
    except FileNotFoundError:
        return _FALLBACK_TEMPLATES
    return json.loads(raw)


def _template(role: str, provider_name: str) -> tuple[str, str, str]:
    templates = _load_templates()
    version = templates.get("version", "v1")
    role_templates = templates.get("roles", {}).get(role, {})
    default = role_templates.get("default", {})
    provider = role_templates.get(provider_name, {})
    system_instruction = provider.get("system", default.get("system", "Return strict JSON only."))
    tone = provider.get("tone", default.get("tone", "Return strict JSON only."))
    return system_instruction, tone, version


def clarification_prompt(provider_name: str, request: NormalizedRequest) -> PromptRender:
    system_instruction, tone, version = _template("clarification", provider_name)
    prompt = (
        f"{tone}\n"
        "Normalize the coding request into a structured task spec.\n"
        f"Request:\n{request.model_dump_json(indent=2)}\n"
    )
    return PromptRender(system_instruction, prompt, version, "clarification", provider_name)


def generation_prompt(provider_name: str, request: NormalizedRequest) -> PromptRender:
    system_instruction, tone, version = _template("generation", provider_name)
    prompt = (
        f"{tone}\n"
        f"Requested language: {request.language}\n"
        f"Risk level: {request.risk_level.value}\n"
        f"Latency budget seconds: {request.latency_budget_seconds}\n"
        f"Framework hint: {request.framework_hint or 'none'}\n"
        f"Target runtime: {request.target_runtime or 'none'}\n"
        f"Acceptance criteria: {request.acceptance_criteria}\n"
        f"User prompt:\n{request.prompt}\n"
    )
    return PromptRender(system_instruction, prompt, version, "generation", provider_name)


def judge_prompt(
    provider_name: str,
    request: NormalizedRequest,
    output: CoderOutput,
    claims: list[ExtractedClaim],
    static_findings: list[StaticFinding],
    sandbox_result: SandboxResult,
) -> PromptRender:
    system_instruction, tone, version = _template("judge", provider_name)
    prompt = (
        "Evaluate whether the generated code is hallucinated or unsupported.\n"
        f"{tone}\n"
        "Use only the evidence below.\n\n"
        f"Normalized request:\n{request.model_dump_json(indent=2)}\n\n"
        f"Coder output:\n{output.model_dump_json(indent=2)}\n\n"
        f"Extracted claims:\n{_dump_models(claims)}\n\n"
        f"Static findings:\n{_dump_models(static_findings)}\n\n"
        f"Sandbox result:\n{sandbox_result.model_dump_json(indent=2)}\n"
    )
    return PromptRender(system_instruction, prompt, version, "judge", provider_name)


def cove_prompt(
    provider_name: str,
    request: NormalizedRequest,
    output: CoderOutput,
    claims: list[ExtractedClaim],
    static_findings: list[StaticFinding],
    sandbox_result: SandboxResult,
    judge_result: JudgeResult,
) -> PromptRender:
    system_instruction, tone, version = _template("cove", provider_name)
    prompt = (
        "Re-check each extracted claim independently against the generated code.\n"
        f"{tone}\n"
        "Return one structured check per claim and summarize unsupported or uncertain claims.\n\n"
        f"Normalized request:\n{request.model_dump_json(indent=2)}\n\n"
        f"Coder output:\n{output.model_dump_json(indent=2)}\n\n"
        f"Extracted claims:\n{_dump_models(claims)}\n\n"
        f"Static findings:\n{_dump_models(static_findings)}\n\n"
        f"Sandbox result:\n{sandbox_result.model_dump_json(indent=2)}\n\n"
        f"Judge result:\n{judge_result.model_dump_json(indent=2)}\n"
    )
    return PromptRender(system_instruction, prompt, version, "cove", provider_name)


def repair_prompt(
    provider_name: str,
    request: NormalizedRequest,
    output: CoderOutput,
    policy_decision: PolicyDecision,
    judge_result: JudgeResult,
    cove_result,
) -> PromptRender:
    system_instruction, tone, version = _template("repair", provider_name)
    prompt = (
        "Revise the generated code to address hallucination or unsupported-claim findings.\n"
        f"{tone}\n"
        "Return only corrected source code.\n\n"
        f"Normalized request:\n{request.model_dump_json(indent=2)}\n\n"
        f"Current coder output:\n{output.model_dump_json(indent=2)}\n\n"
        f"Policy decision:\n{policy_decision.model_dump_json(indent=2)}\n\n"
        f"Judge result:\n{judge_result.model_dump_json(indent=2)}\n\n"
        f"CoVe result:\n{cove_result.model_dump_json(indent=2)}\n"
    )
    return PromptRender(system_instruction, prompt, version, "repair", provider_name)


def _dump_models(models: list) -> str:
    if not models:
        return "[]"
    return "[\n" + ",\n".join(model.model_dump_json(indent=2) for model in models) + "\n]"
