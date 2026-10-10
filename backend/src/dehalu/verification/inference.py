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


def delegates_choices(prompt: str) -> bool:
    return bool(re.search(r"\b(?:do it on your own|you decide|use (?:the )?defaults|run anyway|choose for me|go ahead|decide yourself)\b", prompt, re.I))


def clarification_choices(question: str, language: str | None = None):
    """Deterministic fallback for older records and incomplete intake responses."""
    from dehalu.domain.models import ClarificationChoice, ClarificationQuestion
    if re.search(r'language|runtime|framework', question, re.I):
        options = [('Choose for me', f'Use {language if language and language != "generic" else "Python"} and sensible defaults.'),
                   ('Run in a browser', 'Use JavaScript in the browser.'),
                   ('Run on my computer', 'Use Python as a simple local program.')]
    else:
        options = [('Keep it simple', 'Implement the simplest useful version of my original request with sensible defaults.'),
                   ('Handle more cases', 'Implement my original request with input validation and common edge cases.'),
                   ('Make it reusable', 'Implement my original request as reusable functions with a usage example.')]
    return ClarificationQuestion(question=question, choices=[ClarificationChoice(label=label, value=value, recommended=i == 0) for i, (label, value) in enumerate(options)])


def normalize_model_intake(payload: dict, fallback: InferenceResult) -> InferenceResult:
    """Repair model-authored presentation fields before enforcing the API contract."""
    from pydantic import ValidationError
    if not isinstance(payload, dict):
        raise ValueError('Intake response must be an object')
    data = dict(payload)
    raw_questions = data.get('clarification_questions', [])
    questions = [q.strip() for q in raw_questions if isinstance(q, str) and q.strip()] if isinstance(raw_questions, list) else []
    raw_details = data.get('clarification_details', [])
    details = {}
    for item in raw_details if isinstance(raw_details, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get('question'), str):
            continue
        question = item['question'].strip()
        if not question: continue
        details[question] = item
    # Also retain detail-only questions when the model omitted the legacy field.
    if not isinstance(raw_questions, list) or not any(isinstance(q, str) and q.strip() for q in raw_questions):
        questions = list(details)
    questions = list(dict.fromkeys(questions))[:3]
    normalized = []
    for question in questions:
        choices = details.get(question, {}).get('choices')
        if (not isinstance(choices, list) or len(choices) != 3 or
            any(not isinstance(c, dict) or not isinstance(c.get('label'), str) or not c['label'].strip() or
                not isinstance(c.get('value'), str) or not c['value'].strip() for c in choices)):
            normalized.append(clarification_choices(question, fallback.language).model_dump())
            continue
        recommended = next((i for i, c in enumerate(choices) if c.get('recommended') in (True, 'true')), 0)
        normalized.append({'question': question, 'choices': [
            {'label': c['label'].strip(), 'value': c['value'].strip(), 'recommended': i == recommended}
            for i, c in enumerate(choices)]})
    data.update(clarification_questions=questions, clarification_details=normalized, needs_clarification=bool(questions))
    try:
        return InferenceResult.model_validate(data)
    except ValidationError:
        result = fallback.model_copy(deep=True)
        result.uncertain_assumptions.append('Model intake context was malformed; using prompt-derived context and default clarification choices.')
        return result


def finalize_intake(inference: InferenceResult, prompt: str, *, skip: bool = False) -> InferenceResult:
    """Bound clarification independently of what the local model requests."""
    if skip or delegates_choices(prompt):
        if inference.language in {None, 'generic'}:
            inference.language = 'python'
            inference.uncertain_assumptions.append('Python was selected as the default language.')
        if inference.clarification_questions:
            inference.uncertain_assumptions.extend(f'Using sensible defaults for: {q}' for q in inference.clarification_questions)
        inference.uncertain_assumptions.append('Unspecified details use the simplest useful implementation; clarification was bypassed or completed.')
        inference.clarification_questions = []
        inference.clarification_details = []
        inference.needs_clarification = False
    else:
        questions = list(dict.fromkeys(inference.clarification_questions))[:3]
        if inference.language in {None, 'generic'} and not questions:
            questions = ['Where would you like to use the result?']
        details = {item.question: item for item in inference.clarification_details}
        inference.clarification_questions = questions
        inference.clarification_details = [details.get(q) or clarification_choices(q, inference.language) for q in questions]
        inference.needs_clarification = bool(questions)
    inference.uncertain_assumptions = list(dict.fromkeys(inference.uncertain_assumptions))
    return inference
