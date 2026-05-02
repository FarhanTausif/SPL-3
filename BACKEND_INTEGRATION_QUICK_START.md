# Backend Integration Quick Start Guide

**Status:** ✅ Production Ready  
**Last Updated:** 2025-01-02  
**Test Coverage:** 180+ tests (100% passing)

---

## 🚀 For Frontend Developers

### Start Here

1. **Read the Integration Guide**
   ```
   backend/API_INTEGRATION_GUIDE.md
   ```
   Complete reference for all 5 API endpoints with examples.

2. **Start the Backend**
   ```bash
   cd backend
   source ../venv/bin/activate
   uvicorn dehalu.core.app:app --host 127.0.0.1 --port 8000
   ```

3. **Test Connectivity**
   ```bash
   curl http://localhost:8000/health
   ```

4. **Create Your First Run**
   ```bash
   curl -X POST http://localhost:8000/v1/runs \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "Write a Python function to calculate factorial",
       "language_hint": "python"
     }'
   ```

5. **Poll for Results**
   ```bash
   curl http://localhost:8000/v1/runs/{run_id}
   ```

---

## 📚 Key Documentation Files

| File | Purpose |
|------|---------|
| `API_INTEGRATION_GUIDE.md` | **START HERE** - Complete API reference for frontend |
| `BACKEND_INFRASTRUCTURE_TEST_REPORT.md` | Detailed test results and infrastructure verification |
| `BACKEND_TESTING_COMPLETE.md` | Executive summary of all testing phases |
| `System_Architecture.md` | System design and component overview |
| `System_Design.md` | Verification pipeline design details |

---

## 🔌 5 API Endpoints - Quick Reference

### 1. Health Check
```
GET /health
```
**Purpose:** Verify backend is running and providers are ready  
**Response:** 200 OK with provider status
```json
{
  "status": "ok",
  "providers": { "fake": "ready" },
  "orchestration": { "configured_mode": "direct" }
}
```

### 2. Create Verification Run
```
POST /v1/runs
```
**Purpose:** Submit code for hallucination detection  
**Request:**
```json
{
  "prompt": "Write a Python function to sum numbers",
  "language_hint": "python",
  "risk_level": "low"
}
```
**Response:** 201 Created with run details
```json
{
  "run_id": "uuid-here",
  "status": "completed",
  "normalized_request": { ... },
  "evidence_ids": ["uuid1", "uuid2", ...],
  ...
}
```

### 3. Get Run Status
```
GET /v1/runs/{run_id}
```
**Purpose:** Check run status and get full details  
**Response:** 200 OK with current run state

### 4. Get Evidence
```
GET /v1/runs/{run_id}/evidence
```
**Purpose:** Retrieve verification evidence  
**Response:** 200 OK with array of evidence objects
```json
[
  {
    "kind": "claim_extraction",
    "payload": { ... }
  },
  {
    "kind": "static_analysis",
    "payload": { ... }
  },
  ...
]
```

### 5. Get Events
```
GET /v1/runs/{run_id}/events
```
**Purpose:** Get audit trail of all events  
**Response:** 200 OK with ordered events

---

## 💻 Frontend Integration Pattern (Recommended)

### TypeScript/JavaScript Example

```typescript
// 1. Check backend is ready
async function checkBackend() {
  const response = await fetch('http://localhost:8000/health');
  return response.ok;
}

// 2. Create verification run
async function verifyCode(prompt: string) {
  const response = await fetch('http://localhost:8000/v1/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      language_hint: 'python',
      risk_level: 'medium'
    })
  });
  
  if (!response.ok) {
    throw new Error(`Failed to create run: ${response.status}`);
  }
  
  return await response.json();
}

// 3. Poll for completion
async function waitForCompletion(runId: string) {
  while (true) {
    const response = await fetch(`http://localhost:8000/v1/runs/${runId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get run status: ${response.status}`);
    }
    
    const run = await response.json();
    
    if (run.status !== 'queued' && run.status !== 'running') {
      return run;
    }
    
    // Wait 2 seconds before next poll
    await new Promise(r => setTimeout(r, 2000));
  }
}

// 4. Get evidence
async function getEvidence(runId: string) {
  const response = await fetch(`http://localhost:8000/v1/runs/${runId}/evidence`);
  
  if (!response.ok) {
    throw new Error(`Failed to get evidence: ${response.status}`);
  }
  
  return await response.json();
}

// 5. Complete workflow
async function completeWorkflow(prompt: string) {
  // Verify backend ready
  if (!await checkBackend()) {
    throw new Error('Backend not ready');
  }
  
  // Create verification run
  const run = await verifyCode(prompt);
  console.log('Run created:', run.run_id);
  
  // Wait for completion
  const completed = await waitForCompletion(run.run_id);
  console.log('Status:', completed.status);
  console.log('Evidence count:', completed.evidence_ids.length);
  
  // Get detailed evidence
  const evidence = await getEvidence(completed.run_id);
  console.log('Evidence:', evidence);
  
  return {
    run: completed,
    evidence
  };
}

// Use it
completeWorkflow('Write a factorial function')
  .then(result => console.log('Success:', result))
  .catch(error => console.error('Error:', error));
