from __future__ import annotations

import ast
import re
from time import perf_counter

import httpx

from dehalu.schemas import AgentRole, ToolInvocationRecord, ToolPolicy


class ToolGateway:
    def __init__(self, default_policy: ToolPolicy | None = None, http_client: httpx.Client | None = None) -> None:
        self.default_policy = default_policy or ToolPolicy()
        self._http_client = http_client
        self._stdlib_modules = {"math", "json", "typing", "pathlib", "asyncio", "os", "sys", "re", "collections"}
        self._known_packages = {"fastapi", "sqlalchemy", "pydantic", "httpx", "pytest", "structlog", "crewai", "numpy"}

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
                    policy=effective,
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
        policy: ToolPolicy,
    ) -> ToolInvocationRecord:
        started = perf_counter()
        imports = sorted(
            set(
                [
                    *self._extract_import_roots(code),
                    *self._extract_package_like_terms(request_prompt),
                    *(claim for claim in claims if self._looks_like_package_name(claim)),
                ]
            )
        )
        known = [name for name in imports if name in self._stdlib_modules or name in self._known_packages]
        unknown = [name for name in imports if name not in known]
        live_checked: dict[str, dict[str, object]] = {}
        if policy.allow_web_lookup and self._domain_allowed(policy, "pypi.org"):
            live_checked = self._lookup_python_packages(unknown, timeout_seconds=policy.timeout_seconds)
            live_known = [name for name, result in live_checked.items() if result.get("found")]
            known = sorted(set([*known, *live_known]))
            unknown = [name for name in unknown if name not in live_known]
        summary = f"Validated {len(known)} known imports/packages; {len(unknown)} remained unsupported."
        return ToolInvocationRecord(
            tool_name="package_registry_lookup",
            agent_role=agent_role,
            inputs={"imports": imports},
            summary=summary,
            duration_ms=round((perf_counter() - started) * 1000, 3),
            changed_verdict=bool(unknown),
            metadata={
                "known": known,
                "unknown": unknown,
                "registry": "pypi",
                "live_lookup": bool(live_checked),
                "live_checked": live_checked,
            },
        )

    def _extract_import_roots(self, code: str) -> list[str]:
        roots: set[str] = set()
        try:
            tree = ast.parse(code)
        except SyntaxError:
            tree = None
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots.update(alias.name.split(".")[0] for alias in node.names if alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    roots.add(node.module.split(".")[0])
        for match in re.finditer(r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", code, flags=re.MULTILINE):
            roots.add(match.group(1).split(".")[0])
        return sorted(roots)

    def _extract_package_like_terms(self, text: str) -> list[str]:
        return sorted(
            {
                match.group(0).strip(".,;:()[]{}")
                for match in re.finditer(r"\b[A-Za-z][A-Za-z0-9_]*(?:[-_][A-Za-z0-9]+)+\b", text)
            }
        )

    def _looks_like_package_name(self, value: str) -> bool:
        return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:[-_][A-Za-z0-9]+)+", value))

    def _domain_allowed(self, policy: ToolPolicy, domain: str) -> bool:
        if not policy.allowed_domains:
            return False
        return any(allowed == domain or allowed.endswith(f".{domain}") for allowed in policy.allowed_domains)

    def _lookup_python_packages(self, package_names: list[str], *, timeout_seconds: float) -> dict[str, dict[str, object]]:
        results: dict[str, dict[str, object]] = {}
        if not package_names:
            return results

        client = self._http_client or httpx.Client(timeout=min(timeout_seconds, 8.0))
        close_client = self._http_client is None
        try:
            for package_name in package_names:
                candidates = self._pypi_name_candidates(package_name)
                result: dict[str, object] = {"found": False, "checked_names": candidates}
                for candidate in candidates:
                    try:
                        response = client.get(f"https://pypi.org/pypi/{candidate}/json")
                    except httpx.HTTPError as exc:
                        result = {
                            "found": False,
                            "checked_names": candidates,
                            "error": type(exc).__name__,
                        }
                        break
                    if response.status_code == 200:
                        payload = response.json()
                        info = payload.get("info", {}) if isinstance(payload, dict) else {}
                        result = {
                            "found": True,
                            "matched_name": info.get("name") or candidate,
                            "version": info.get("version"),
                            "registry_url": f"https://pypi.org/project/{candidate}/",
                        }
                        break
                    if response.status_code not in {404, 301, 302}:
                        result = {
                            "found": False,
                            "checked_names": candidates,
                            "status_code": response.status_code,
                        }
                        break
                results[package_name] = result
        finally:
            if close_client:
                client.close()
        return results

    def _pypi_name_candidates(self, package_name: str) -> list[str]:
        candidates = [package_name]
        hyphenated = package_name.replace("_", "-")
        underscored = package_name.replace("-", "_")
        for candidate in (hyphenated, underscored):
            if candidate not in candidates:
                candidates.append(candidate)
        return candidates

    def _python_symbol_validation(
        self,
        *,
        agent_role: AgentRole,
        claims: list[str],
        request_prompt: str,
        code: str,
        policy: ToolPolicy,
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
        policy: ToolPolicy,
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
        policy: ToolPolicy,
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
