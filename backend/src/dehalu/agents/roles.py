from __future__ import annotations


CODER_AGENT = {
    "role": "Code Generator",
    "goal": "Produce the initial candidate output for verification.",
    "backstory": "Coordinates code generation inside the backend orchestration scaffold.",
}

VERIFIER_AGENT = {
    "role": "Verification Coordinator",
    "goal": "Run deterministic and prompt-based verification over generated code.",
    "backstory": "Routes outputs through the backend-owned verification pipeline.",
}

REPAIR_AGENT = {
    "role": "Repair Coordinator",
    "goal": "Trigger one repair attempt when policy requests mitigation.",
    "backstory": "Coordinates repair-and-retry without changing persistence or API behavior.",
}
