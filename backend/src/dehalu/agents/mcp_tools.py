"""MCP Tool Configuration for DeHalu CrewAI Agents.

This module defines Model Context Protocol (MCP) tool specifications and
bindings for agents in the hallucination detection and mitigation pipeline.

MCP tools provide read-only context and execution capabilities to agents,
allowing them to:
- Analyze code (parse, lint, validate syntax/semantics)
- Execute code safely (sandbox runtime)
- Validate claims (API/symbol existence, dependency availability)
- Look up documentation and metadata

Design Philosophy:
- Tools are deterministic and read-only (no state mutations)
- Each tool has a JSON schema for input validation and output contracts
- Tools are grouped by category (static-analysis, sandbox, api-validation, etc.)
- Agent tool bindings are explicit; agents only get tools they need
- Tool availability is checked at runtime; missing tools raise errors if required

Tool Categories:
1. **static-analysis** - Parse, lint, validate syntax/AST/symbols
2. **sandbox** - Safe, bounded code execution with resource monitoring
3. **api-validation** - Check API/package existence, signatures, versions
4. **documentation** - Fetch docs, examples, signatures from registries

Tool Providers:
Each tool is backed by a backend implementation in adapters/ or verification/:
- Language parsing: dehalu.adapters.language.tree_sitter, .parser, .validators
- Linting: dehalu.adapters.language.linters
- Sandbox: dehalu.verification.sandbox.runtime, .resource_monitor
- API/Docs: dehalu.adapters.tools.api_validator, .doc_lookup, .package_registry
- Symbols: dehalu.adapters.language.symbol_resolver

References:
- System_Design.md sections on Static Analysis, Sandbox Execution, Judges
- task_specs.py for agent task definitions and dependencies
- roles.py for agent role definitions and responsibilities
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPToolSpec:
    """Specification for an MCP tool available to agents.

    An MCPToolSpec defines the contract for a tool: its name, description,
    input/output schemas, whether it's required or optional for an agent,
    and which backend implementations provide it.

    Attributes:
        name: Unique identifier for the tool (kebab-case, e.g., "tree-sitter")
        description: One-sentence description of tool purpose
        category: Tool category: "static-analysis", "sandbox", "api-validation", "documentation"
        schema: JSON schema dict with "inputs" and "outputs" keys, each containing
                a "properties" dict and optional "required" list
        required: If True, agent MUST have this tool available
        providers: List of backend module paths that implement this tool
                   (e.g., ["dehalu.adapters.language.tree_sitter"])
    """

    name: str
    description: str
    category: str
    schema: dict[str, Any] = field(default_factory=dict)
    required: bool = False
    providers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate tool specification on initialization."""
        if not self.name or not self.name.islower() or " " in self.name:
            raise ValueError(f"Tool name must be lowercase kebab-case, got: {self.name}")
        if self.category not in ("static-analysis", "sandbox", "api-validation", "documentation"):
            raise ValueError(f"Invalid tool category: {self.category}")
        if not self.providers:
            raise ValueError(f"Tool {self.name} must have at least one provider")


# =============================================================================
# TOOL SPECIFICATIONS
# =============================================================================

TREE_SITTER_TOOL = MCPToolSpec(
    name="tree-sitter",
    description="Language-agnostic AST parsing and syntax validation using Tree-sitter.",
    category="static-analysis",
    schema={
        "inputs": {
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Source code to parse",
                },
                "language": {
                    "type": "string",
                    "description": "Language identifier (python, javascript, go, rust, c, cpp, java, etc.)",
                    "enum": ["python", "javascript", "typescript", "go", "rust", "c", "cpp", "java", "csharp"],
                },
            },
            "required": ["code", "language"],
        },
        "outputs": {
            "properties": {
                "ast": {
                    "type": "object",
                    "description": "Abstract syntax tree in JSON format",
                },
                "parse_errors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of parse errors or empty list if valid",
                },
                "syntax_valid": {
                    "type": "boolean",
                    "description": "True if code parsed without syntax errors",
                },
            },
            "required": ["ast", "parse_errors", "syntax_valid"],
        },
    },
    required=False,
    providers=["dehalu.adapters.language.tree_sitter"],
)