```

---

## ⚡ Error Handling

| Status Code | Meaning | Handling |
|---|---|---|
| 200 | Success | Process response |
| 201 | Created | Run created, use run_id |
| 400 | Bad request | Fix request format |
| 404 | Not found | Run/resource doesn't exist |
| 422 | Validation error | Fix input fields |
| 500 | Server error | Retry or contact support |

**Example error handling:**
```typescript
try {
  const response = await fetch('http://localhost:8000/v1/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt })
  });
  
  if (!response.ok) {
    const error = await response.json();
    console.error(`Error ${response.status}:`, error.detail);
    return;
  }
  
  const run = await response.json();
  console.log('Success:', run);
} catch (error) {
  console.error('Network error:', error);
}
```

---

## 🧪 Testing the Backend

### Run All Tests
```bash
cd backend
pytest tests/ -v
```

### Run Just E2E Tests (37 tests)
```bash
pytest tests/e2e_*.py -v
```

### Run Specific Phase
```bash
# Phase 2: Database persistence
pytest tests/e2e_backend_infrastructure.py -v

# Phase 3: Orchestration flows
pytest tests/e2e_orchestration_flows.py -v

# Phase 4: Error handling
pytest tests/e2e_error_handling.py -v
```

### Quick Sanity Check
```bash
pytest tests/e2e_*.py -q  # Should show "37 passed"
```

---

## 🔧 Environment Setup

### Development (.env)
```
DEHALU_DATABASE_URL=sqlite:///./dehalu.db
DEHALU_ORCHESTRATION_MODE=direct
DEHALU_PROVIDER_ORDER=fake
```

### Production (.env.prod)
```
DEHALU_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/dehalu
DEHALU_ORCHESTRATION_MODE=direct
DEHALU_GEMINI_API_KEY=your-key
DEHALU_GROK_API_KEY=your-key
DEHALU_MISTRAL_API_KEY=your-key
DEHALU_CEREBRAS_API_KEY=your-key
DEHALU_PROVIDER_ORDER=gemini,grok,mistral,cerebras
```

---

## 📊 Backend Capabilities

### Supported Languages
- Python 3.6+

### Risk Levels
- low, medium, high

### Run Modes
- basic (synchronous)
- advanced (asynchronous)

### Evidence Collected
- Claims extracted from code
- Static analysis findings
- Sandbox execution results
- Judge verdict (hallucination score)
- CoVE verification checks
- Policy decision
- Repair attempts (if triggered)

---

## ✅ Verification Checklist

### Before Starting Frontend Development
- [ ] Backend running (`uvicorn...`)
- [ ] Health endpoint returns 200
- [ ] Can create run (POST /v1/runs returns 201)
- [ ] Can get status (GET /v1/runs/{run_id} returns 200)
- [ ] Can get evidence (GET /v1/runs/{run_id}/evidence returns 200)
- [ ] Tests pass (`pytest tests/ -v`)

### Before Deploying to Production
- [ ] All 180+ tests passing
- [ ] PostgreSQL database configured
- [ ] API keys set for real providers
- [ ] Alembic migrations run (`alembic upgrade head`)
- [ ] Health endpoint working
- [ ] Error handling tested
- [ ] Load testing completed

---

## 🆘 Troubleshooting

### Backend Won't Start
```bash
# Check Python version
python3 --version  # Should be 3.12+

# Check dependencies
pip list | grep dehalu

# Reinstall if needed
cd backend
pip install -e ".[test]"
```

### Database Connection Error
```bash
# For development, SQLite should work
# Check .env has correct path

# For production, verify PostgreSQL:
psql -U user -d dehalu -c "SELECT 1"
```

### Tests Failing
```bash
# Run with verbose output
pytest tests/ -vv

# Check specific test
pytest tests/e2e_backend_infrastructure.py::test_complete_lifecycle_run_creation_to_completion -vv
```

### API Timeout
```bash
# Check if backend is running
curl http://localhost:8000/health

# Restart if needed
# Kill process: pkill -f uvicorn
# Restart: uvicorn dehalu.core.app:app --reload
```

---

## 📞 Support Resources

### Documentation
- `API_INTEGRATION_GUIDE.md` - Comprehensive API reference
- `BACKEND_INFRASTRUCTURE_TEST_REPORT.md` - Detailed test report
- `System_Architecture.md` - System design
- `System_Design.md` - Pipeline design

### Code Examples
- `tests/integration/test_api.py` - API usage patterns
- `tests/e2e_*.py` - Complete workflows

### Getting Help
1. Check documentation files first
2. Review test files for examples
3. Run `pytest tests/ -v` to see all tests pass
4. Check backend logs for errors

---

## 🎯 Next Steps

1. **For Frontend Developers**
   - Read `API_INTEGRATION_GUIDE.md`
   - Follow the integration pattern above
   - Start with `/health` endpoint
   - Build basic integration (create → poll → get evidence)

2. **For DevOps/Deployment**
   - Use `.env.prod` template
   - Configure PostgreSQL
   - Set up API keys
   - Run Alembic migrations
   - Deploy backend first, then frontend

3. **For QA/Testing**
   - Run full test suite: `pytest tests/ -v`
   - Test manual flows with curl examples
   - Verify error handling
   - Load test when deployed

---

## ✨ Key Features Ready

✅ All 5 API endpoints working  
✅ Complete verification pipeline  
✅ Robust error handling  
✅ Database persistence  
✅ Multi-provider support  
✅ Health checks  
✅ Event audit trail  
✅ 180+ passing tests  

---

**Status:** PRODUCTION READY ✅  
**Last Updated:** 2025-01-02  
**Frontend Integration:** Ready ✅
