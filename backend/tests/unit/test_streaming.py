from dehalu.core.settings import Settings
from dehalu.providers.llm import OllamaClient


def test_fake_ollama_stream_emits_tokens_and_done_metadata() -> None:
    client = OllamaClient(Settings(allow_fake_llm=True))

    chunks = list(client.stream_generate("Write a Python function that adds two numbers."))

    from dehalu.providers.llm import validate_artifact
    code, _, _ = validate_artifact("".join(chunk.text for chunk in chunks), "python")
    assert code.startswith("def add")
    assert chunks[-1].done is True
    assert "entropy" in (chunks[-1].metadata or {})