LINTER_ADAPTERS_TOOL = MCPToolSpec(
    name="linter-adapters",
    description="Language-specific linting and style checking.",
    category="static-analysis",
    schema={
        "inputs": {
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Source code to lint",
                },
                "language": {
                    "type": "string",
                    "description": "Language identifier",
                    "enum": ["python", "javascript", "typescript", "go", "rust", "c", "cpp", "java", "csharp"],
                },
                "rules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of rule names to check (e.g., ['unused-imports', 'undefined-names']); empty = all",
                },
            },
            "required": ["code", "language"],
        },
        "outputs": {
            "properties": {
                "lint_findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rule": {"type": "string"},
                            "severity": {"type": "string", "enum": ["error", "warning", "info"]},
                            "line": {"type": "integer"},
                            "column": {"type": "integer"},
                            "message": {"type": "string"},
                        },
                    },
                    "description": "List of linting violations",
                },
                "compliant": {
                    "type": "boolean",
                    "description": "True if code passes all checked rules",
                },
            },
            "required": ["lint_findings", "compliant"],
        },
    },
    required=False,
    providers=["dehalu.adapters.language.linters"],
)

AST_VALIDATOR_TOOL = MCPToolSpec(
    name="ast-validator",
    description="Validate AST structure, symbol definitions, and semantic constraints.",
    category="static-analysis",
    schema={
        "inputs": {
            "properties": {
                "ast": {
                    "type": "object",
                    "description": "Abstract syntax tree from tree-sitter (or similar)",
                },
                "language": {
                    "type": "string",
                    "description": "Language identifier",
                    "enum": ["python", "javascript", "typescript", "go", "rust", "c", "cpp", "java", "csharp"],
                },
            },
            "required": ["ast", "language"],
        },
        "outputs": {
            "properties": {
                "valid_symbols": {
                    "type": "boolean",
                    "description": "True if all symbol definitions and references are valid",
                },
                "invalid_refs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string"},
                            "reason": {"type": "string"},
                            "line": {"type": "integer"},
                        },
                    },
                    "description": "List of invalid symbol references",
                },
                "warnings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Non-critical semantic warnings",
                },
            },
            "required": ["valid_symbols", "invalid_refs", "warnings"],
        },
    },
    required=False,
    providers=["dehalu.adapters.language.validators"],
)

SANDBOX_RUNTIME_TOOL = MCPToolSpec(
    name="sandbox-runtime",
    description="Execute code safely in a bounded, isolated runtime with resource limits.",
    category="sandbox",
    schema={
        "inputs": {
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Source code to execute",
                },
                "language": {
                    "type": "string",
                    "description": "Language identifier",
                    "enum": ["python", "javascript", "typescript", "go", "rust", "c", "cpp", "java", "csharp"],
                },
                "timeout_ms": {
                    "type": "integer",
                    "description": "Execution timeout in milliseconds (default 5000)",
                    "minimum": 100,
                    "maximum": 60000,
                },
                "env_vars": {
                    "type": "object",
                    "description": "Environment variables to pass to the sandbox",
                },
            },
            "required": ["code", "language"],
        },
        "outputs": {
            "properties": {
                "exit_code": {
                    "type": "integer",
                    "description": "Process exit code (0 = success)",
                },
                "stdout": {
                    "type": "string",
                    "description": "Standard output from execution",
                },
                "stderr": {
                    "type": "string",
                    "description": "Standard error from execution",
                },
                "duration_ms": {
                    "type": "number",
                    "description": "Wall-clock execution time in milliseconds",
                },
                "timed_out": {
                    "type": "boolean",
                    "description": "True if execution exceeded timeout",
                },
            },
            "required": ["exit_code", "stdout", "stderr", "duration_ms", "timed_out"],
        },
    },
    required=False,
    providers=["dehalu.verification.sandbox.runtime"],
)

RESOURCE_MONITOR_TOOL = MCPToolSpec(
    name="resource-monitor",
    description="Track CPU, memory, and time usage during code execution.",
    category="sandbox",
    schema={
        "inputs": {
            "properties": {
                "pid": {
                    "type": "integer",
                    "description": "Process ID to monitor",
                },
                "metrics": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["cpu", "memory", "wall_time", "peak_memory"],
                    },
                    "description": "Metrics to collect",
                },
            },
            "required": ["pid", "metrics"],
        },
        "outputs": {
            "properties": {
                "cpu_usage": {
                    "type": "number",
                    "description": "CPU usage as a percentage (0-100)",
                },
                "memory_mb": {
                    "type": "number",
                    "description": "Current memory usage in MB",
                },
                "peak_memory_mb": {
                    "type": "number",
                    "description": "Peak memory usage in MB",
                },
                "wall_time_ms": {
                    "type": "number",
                    "description": "Elapsed wall-clock time in milliseconds",
                },
            },
            "required": ["cpu_usage", "memory_mb", "wall_time_ms"],
        },
    },
    required=False,
    providers=["dehalu.verification.sandbox.resource_monitor"],
)

