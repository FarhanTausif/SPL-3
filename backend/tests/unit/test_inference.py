from dehalu.verification.inference import infer_prompt


def test_inference_marks_blocking_ambiguity() -> None:
    result = infer_prompt("add", None, [])

    assert result.needs_clarification is True
    assert result.clarification_questions


def test_inference_marks_uncertain_language_without_blocking() -> None:
    result = infer_prompt("Write a function that adds two numbers.", None, [])

    assert result.needs_clarification is False
    assert result.language == "generic"
    assert result.uncertain_assumptions


def test_framework_language_inference_marks_assumption_and_preserves_api_names():
    inferred = infer_prompt('Build an endpoint using FastAPI. Use json.loads for input.', None, [])
    assert inferred.language == 'python'
    assert inferred.uncertain_assumptions
    assert any('json.loads' in requirement for requirement in inferred.requirements)


def test_cpp_and_typescript_are_not_misidentified():
    assert infer_prompt('Use clang to write C++ code', None, []).language == 'cpp'
    assert infer_prompt('Write TypeScript for React', None, []).language == 'typescript'
