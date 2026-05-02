# DeHalu Backend API Integration Guide

**Frontend Integration Ready ✓**  
**Version:** 1.0.0  
**Last Updated:** 2025-05-02  
**Base URL:** `http://localhost:8000` (development) | `https://api.dehalu.app` (production)

## Quick Start

### 1. Check Backend Health
```bash
curl http://localhost:8000/health | jq .
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "providers": {
    "fake": true,
    "gemini": false
  },
  "orchestration": {
    "configured_mode": "direct",
    "crewai_enabled": false,
    "queue_backlog": { "queued": 0, "total": 0 },
    "worker_readiness": { "state": "idle", "ready": true }
  }
}
```

### 2. Create a Verification Run
```bash
curl -X POST http://localhost:8000/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a Python function to calculate factorial",
    "language_hint": "python",
    "risk_level": "low"
  }' | jq .
```

**Response (201 Created):**
```json
{
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "coder_output": {
    "code": "def factorial(n):\n  return 1 if n <= 1 else n * factorial(n-1)",
    "language": "python",
    "dependencies": [],
    "assumptions": []
  },
  "policy_decision": {
    "state": "accept",
    "score": 0.95,
    "reasons": ["Static analysis passed", "Sandbox check passed"]
  },
  "evidence_ids": ["ev-1", "ev-2", "ev-3"],
  "fused_metrics": {
    "hallucination_likelihood": 0.05,
    "judge_confidence": 0.9
  }
}
```

---

## API Reference

### Endpoint 1: Health Check
**Purpose:** Verify backend readiness, check provider availability, worker status

```
GET /health
```

**Response:**
```json
{
  "status": "ok | degraded",
  "version": "0.1.0",
  "providers": {
    "fake": true,
    "gemini": false,
    "groq": false
  },
  "orchestration": {
    "configured_mode": "direct | crewai",
    "crewai_enabled": false,
    "crewai_available": false,
    "worker_id": "dehalu-worker-1",
    "queue_backlog": {
      "queued": 0,
      "total": 0,
      "has_backlog": false
    },
    "worker_readiness": {
      "state": "idle | running | stale",
      "ready": true,
      "age_seconds": null
    },
    "provider_role_readiness": {
      "routing_policy_version": "v1",
      "roles": {
        "generation": { "selected": "fake" },
        "judgment": { "selected": "fake" },
        "repair": { "selected": "fake" }
      },
      "live_provider_operation_ready": true
    }
  }
}
```

---

### Endpoint 2: Create Run
**Purpose:** Submit code for hallucination detection and verification

```
POST /v1/runs
Content-Type: application/json
```

**Request Body:**
```json
{
  "prompt": "Write a Python function that calculates...",
  "language_hint": "python",
  "risk_level": "low|medium|high",
  "latency_budget_seconds": 15,
  "provider": null,
  "run_mode": "basic",
  "target_runtime": "python3.9+",
  "framework_hint": "standard",
  "acceptance_criteria": []
}
```

**Field Details:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | ✓ | - | Natural language request for code generation |
| `language_hint` | string | ○ | "python" | Target language (python, javascript, java, etc.) |
| `risk_level` | enum | ○ | "medium" | low \| medium \| high - affects policy thresholds |
| `latency_budget_seconds` | int | ○ | 15 | 1-120; max time for verification pipeline |
| `provider` | string | ○ | auto | Specific provider or "auto" for selection |
| `run_mode` | string | ○ | "basic" | basic (sync) \| advanced (async with workers) |
| `target_runtime` | string | ○ | - | Runtime environment hint (e.g., "python3.9+") |
| `framework_hint` | string | ○ | "standard" | Framework context (e.g., "fastapi", "django") |
| `acceptance_criteria` | array | ○ | [] | Custom acceptance criteria for verification |