API_CHECKER_TOOL = MCPToolSpec(
    name="api-checker",
    description="Validate API/symbol existence, signatures, and deprecation status.",
    category="api-validation",
    schema={
        "inputs": {
            "properties": {
                "api_name": {
                    "type": "string",
                    "description": "API or module name to check (e.g., 'requests', 'os.path')",
                },
                "symbol": {
                    "type": "string",
                    "description": "Specific symbol within the API (e.g., 'get', 'join')",
                },
                "language": {
                    "type": "string",
                    "description": "Language identifier",
                    "enum": ["python", "javascript", "typescript", "go", "rust", "c", "cpp", "java", "csharp"],
                },
                "version": {
                    "type": "string",
                    "description": "Specific version to check against (optional)",
                },
            },
            "required": ["api_name", "language"],
        },
        "outputs": {
            "properties": {
                "exists": {
                    "type": "boolean",
                    "description": "True if API/symbol exists",
                },
                "signature": {
                    "type": "string",
                    "description": "Function/method signature if found",
                },
                "deprecation_status": {
                    "type": "string",
                    "enum": ["active", "deprecated", "removed"],
                    "description": "Deprecation status",
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes or warnings",
                },
            },
            "required": ["exists", "deprecation_status"],
        },
    },
    required=False,
    providers=["dehalu.adapters.tools.api_validator"],
)

DEPENDENCY_VALIDATOR_TOOL = MCPToolSpec(
    name="dependency-validator",
    description="Check package/dependency existence, versions, and compatibility.",
    category="api-validation",
    schema={
        "inputs": {
            "properties": {
                "package_name": {
                    "type": "string",
                    "description": "Package name (e.g., 'numpy', '@babel/core')",
                },
                "version_spec": {
                    "type": "string",
                    "description": "Version specifier (e.g., '>=1.0.0', '^2.0', optional)",
                },
                "language": {
                    "type": "string",
                    "description": "Language/ecosystem identifier",
                    "enum": ["python", "javascript", "go", "rust", "java", "csharp", "cpp"],
                },
            },
            "required": ["package_name", "language"],
        },
        "outputs": {
            "properties": {
                "exists": {
                    "type": "boolean",
                    "description": "True if package exists in registry",
                },
                "latest_version": {
                    "type": "string",
                    "description": "Latest available version",
                },
                "compatibility": {
                    "type": "boolean",
                    "description": "True if version_spec is compatible with latest",
                },
                "registry": {
                    "type": "string",
                    "description": "Package registry used (PyPI, npm, etc.)",
                },
            },
            "required": ["exists", "registry"],
        },
    },
    required=False,
    providers=["dehalu.adapters.tools.dependency_checker"],
)

API_DOCS_LOOKUP_TOOL = MCPToolSpec(
    name="api-docs-lookup",
    description="Fetch API documentation, examples, and signatures from online registries.",
    category="documentation",
    schema={
        "inputs": {
            "properties": {
                "api_name": {
                    "type": "string",
                    "description": "API or module name",
                },
                "symbol": {
                    "type": "string",
                    "description": "Specific symbol to look up (method, class, function, etc.)",
                },
                "language": {
                    "type": "string",
                    "description": "Language identifier",
                    "enum": ["python", "javascript", "typescript", "go", "rust", "java", "csharp"],
                },
            },
            "required": ["api_name", "language"],
        },
        "outputs": {
            "properties": {
                "documentation": {
                    "type": "string",
                    "description": "Documentation text or markdown",
                },
                "examples": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Code examples from documentation",
                },
                "signature": {
                    "type": "string",
                    "description": "Function/method signature",
                },
                "url": {
                    "type": "string",
                    "description": "URL to documentation source",
                },
            },
            "required": ["documentation"],
        },
    },
    required=False,
    providers=["dehalu.adapters.tools.doc_lookup"],
)

