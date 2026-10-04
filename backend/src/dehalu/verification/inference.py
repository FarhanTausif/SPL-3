from __future__ import annotations

import re

from dehalu.api.schemas import InferenceResult


LANGUAGE_HINTS = {
    "python": ["python", "django", "flask", "fastapi", "pytest", "pandas", "numpy"],
    "typescript": ["typescript", " ts ", "tsx"],
    "javascript": ["javascript", "node", "express", "react", "next.js", "nextjs"],
    "java": [" java ", "spring"],
    "go": ["golang", " go "],
    "rust": ["rust", "cargo"],
    "cpp": ["c++", "cpp"],
    "c": [" c ", "clang"],
}


def infer_prompt(prompt: str, language_hint: str | None, constraints: list[str]) -> InferenceResult:
    text = f" {prompt.lower()} "
    if language_hint:
        from dehalu.verification.adapters import normalize
        language_hint = normalize(language_hint)
    language = language_hint or None
    if not language:
        for candidate, hints in LANGUAGE_HINTS.items():
            if any(hint in text for hint in hints):
                language = candidate
                break

    framework = _first_match(text, ["fastapi", "django", "flask", "react", "next.js", "express", "spring"])
    runtime = _first_match(text, ["node", "browser", "python 3", "jvm", "cli"])
    candidates = re.findall(r"(?:using|import)\s+([a-zA-Z_][\w.-]+)", prompt, re.I)
    ignored = {'a', 'an', 'the', 'no', 'standard', *LANGUAGE_HINTS}
    libraries = sorted({name for name in candidates if name.lower() not in ignored})
    requirements = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+|\n", prompt) if sentence.strip()]
    uncertain = []
    questions = []

    if language and not language_hint and language not in text:
        uncertain.append(f"Target language {language} was inferred from framework/tool cues.")
    if not language:
        uncertain.append("Target language was not explicitly stated.")
        if len(prompt.split()) < 6:
            questions.append("Which programming language should DeHalu generate and verify?")

    if not requirements:
        questions.append("What should the generated code do?")

    if constraints:
        requirements.extend(constraints)

    return InferenceResult(
        language=language or "generic",
        framework=framework,
        runtime=runtime,
        libraries=libraries,
        requirements=requirements,
        constraints=constraints,
        uncertain_assumptions=uncertain,
        clarification_questions=questions,
        needs_clarification=bool(questions),
    )


def _first_match(text: str, values: list[str]) -> str | None:
    return next((value for value in values if value in text), None)