**Response (201 Created):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "normalized_request": {
    "original_prompt": "Write a function...",
    "prompt": "Write a function...",
    "language": "python",
    "risk_level": "low"
  },
  "status": "completed",
  "stage_summary": [
    {
      "stage": "generation",
      "duration_ms": 1250,
      "status": "completed"
    },
    {
      "stage": "verification",
      "duration_ms": 850,
      "status": "completed"
    }
  ],
  "coder_output": {
    "code": "def calculate_sum(n):\n  return sum(range(1, n+1))",
    "language": "python",
    "dependencies": [],
    "assumptions": ["Input is positive integer"]
  },
  "extracted_claims": [
    {
      "kind": "code",
      "value": "def calculate_sum(n):\n  return sum(range(1, n+1))",
      "line": 1
    }
  ],
  "static_findings": [],
  "sandbox_result": {
    "status": "passed",
    "duration_ms": 150,
    "output": "Test passed"
  },
  "judge_result": {
    "verdict": "pass",
    "hallucination_score": 0.05,
    "model": "gemini-2.0-flash",
    "duration_ms": 800
  },
  "cove_result": {
    "verdict": "pass",
    "hallucination_score": 0.02
  },
  "policy_decision": {
    "state": "accept",
    "reasons": ["Static analysis passed", "Sandbox passed", "Judge passed"],
    "score": 0.97,
    "hard_fail": false,
    "metrics": {
      "hallucination_likelihood": 0.03,
      "judge_confidence": 0.95
    }
  },
  "repair_result": null,
  "evidence_ids": ["ev-001", "ev-002", "ev-003"],
  "fused_metrics": {
    "hallucination_likelihood": 0.03,
    "judge_confidence": 0.95,
    "static_analysis_warnings": 0,
    "sandbox_status": "passed",
    "repair_attempted": false
  }
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 422 Unprocessable Entity | Invalid request format or missing required fields |
| 500 Internal Server Error | Backend service error (check `/health` status) |

---

### Endpoint 3: Get Run Status
**Purpose:** Poll run status, retrieve evidence, check completion

```
GET /v1/runs/{run_id}
```

**Path Parameters:**
- `run_id` (string, UUID): The run identifier from create_run response

**Response (200 OK):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-05-02T12:34:56Z",
  "updated_at": "2025-05-02T12:34:57Z",
  "status": "completed|running|queued|needs_clarification|failed",
  "normalized_request": { ... },
  "policy_decision": { ... },
  "fused_metrics": { ... },
  "evidence_summary": {
    "total": 5,
    "kinds": {
      "claim_extraction": 1,
      "static_analysis": 1,
      "sandbox": 1,
      "judge": 1,
      "policy": 1
    }
  }
}
```

**Status Values:**
- `queued` - Waiting to start (in worker queue)
- `running` - Currently processing
- `completed` - Finished successfully
- `needs_clarification` - Requires user input
- `failed` - Verification failed, code rejected

---

### Endpoint 4: Get Evidence
**Purpose:** Retrieve verification artifacts for a run

```
GET /v1/runs/{run_id}/evidence
```

**Response (200 OK):**
```json
[
  {
    "id": "ev-001",
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "kind": "claim_extraction",
    "payload": {
      "claims": [
        {
          "kind": "code",
          "value": "def factorial(n):\n  return 1 if n <= 1 else n * factorial(n-1)",
          "line": 1
        }
      ]
    },
    "created_at": "2025-05-02T12:34:56Z"
  },
  {
    "id": "ev-002",
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "kind": "static_analysis",
    "payload": {
      "findings": [],
      "syntax_valid": true
    },
    "created_at": "2025-05-02T12:34:56Z"
  }
]
```

**Evidence Kinds:**
- `claim_extraction` - Parsed claims from code
- `static_analysis` - Static code analysis findings
- `sandbox` - Execution sandbox results
- `judge` - LLM judge verdict
- `cove` - CoVe verification results
- `policy` - Final policy decision
- `repair` - Repair attempt results (if applicable)

---

### Endpoint 5: Get Event Stream
**Purpose:** Retrieve audit trail of run stages and transitions

```
GET /v1/runs/{run_id}/events
```

**Response (200 OK):**
```json
[
  {
    "sequence": 1,
    "event_type": "run_created",
    "stage": "initialization",
    "status": "started",
    "message": "Run created",
    "payload": {},
    "created_at": "2025-05-02T12:34:56Z"
  },
  {
    "sequence": 2,
    "event_type": "generation",
    "stage": "generation",
    "status": "started",
    "message": "Generating code with provider: gemini",
    "payload": { "provider": "gemini" },
    "created_at": "2025-05-02T12:34:56Z"
  },
  {
    "sequence": 3,
    "event_type": "generation",
    "stage": "generation",
    "status": "completed",
    "message": "Code generated successfully",
    "payload": { "duration_ms": 1250 },
    "created_at": "2025-05-02T12:34:57Z"
  },
  {
    "sequence": 4,
    "event_type": "verification",
    "stage": "verification",
    "status": "started",
    "message": "Starting verification pipeline",
    "payload": {},
    "created_at": "2025-05-02T12:34:57Z"
  }
]
```

---

## Common Use Patterns

### Pattern 1: Create Run & Wait for Result (Sync)
```typescript
// Frontend code (TypeScript)
async function verifyCode(prompt: string) {
  // 1. Create run
  const response = await fetch('http://localhost:8000/v1/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      language_hint: 'python',
      run_mode: 'basic'  // Synchronous
    })
  });
  
  const run = await response.json();
  
  // 2. Check status (for basic mode, already completed)
  if (run.status === 'completed') {
    console.log('Code accepted:', run.policy_decision.state);
    return run;
  }
  
  if (run.status === 'failed') {
    console.error('Code rejected:', run.policy_decision.reasons);
  }
  
  return run;
}
```

### Pattern 2: Create Run & Poll (Async)
```typescript
async function verifyCodeAsync(prompt: string) {
  // 1. Create run
  const response = await fetch('http://localhost:8000/v1/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      language_hint: 'python',
      run_mode: 'advanced'  // Asynchronous (queued)
    })
  });
  
  const run = await response.json();
  const runId = run.run_id;
  
  // 2. Poll status until completion
  let completed = false;
  let attempts = 0;
  const maxAttempts = 60;  // 1 minute with 1s intervals
  
  while (!completed && attempts < maxAttempts) {
    const statusResponse = await fetch(`http://localhost:8000/v1/runs/${runId}`);
    const status = await statusResponse.json();
    
    if (status.status === 'completed') {
      return status;
    }
    
    if (status.status === 'failed' || status.status === 'needs_clarification') {
      return status;
    }
    
    // Wait 1 second before next poll
    await new Promise(r => setTimeout(r, 1000));
    attempts++;
  }
  
  throw new Error('Verification timeout');
}
```

### Pattern 3: Retrieve Evidence Details
```typescript
async function getEvidence(runId: string) {
  const response = await fetch(`http://localhost:8000/v1/runs/${runId}/evidence`);
  const evidence = await response.json();
  
  // Find specific evidence kinds
  const claimExtraction = evidence.find(e => e.kind === 'claim_extraction');
  const staticAnalysis = evidence.find(e => e.kind === 'static_analysis');
  const judgeVerdict = evidence.find(e => e.kind === 'judge');
  
  return {
    claims: claimExtraction?.payload,
    staticIssues: staticAnalysis?.payload,
    judgeOpinion: judgeVerdict?.payload
  };
}
```

### Pattern 4: Check Backend Health
```typescript
async function checkBackendHealth() {
  const response = await fetch('http://localhost:8000/health');
  const health = await response.json();
  
  return {
    isHealthy: health.status === 'ok',
    providers: Object.keys(health.providers).filter(p => health.providers[p]),
    workerReady: health.orchestration.worker_readiness.ready,
    hasBacklog: health.orchestration.queue_backlog.has_backlog
  };
}
```

---

## Error Handling Guide

### 422 Unprocessable Entity
**Cause:** Invalid request format or missing required fields

**Example Error:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "prompt"],
      "msg": "Field required"
    }
  ]
}
```