SYMBOL_RESOLVER_TOOL = MCPToolSpec(
    name="symbol-resolver",
    description="Resolve symbol definitions and types within code or imported modules.",
    category="static-analysis",
    schema={
        "inputs": {
            "properties": {
                "symbol_name": {
                    "type": "string",
                    "description": "Symbol name to resolve (e.g., 'MyClass', 'my_function')",
                },
                "language": {
                    "type": "string",
                    "description": "Language identifier",
                    "enum": ["python", "javascript", "typescript", "go", "rust", "java", "csharp"],
                },
                "context": {
                    "type": "string",
                    "description": "Surrounding code context for scope resolution (optional)",
                },
            },
            "required": ["symbol_name", "language"],
        },
        "outputs": {
            "properties": {
                "definition": {
                    "type": "string",
                    "description": "Symbol definition (code snippet or signature)",
                },
                "location": {
                    "type": "string",
                    "description": "Location in source (module:line or file:line)",
                },
                "type": {
                    "type": "string",
                    "description": "Symbol type (function, class, variable, etc.)",
                    "enum": ["function", "class", "variable", "module", "constant", "interface", "type_alias", "unknown"],
                },
                "resolved": {
                    "type": "boolean",
                    "description": "True if symbol was successfully resolved",
                },
            },
            "required": ["resolved", "type"],
        },
    },
    required=False,
    providers=["dehalu.adapters.language.symbol_resolver"],
)

PACKAGE_REGISTRY_TOOL = MCPToolSpec(
    name="package-registry",
    description="Query package registries (PyPI, npm, crates.io, etc.) for metadata.",
    category="documentation",
    schema={
        "inputs": {
            "properties": {
                "package_name": {
                    "type": "string",
                    "description": "Package name to query",
                },
                "language": {
                    "type": "string",
                    "description": "Language/ecosystem",
                    "enum": ["python", "javascript", "go", "rust", "java", "csharp"],
                },
                "query": {
                    "type": "string",
                    "description": "Query type: 'metadata', 'versions', 'downloads', 'similar'",
                    "enum": ["metadata", "versions", "downloads", "similar"],
                },
            },
            "required": ["package_name", "language"],
        },
        "outputs": {
            "properties": {
                "metadata": {
                    "type": "object",
                    "description": "Package metadata (name, description, author, license, etc.)",
                },
                "latest_version": {
                    "type": "string",
                    "description": "Latest stable version",
                },
                "registry_url": {
                    "type": "string",
                    "description": "URL to package registry entry",
                },
                "found": {
                    "type": "boolean",
                    "description": "True if package exists",
                },
            },
            "required": ["found", "metadata"],
        },
    },
    required=False,
    providers=["dehalu.adapters.tools.package_registry"],
)

LANGUAGE_PARSER_TOOL = MCPToolSpec(
    name="language-parser",
    description="Extract language-specific metadata (imports, exports, classes, functions).",
    category="static-analysis",
    schema={
        "inputs": {
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Source code to parse",
                },
                "language": {
                    "type": "string",
                    "description": "Language identifier",
                    "enum": ["python", "javascript", "typescript", "go", "rust", "java", "csharp"],
                },
                "metadata_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["imports", "exports", "classes", "functions", "variables", "types"],
                    },
                    "description": "Types of metadata to extract (empty = all)",
                },
            },
            "required": ["code", "language"],
        },
        "outputs": {
            "properties": {
                "imports": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of imported modules/symbols",
                },
                "exports": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of exported symbols (if applicable)",
                },
                "classes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of defined classes",
                },
                "functions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of defined functions",
                },
                "variables": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of module-level variables",
                },
                "types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of type definitions (interfaces, type aliases, etc.)",
                },
            },
            "required": ["imports"],
        },
    },
    required=False,
    providers=["dehalu.adapters.language.parser"],
)

# =============================================================================
# TOOL REGISTRY
# =============================================================================

TOOLS_BY_NAME = {
    "tree-sitter": TREE_SITTER_TOOL,
    "linter-adapters": LINTER_ADAPTERS_TOOL,
    "ast-validator": AST_VALIDATOR_TOOL,
    "sandbox-runtime": SANDBOX_RUNTIME_TOOL,
    "resource-monitor": RESOURCE_MONITOR_TOOL,
    "api-checker": API_CHECKER_TOOL,
    "dependency-validator": DEPENDENCY_VALIDATOR_TOOL,
    "api-docs-lookup": API_DOCS_LOOKUP_TOOL,
    "symbol-resolver": SYMBOL_RESOLVER_TOOL,
    "package-registry": PACKAGE_REGISTRY_TOOL,
    "language-parser": LANGUAGE_PARSER_TOOL,
}

# =============================================================================
# AGENT-TOOL BINDINGS
# =============================================================================

