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