**Fix:** Ensure all required fields are provided with correct types

---

### 404 Not Found
**Cause:** Run ID does not exist

**Example Error:**
```json
{
  "detail": "Run not found"
}
```

**Fix:** Verify run_id is correct UUID from create_run response

---

### 500 Internal Server Error
**Cause:** Backend service error

**Example Error:**
```json
{
  "detail": "Internal server error"
}
```

**Fix:** Check `/health` endpoint, verify database connectivity

---

## Rate Limiting & Quotas

**Current Implementation:** No rate limits (MVP)

**Recommended:**
- 100 requests/minute per IP
- 10 concurrent runs per user
- 5MB max code size

---

## Authentication

**Current Implementation:** None (open API for MVP)

**Planned (Future):** JWT or API keys

---

## Status Codes

| Code | Meaning | Scenario |
|------|---------|----------|
| 200 | OK | Health check, get run, get evidence |
| 201 | Created | Run successfully created |
| 400 | Bad Request | Malformed JSON request |
| 404 | Not Found | Run ID doesn't exist |
| 422 | Unprocessable Entity | Invalid request schema |
| 500 | Internal Error | Backend error |
| 503 | Service Unavailable | Providers down |

---

## Next Steps for Frontend

1. **Integration Testing**
   - Test each endpoint with valid/invalid inputs
   - Verify response schemas match documentation
   - Test error handling and retry logic

2. **UI Implementation**
   - Create form for code submission
   - Display verification status/progress
   - Show evidence and policy decisions
   - Handle error states gracefully

3. **Deployment**
   - Set production API base URL
   - Configure error logging/monitoring
   - Test with real provider API keys

---

## Support & Questions

For issues or questions about the API:
1. Check `/health` endpoint status
2. Review API_INTEGRATION_GUIDE.md (this file)
3. Check backend logs: `backend/logs/`
4. File an issue with request/response examples

---

**Version:** 1.0.0  
**Last Updated:** 2025-05-02  
**Status:** ✅ Ready for Production Integration
