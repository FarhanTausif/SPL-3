from __future__ import annotations

from time import perf_counter

from dehalu.schemas import AgentRole, ToolInvocationRecord, ToolPolicy


class ToolGateway:
    def __init__(self, default_policy: ToolPolicy | None = None) -> None:
        self.default_policy = default_policy or ToolPolicy()
        self._stdlib_modules = {"math", "json", "typing", "pathlib", "asyncio", "httpx", "fastapi"}
        self._known_packages = {"fastapi", "sqlalchemy", "pydantic", "httpx", "pytest", "structlog", "crewai"}

    def run_verifier_suite(
        self,
        *,
        agent_role: AgentRole,
        claims: list[str],
        request_prompt: str,
        code: str,
        policy: ToolPolicy | None = None,
    ) -> list[ToolInvocationRecord]:
        effective = policy or self.default_policy
        records: list[ToolInvocationRecord] = []
        budget = effective.max_calls_per_role
        for tool_name, runner in (
            ("package_registry_lookup", self._package_registry_lookup),
            ("python_symbol_validation", self._python_symbol_validation),
            ("requirement_checklist_matcher", self._requirement_checklist_matcher),
            ("claim_to_evidence_linker", self._claim_to_evidence_linker),
        ):
            if len(records) >= budget:
                break
            records.append(
                runner(
                    agent_role=agent_role,
                    claims=claims,
                    request_prompt=request_prompt,
                    code=code,
                )
            )
        return records

    def _package_registry_lookup(
        self,
        *,
        agent_role: AgentRole,
        claims: list[str],
        request_prompt: str,
        code: str,
    ) -> ToolInvocationRecord:
        started = perf_counter()
        imports = [claim for claim in claims if claim and "." not in claim]
        known = [name for name in imports if name in self._stdlib_modules or name in self._known_packages]
        unknown = [name for name in imports if name not in known]
        summary = f"Validated {len(known)} known imports; {len(unknown)} remained unsupported."
        return ToolInvocationRecord(
            tool_name="package_registry_lookup",
            agent_role=agent_role,
            inputs={"imports": imports},
            summary=summary,
            duration_ms=round((perf_counter() - started) * 1000, 3),
            changed_verdict=bool(unknown),
            metadata={"known": known, "unknown": unknown},
        )

    def _python_symbol_validation(
        self,
        *,
        agent_role: AgentRole,
        claims: list[str],
        request_prompt: str,
        code: str,
    ) -> ToolInvocationRecord:
        started = perf_counter()
        symbols = [claim for claim in claims if "." in claim or claim.isidentifier()]
        present = [symbol for symbol in symbols if symbol in code]
        missing = [symbol for symbol in symbols if symbol not in code]
        return ToolInvocationRecord(
            tool_name="python_symbol_validation",
            agent_role=agent_role,
            inputs={"symbols": symbols},
            summary=f"Matched {len(present)} symbols directly in the code; {len(missing)} were unsupported.",
            duration_ms=round((perf_counter() - started) * 1000, 3),
            changed_verdict=bool(missing),
            metadata={"present": present, "missing": missing},
        )

    def _requirement_checklist_matcher(
        self,
        *,
        agent_role: AgentRole,
        claims: list[str],
        request_prompt: str,
        code: str,
    ) -> ToolInvocationRecord:
        started = perf_counter()
        keywords = [token for token in request_prompt.lower().split() if len(token) > 4][:8]
        matched = [token for token in keywords if token in code.lower()]
        return ToolInvocationRecord(
            tool_name="requirement_checklist_matcher",
            agent_role=agent_role,
            inputs={"keywords": keywords},
            summary=f"Matched {len(matched)} request keywords in code.",
            duration_ms=round((perf_counter() - started) * 1000, 3),
            changed_verdict=False,
            metadata={"matched": matched, "unmatched": [token for token in keywords if token not in matched]},
        )

    def _claim_to_evidence_linker(
        self,
        *,
        agent_role: AgentRole,
        claims: list[str],
        request_prompt: str,
        code: str,
    ) -> ToolInvocationRecord:
        started = perf_counter()
        linked = {claim: ("supported" if claim in code else "unsupported") for claim in claims[:20]}
        unsupported = [claim for claim, verdict in linked.items() if verdict == "unsupported"]
        return ToolInvocationRecord(
            tool_name="claim_to_evidence_linker",
            agent_role=agent_role,
            inputs={"claim_count": len(claims)},
            summary=f"Linked {len(linked)} claims to local evidence with {len(unsupported)} unsupported.",
            duration_ms=round((perf_counter() - started) * 1000, 3),
            changed_verdict=bool(unsupported),
            metadata={"linked_claims": linked},
        )