AGENT_TOOL_BINDINGS = {
    "Clarification Agent": {
        "tools": [],
        "optional_tools": [],
        "rationale": "Clarification uses LLM reasoning only; no tool access needed.",
    },
    "Generator": {
        "tools": [],
        "optional_tools": [],
        "rationale": "Generator produces code based on prompt; verification happens downstream.",
    },
    "Claim Extractor": {
        "tools": ["language-parser"],
        "optional_tools": ["tree-sitter"],
        "rationale": "Extracts imports, symbols, classes, functions from generated code. Tree-sitter helps with edge cases.",
    },
    "Static Verifier": {
        "tools": ["tree-sitter", "linter-adapters", "ast-validator"],
        "optional_tools": ["symbol-resolver"],
        "rationale": "Performs deterministic syntax validation, linting, and semantic checks. Symbol resolver optional for import validation.",
    },
    "Sandbox Verifier": {
        "tools": ["sandbox-runtime"],
        "optional_tools": ["resource-monitor"],
        "rationale": "Executes code safely with timeout. Resource monitor optional for performance profiling.",
    },
    "Judge": {
        "tools": ["api-checker", "dependency-validator"],
        "optional_tools": ["api-docs-lookup"],
        "rationale": "Validates claims about APIs/dependencies. Docs lookup optional for signature verification.",
    },
    "CoVe": {
        "tools": [],
        "optional_tools": ["symbol-resolver", "api-checker"],
        "rationale": "Chain-of-Verification uses LLM reasoning; tools optional for claim cross-checking.",
    },
    "Policy Coordinator": {
        "tools": [],
        "optional_tools": [],
        "rationale": "Policy fusion is deterministic; no tool access needed.",
    },
    "Repair": {
        "tools": ["api-docs-lookup", "symbol-resolver", "package-registry"],
        "optional_tools": ["linter-adapters", "api-checker"],
        "rationale": "Needs docs, symbols, and package info to fix hallucinations. Optional linter/API checker for targeted fixes.",
    },
}

# =============================================================================
# TOOL PROVIDER REGISTRY
# =============================================================================

