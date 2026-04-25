from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

try:
    from crewai import Agent, Crew, Process, Task

    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False

    class Process(StrEnum):
        sequential = "sequential"

    @dataclass
    class Agent:
        role: str
        goal: str
        backstory: str
        verbose: bool = False
        allow_delegation: bool = False
        tools: list[Any] = field(default_factory=list)
        llm: Any | None = None

    @dataclass
    class Task:
        description: str
        expected_output: str
        agent: Agent
        callback: Any | None = None

    @dataclass
    class Crew:
        agents: list[Agent]
        tasks: list[Task]
        process: Process = Process.sequential
        verbose: bool = False
