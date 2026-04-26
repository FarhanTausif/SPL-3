from __future__ import annotations


GENERATOR_AGENT = {
    "role": "Generator",
    "goal": "Produce a candidate code output for verification.",
    "backstory": "Executes the provider-backed generation stage inside the backend orchestration pipeline.",
}

CLAIM_EXTRACTOR_AGENT = {
    "role": "Claim Extractor",
    "goal": "Extract structured claims from the generated output.",
    "backstory": "Transforms generated code into explicit verification targets for downstream stages.",
}

STATIC_VERIFIER_AGENT = {
    "role": "Static Verifier",
    "goal": "Run deterministic syntax and static analysis checks.",
    "backstory": "Applies backend-owned language adapters and static rules before prompt-based judgment.",
}

JUDGE_AGENT = {
    "role": "Judge",
    "goal": "Score hallucination risk using structured judge output.",
    "backstory": "Calls the provider judge stage using normalized request and deterministic evidence.",
}

COVE_AGENT = {
    "role": "CoVe",
    "goal": "Re-check extracted claims independently.",
    "backstory": "Runs claim-by-claim verification using the backend-owned CoVe stage.",
}

REPAIR_AGENT = {
    "role": "Repair",
    "goal": "Trigger one repair attempt when policy requests mitigation.",
    "backstory": "Coordinates repair-and-retry without changing persistence or API behavior.",
}

POLICY_COORDINATOR_AGENT = {
    "role": "Policy Coordinator",
    "goal": "Decide whether to accept, warn, reject, or repair.",
    "backstory": "Fuses deterministic and prompt-based evidence into the final policy decision.",
}
