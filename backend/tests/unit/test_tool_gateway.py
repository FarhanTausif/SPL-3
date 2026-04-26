from __future__ import annotations

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