TOOL_PROVIDERS = {
    "tree-sitter": "dehalu.adapters.language.tree_sitter",
    "linter-adapters": "dehalu.adapters.language.linters",
    "ast-validator": "dehalu.adapters.language.validators",
    "sandbox-runtime": "dehalu.verification.sandbox.runtime",
    "resource-monitor": "dehalu.verification.sandbox.resource_monitor",
    "api-checker": "dehalu.adapters.tools.api_validator",
    "dependency-validator": "dehalu.adapters.tools.dependency_checker",
    "api-docs-lookup": "dehalu.adapters.tools.doc_lookup",
    "symbol-resolver": "dehalu.adapters.language.symbol_resolver",
    "package-registry": "dehalu.adapters.tools.package_registry",
    "language-parser": "dehalu.adapters.language.parser",
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_agent_tools(agent_role: str) -> tuple[list[MCPToolSpec], list[MCPToolSpec]]:
    """Get required and optional tools for an agent.

    Args:
        agent_role: Agent role name (e.g., "Static Verifier", "Judge")

    Returns:
        Tuple of (required_tools: list[MCPToolSpec], optional_tools: list[MCPToolSpec])

    Raises:
        ValueError: If agent_role is not found in AGENT_TOOL_BINDINGS
        KeyError: If a tool name in bindings is not in TOOLS_BY_NAME
    """
    if agent_role not in AGENT_TOOL_BINDINGS:
        raise ValueError(
            f"Agent role '{agent_role}' not found. Valid roles: "
            f"{', '.join(AGENT_TOOL_BINDINGS.keys())}"
        )

    bindings = AGENT_TOOL_BINDINGS[agent_role]
    required_tool_names = bindings["tools"]
    optional_tool_names = bindings["optional_tools"]

    required_tools = []
    for tool_name in required_tool_names:
        if tool_name not in TOOLS_BY_NAME:
            raise KeyError(f"Tool '{tool_name}' not defined in TOOLS_BY_NAME")
        required_tools.append(TOOLS_BY_NAME[tool_name])

    optional_tools = []
    for tool_name in optional_tool_names:
        if tool_name not in TOOLS_BY_NAME:
            raise KeyError(f"Tool '{tool_name}' not defined in TOOLS_BY_NAME")
        optional_tools.append(TOOLS_BY_NAME[tool_name])

    return required_tools, optional_tools


def get_tool_by_name(tool_name: str) -> MCPToolSpec:
    """Look up a tool specification by name.

    Args:
        tool_name: Tool name (e.g., "tree-sitter")

    Returns:
        MCPToolSpec for the tool

    Raises:
        KeyError: If tool_name not found
    """
    if tool_name not in TOOLS_BY_NAME:
        raise KeyError(
            f"Tool '{tool_name}' not found. Available tools: "
            f"{', '.join(TOOLS_BY_NAME.keys())}"
        )
    return TOOLS_BY_NAME[tool_name]


def validate_tool_availability(
    agent_role: str, available_tools: set[str]
) -> tuple[bool, list[str]]:
    """Check if all required tools are available for an agent.

    This function validates that an agent can access all required tools
    from its binding. Optional tools are not checked (missing optional
    tools degrade capability but don't fail validation).

    Args:
        agent_role: Agent role name
        available_tools: Set of tool names available to the agent

    Returns:
        Tuple of (all_available: bool, missing_tools: list[str])
        - all_available: True if all required tools are in available_tools
        - missing_tools: List of required tool names that are missing

    Raises:
        ValueError: If agent_role not found
    """
    if agent_role not in AGENT_TOOL_BINDINGS:
        raise ValueError(f"Agent role '{agent_role}' not found")

    required_tool_names = AGENT_TOOL_BINDINGS[agent_role]["tools"]
    missing_tools = [tool_name for tool_name in required_tool_names if tool_name not in available_tools]

    return len(missing_tools) == 0, missing_tools


def estimate_tool_usage(workflow_tasks: list[str]) -> dict[str, int]:
    """Estimate how many times each tool will be used in a workflow.

    Provides rough estimates based on typical verification flow:
    - ClaimExtractionTask uses language-parser and optionally tree-sitter
    - StaticAnalysisTask uses tree-sitter, linter-adapters, ast-validator
    - SandboxExecutionTask uses sandbox-runtime and optionally resource-monitor
    - JudgeTask uses api-checker and dependency-validator
    - RepairTask uses api-docs-lookup, symbol-resolver, package-registry

    Args:
        workflow_tasks: List of task names in workflow

    Returns:
        Dictionary mapping tool names to estimated call counts

    Example:
        >>> tasks = ["ClaimExtractionTask", "StaticAnalysisTask", "JudgeTask"]
        >>> usage = estimate_tool_usage(tasks)
        >>> usage["tree-sitter"]
        2  # used by claim extraction and static analysis
    """
    usage: dict[str, int] = {}

    task_tool_usage = {
        "ClarificationTask": {},
        "GenerationTask": {},
        "ClaimExtractionTask": {
            "language-parser": 1,
            "tree-sitter": 1,
        },
        "StaticAnalysisTask": {
            "tree-sitter": 1,
            "linter-adapters": 1,
            "ast-validator": 1,
            "symbol-resolver": 1,
        },
        "SandboxExecutionTask": {
            "sandbox-runtime": 1,
            "resource-monitor": 1,
        },
        "JudgeTask": {
            "api-checker": 2,
            "dependency-validator": 1,
            "api-docs-lookup": 1,
        },
        "CoVeTask": {
            "symbol-resolver": 1,
            "api-checker": 1,
        },
        "PolicyCoordinatorTask": {},
        "RepairTask": {
            "api-docs-lookup": 2,
            "symbol-resolver": 1,
            "package-registry": 1,
            "linter-adapters": 1,
            "api-checker": 1,
        },
    }

    for task_name in workflow_tasks:
        task_tools = task_tool_usage.get(task_name, {})
        for tool_name, count in task_tools.items():
            usage[tool_name] = usage.get(tool_name, 0) + count

    return usage


def get_tools_by_category(category: str) -> list[MCPToolSpec]:
    """Get all tools in a specific category.

    Args:
        category: Category name ("static-analysis", "sandbox", "api-validation", "documentation")

    Returns:
        List of MCPToolSpec objects in that category

    Raises:
        ValueError: If category is invalid
    """
    valid_categories = ("static-analysis", "sandbox", "api-validation", "documentation")
    if category not in valid_categories:
        raise ValueError(
            f"Invalid category '{category}'. Valid categories: {', '.join(valid_categories)}"
        )

    return [tool for tool in TOOLS_BY_NAME.values() if tool.category == category]


def get_all_tools() -> list[MCPToolSpec]:
    """Get all tool specifications.

    Returns:
        List of all MCPToolSpec objects in definition order
    """
    return list(TOOLS_BY_NAME.values())
