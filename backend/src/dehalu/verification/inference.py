from __future__ import annotations

import re

from dehalu.api.schemas import InferenceResult


LANGUAGE_HINTS = {
    "python": ["python", "django", "flask", "fastapi", "pytest", "pandas", "numpy"],
    "javascript": ["javascript", "node", "express", "react", "next.js", "nextjs"],
    "typescript": ["typescript", "ts", "tsx"],
    "java": ["java", "spring"],
    "go": ["golang", " go "],
    "rust": ["rust", "cargo"],
    "c": [" c ", "clang"],
    "cpp": ["c++", "cpp"],
}


def infer_prompt(prompt: str, language_hint: str | None, constraints: list[str]) -> InferenceResult:
    text = f" {prompt.lower()} "
    language = language_hint or None
    if not language:
        for candidate, hints in LANGUAGE_HINTS.items():
            if any(hint in text for hint in hints):
                language = candidate
                break

    framework = _first_match(text, ["fastapi", "django", "flask", "react", "next.js", "express", "spring"])
    runtime = _first_match(text, ["node", "browser", "python 3", "jvm", "cli"])
    libraries = sorted(set(re.findall(r"(?:use|using|with|import)\s+([a-zA-Z_][\w.-]+)", prompt, re.I)))
    requirements = [sentence.strip() for sentence in re.split(r"[.;\n]", prompt) if sentence.strip()]
    uncertain = []
    questions = []

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
        uncertain_assumptions=uncertain,
        clarification_questions=questions,
        needs_clarification=bool(questions),
    )


def _first_match(text: str, values: list[str]) -> str | None:
    return next((value for value in values if value in text), None)
