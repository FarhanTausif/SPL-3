from __future__ import annotations

import httpx

from dehalu.adapters.tools import ToolGateway
from dehalu.schemas import AgentRole, ToolPolicy


def test_tool_gateway_enforces_budget() -> None:
    gateway = ToolGateway(default_policy=ToolPolicy(max_calls_per_role=2))

    records = gateway.run_verifier_suite(
        agent_role=AgentRole.judge,
        claims=["math", "math.sqrt", "missing_symbol"],
        request_prompt="Write Python code that uses math sqrt safely.",
        code="import math\nprint(math.sqrt(4))\n",
    )

    assert len(records) == 2
    assert records[0].tool_name == "package_registry_lookup"


def test_tool_gateway_marks_missing_symbols_as_verdict_changes() -> None:
    gateway = ToolGateway()

    records = gateway.run_verifier_suite(
        agent_role=AgentRole.cove,
        claims=["totally_missing_symbol"],
        request_prompt="Return code.",
        code="print('ok')\n",
    )

    symbol_check = next(record for record in records if record.tool_name == "python_symbol_validation")
    assert symbol_check.changed_verdict is True
    assert "totally_missing_symbol" in symbol_check.metadata["missing"]


def test_package_registry_lookup_extracts_imports_from_code_even_with_trailing_prose() -> None:
    code = """import numpy as np
from fast_vector_search import HybridGraphVectorIndex

index = HybridGraphVectorIndex(128)
```

This prose should not hide imports.
"""

    records = ToolGateway().run_verifier_suite(
        agent_role=AgentRole.judge,
        claims=[],
        request_prompt="Use fast-vector-search-lib.",
        code=code,
    )

    package_record = next(record for record in records if record.tool_name == "package_registry_lookup")

    assert "numpy" in package_record.metadata["known"]
    assert "fast_vector_search" in package_record.metadata["unknown"]
    assert package_record.changed_verdict is True


def test_package_registry_lookup_uses_pypi_when_policy_allows_domain() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/pypi/pandas/json":
            return httpx.Response(200, json={"info": {"name": "pandas", "version": "2.2.0"}})
        return httpx.Response(404)

    gateway = ToolGateway(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    records = gateway.run_verifier_suite(
        agent_role=AgentRole.judge,
        claims=[],
        request_prompt="Use pandas-dataframe-tools for context, but import pandas.",
        code="import pandas\n",
        policy=ToolPolicy(allow_web_lookup=True, allowed_domains=["pypi.org"]),
    )

    package_record = next(record for record in records if record.tool_name == "package_registry_lookup")

    assert any(str(request.url).endswith("/pypi/pandas/json") for request in requests)
    assert "pandas" in package_record.metadata["known"]
    assert "pandas" not in package_record.metadata["unknown"]
    assert package_record.metadata["live_lookup"] is True
