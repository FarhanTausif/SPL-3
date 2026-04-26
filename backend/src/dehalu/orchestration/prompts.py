from __future__ import annotations

from dehalu.schemas import CoderOutput, ExtractedClaim, JudgeResult, NormalizedRequest, PolicyDecision, SandboxResult, StaticFinding


def clarification_prompt(provider_name: str, request: NormalizedRequest) -> tuple[str, str]:
    provider_tone = {
        "gemini": "Return strict JSON only. Be concise and schema-faithful.",
        "mistral": "Return compact strict JSON only. Prefer explicit ambiguity flags.",
        "grok": "Return strict JSON only with practical coding assumptions.",
        "cerebras": "Return strict JSON only and keep each field literal.",
    }.get(provider_name, "Return strict JSON only.")
    return (
        "You clarify software requests before generation.",
        (
            f"{provider_tone}\n"
            "Normalize the coding request into a structured task spec.\n"
            f"Request:\n{request.model_dump_json(indent=2)}\n"
        ),
    )


def generation_prompt(provider_name: str, request: NormalizedRequest) -> tuple[str, str]:
    provider_tone = {
        "grok": "Prefer implementation speed while staying correct. Return only code.",
        "gemini": "Be conservative and schema-aware. Return only code.",
    }.get(provider_name, "Return only code.")
    return (
        "You are a coding model inside a verification gateway.",
        (
            f"{provider_tone}\n"
            f"Requested language: {request.language}\n"
            f"Risk level: {request.risk_level.value}\n"
            f"Latency budget seconds: {request.latency_budget_seconds}\n"
            f"Framework hint: {request.framework_hint or 'none'}\n"
            f"Target runtime: {request.target_runtime or 'none'}\n"
            f"Acceptance criteria: {request.acceptance_criteria}\n"
            f"User prompt:\n{request.prompt}\n"
        ),
    )


def judge_prompt(
    provider_name: str,
    request: NormalizedRequest,
    output: CoderOutput,
    claims: list[ExtractedClaim],
    static_findings: list[StaticFinding],
    sandbox_result: SandboxResult,
) -> tuple[str, str]:
    provider_tone = {
        "gemini": "Be strict about unsupported APIs and missing requirement coverage.",
        "mistral": "Prioritize contradiction detection and unsupported assumptions.",
        "cerebras": "Prefer deterministic-seeming evidence over fluent prose.",
        "grok": "Be practical but skeptical about library/API correctness.",
    }.get(provider_name, "Return strict JSON only.")
    prompt = (
        "Evaluate whether the generated code is hallucinated or unsupported.\n"
        f"{provider_tone}\n"
        "Use only the evidence below.\n\n"
        f"Normalized request:\n{request.model_dump_json(indent=2)}\n\n"
        f"Coder output:\n{output.model_dump_json(indent=2)}\n\n"
        f"Extracted claims:\n{_dump_models(claims)}\n\n"
        f"Static findings:\n{_dump_models(static_findings)}\n\n"
        f"Sandbox result:\n{sandbox_result.model_dump_json(indent=2)}\n"
    )
    return ("You are a code hallucination judge.", prompt)


def cove_prompt(
    provider_name: str,
    request: NormalizedRequest,
    output: CoderOutput,
    claims: list[ExtractedClaim],
    static_findings: list[StaticFinding],
    sandbox_result: SandboxResult,
    judge_result: JudgeResult,
) -> tuple[str, str]:
    provider_tone = {
        "mistral": "Break claims down explicitly and mark uncertain claims conservatively.",
        "gemini": "Return exact structured checks and summarize unsupported claims clearly.",
    }.get(provider_name, "Return strict JSON only.")
    prompt = (
        "Re-check each extracted claim independently against the generated code.\n"
        f"{provider_tone}\n"
        "Return one structured check per claim and summarize unsupported or uncertain claims.\n\n"
        f"Normalized request:\n{request.model_dump_json(indent=2)}\n\n"
        f"Coder output:\n{output.model_dump_json(indent=2)}\n\n"
        f"Extracted claims:\n{_dump_models(claims)}\n\n"
        f"Static findings:\n{_dump_models(static_findings)}\n\n"
        f"Sandbox result:\n{sandbox_result.model_dump_json(indent=2)}\n\n"
        f"Judge result:\n{judge_result.model_dump_json(indent=2)}\n"
    )
    return ("You are a Chain-of-Verification checker for generated code.", prompt)


def repair_prompt(
    provider_name: str,
    request: NormalizedRequest,
    output: CoderOutput,
    policy_decision: PolicyDecision,
    judge_result: JudgeResult,
    cove_result,
) -> tuple[str, str]:
    provider_tone = {
        "grok": "Favor direct minimal edits that preserve intent.",
        "gemini": "Be conservative and remove unsupported assumptions.",
        "mistral": "Prefer structurally safe rewrites over partial patches.",
        "cerebras": "Return corrected code only, with no explanation.",
    }.get(provider_name, "Return corrected code only.")
    prompt = (
        "Revise the generated code to address hallucination or unsupported-claim findings.\n"
        f"{provider_tone}\n"
        "Return only corrected source code.\n\n"
        f"Normalized request:\n{request.model_dump_json(indent=2)}\n\n"
        f"Current coder output:\n{output.model_dump_json(indent=2)}\n\n"
        f"Policy decision:\n{policy_decision.model_dump_json(indent=2)}\n\n"
        f"Judge result:\n{judge_result.model_dump_json(indent=2)}\n\n"
        f"CoVe result:\n{cove_result.model_dump_json(indent=2)}\n"
    )
    return ("You repair generated source code after hallucination detection.", prompt)


def _dump_models(models: list) -> str:
    if not models:
        return "[]"
    return "[\n" + ",\n".join(model.model_dump_json(indent=2) for model in models) + "\n]"
