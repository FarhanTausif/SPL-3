# Frontend Phase 1 MVP - Testing & Integration Guide

## 🚀 Quick Start

### 1. Ensure Backend is Running

```bash
cd backend
uvicorn dehalu.core.app:app --reload --host 0.0.0.0 --port 8000
```

Verify with:
```bash
curl http://localhost:8000/health
```

### 2. Start Frontend

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 3. Test End-to-End Workflow

**Step A: Input Wizard**
1. Go to home page
2. Enter prompt: "Write a Python function that calculates factorial"
3. Select "Python" language
4. Choose "Medium" risk level
5. Click "Start Verification"

**Step B: Live Monitoring**
1. See real-time status display
2. Watch pipeline stages update
3. Monitor should poll every 2 seconds

**Step C: Results**
1. When verification completes, see verdict
2. View confidence score
3. See generated code with syntax highlighting
4. Review evidence summary

## 🔍 Testing Checklist

### API Integration Tests

#### ✅ Test 1: Create Run

```bash
curl -X POST http://localhost:8000/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a Python function to add two numbers",
    "language": "python",
    "risk_level": "medium"
  }'

# Expected response:
# {
#   "run_id": "...",
#   "status": "queued",
#   "created_at": "...",
#   "updated_at": "..."
# }
```

#### ✅ Test 2: Get Run Status

```bash
curl http://localhost:8000/v1/runs/{run_id}

# Expected responses:
# - status: "queued"
# - status: "started"
# - status: "completed"
# - status: "failed"
```

#### ✅ Test 3: Get Evidence

```bash
curl http://localhost:8000/v1/runs/{run_id}/evidence

# Expected: Array of evidence objects
# [
#   {
#     "id": "...",
#     "evidence_kind": "claims",
#     "finding": "...",
#     "timestamp": "..."
#   }
# ]
```

#### ✅ Test 4: Health Check

```bash
curl http://localhost:8000/health

# Expected: Provider status
# {
#   "status": "ok",
#   "providers": {...},
#   "worker_count": N
# }
```

### Frontend Component Tests

#### ✅ Test 5: Verification Form Validation

```typescript
// Test scenarios:
1. Empty prompt → Show "Prompt is required"
2. Prompt < 10 chars → Show "At least 10 characters"
3. Prompt > 5000 chars → Show "Max 5000 characters"
4. Valid prompt → Submit to backend
```

#### ✅ Test 6: Live Monitor Polling

```typescript
// Check DevTools Network tab:
1. See GET /v1/runs/{run_id} requests
2. Should occur every 2 seconds
3. Status should update in real-time
4. Should stop when status = "completed"
```

#### ✅ Test 7: Results Display

```typescript
// After completion, verify:
1. Verdict badge shows (ACCEPT/WARN/REJECT)
2. Confidence score displays
3. Generated code shows with syntax highlighting
4. Evidence list populated
5. Copy button works
```

#### ✅ Test 8: Error Handling

```typescript
// Test error scenarios:
1. Backend offline → Show "Cannot connect to backend"
2. Invalid run ID → Show "Run not found"
3. Network timeout → Auto-retry with backoff
4. 500 error → Show error message
```

### UI/UX Tests

#### ✅ Test 9: Responsive Design

```
1. Mobile (320px): Touch-friendly, stacked layout
2. Tablet (768px): Optimized columns, readable
3. Desktop (1024px+): Full layout, comfortable spacing
```

#### ✅ Test 10: Navigation

```
1. Home → Can submit prompt
2. Home → Monitor page (after submit)
3. Monitor → Back to home works
4. Direct URL access: /monitor/{run_id} works
```

## 📊 Performance Testing

### Load Testing

```bash
# Test with high traffic
ab -n 100 -c 10 http://localhost:3000

# Expected: < 3s response time
```

### Bundle Size Check

```bash
cd frontend
npm run build

# Check output:
# - /: 119 kB first load
# - /monitor/[id]: 125 kB first load
# - Shared: 87.3 kB
```

## 🧪 Browser DevTools Checks

### Network Tab

```
✓ POST /v1/runs (201 Created)
✓ GET /v1/runs/{run_id} (200 OK) - repeating every 2s
✓ GET /v1/runs/{run_id}/evidence (200 OK)
✓ No 404 or 500 errors
✓ No CORS errors
```

### Console Tab

```
✓ No TypeScript errors
✓ No runtime exceptions
✓ Zustand store logs (optional)
✓ React Query logs (optional)
```

### Application Tab

```
✓ Cookies: Check CORS settings
✓ Storage: Zustand state persistence (if configured)
✓ Cache: NextJS static generation working
```

## 🔐 Security Testing

### Input Validation

```bash
# Test prompt injection
curl -X POST http://localhost:8000/v1/runs \
  -d '{"prompt": "'; DROP TABLE --", ...}'
# Expected: Properly escaped/rejected
```

### CORS Testing

```javascript
// From browser console
fetch('http://localhost:8000/health')
  .then(r => r.json())
  .then(console.log)
// Expected: Should work (CORS enabled)
```

## 📈 Monitoring & Observability

### Logging

```typescript
// Check browser console for:
1. API request/response logs
2. Store state changes
3. Query status updates
4. Error messages
```

### Health Metrics

```bash
# Check backend health
curl http://localhost:8000/health | jq

# Monitor output:
{
  "status": "ok",
  "providers": {
    "gemini": "available",
    "grok": "available",
    ...
  },
  "worker_count": 2,
  "queue_depth": 0
}
```

## 🐛 Debugging

### Enable Debug Logging

```typescript
// In stores/runStore.ts or hooks
console.log('Polling run:', { runId, status, evidence })
```

### React Query DevTools

```bash
# Add to components (optional for Phase 2+)
npm install @tanstack/react-query-devtools
```

### Network Throttling

```
DevTools → Network → Throttle
1. Test with "Slow 3G"
2. Check loading states work
3. Verify error retry logic
```

## 🎯 Success Criteria

### Functional ✅
- [ ] Form submission creates run on backend
- [ ] Polling updates status every 2 seconds
- [ ] Results display after completion
- [ ] Evidence shows from all sources
- [ ] Navigation works correctly

### Performance ✅
- [ ] Home page loads in < 2 seconds
- [ ] Polling requests < 200ms each
- [ ] No jank during animations
- [ ] Mobile performance acceptable

### Usability ✅
- [ ] Form validation clear
- [ ] Error messages helpful
- [ ] Loading states visible
- [ ] Copy button works
- [ ] Responsive on mobile/tablet

### Reliability ✅
- [ ] No console errors
- [ ] No CORS errors
- [ ] No network timeouts
- [ ] Auto-retry on failure
- [ ] Graceful error handling

## 🚀 Integration Checklist

Before Phase 2, verify:

- [ ] Backend runs on localhost:8000
- [ ] All 5 API endpoints working
- [ ] Database persistence verified
- [ ] CORS enabled
- [ ] Frontend builds successfully
- [ ] End-to-end workflow tested
- [ ] Polling works as expected
- [ ] Results display correctly
- [ ] Error handling functional
- [ ] No console errors

## 📚 Useful Commands

```bash
# Frontend development
npm run dev              # Start dev server
npm run build           # Production build
npm run start           # Run production server
npm run lint            # Lint check

# Backend integration
curl http://localhost:8000/health
curl -X POST http://localhost:8000/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", "language": "python"}'

# Clean install
rm -rf node_modules package-lock.json
npm install
npm run dev
```

## 🎉 Next Steps After Phase 1

Once Phase 1 testing is complete:

1. **Phase 2: Premium Visualization**
   - Install React Flow
   - Create WorkflowDAG component
   - Add animated state transitions
   - Implement metrics dashboard

2. **Phase 3: Polish & Testing**
   - Add mobile optimization
   - Implement accessibility
   - Write unit tests (Vitest)
   - Write E2E tests (Cypress)
   - Create Storybook

3. **Phase 4-5: Future**
   - WebSocket real-time updates
   - Agent details modals
   - History tracking
   - Dark mode support

## 📞 Troubleshooting

### Issue: "Cannot connect to backend"
```bash
# Check backend
curl http://localhost:8000/health
# If fails, start backend:
cd backend && uvicorn dehalu.core.app:app
```

### Issue: "CORS error"
```
# Ensure backend has CORS enabled
# Check backend/src/dehalu/core/app.py
# Should include: app.add_middleware(CORSMiddleware, ...)
```

### Issue: "Polling stops after first request"
```typescript
// Check useRunStatus hook
// Verify refetchInterval: 2000 is set
// Check browser Network tab for requests
```

### Issue: "Cannot read property 'run_id' of undefined"
```typescript
// Verify API response structure
// Check if createRun returns { run_id, status, ... }
// Log response in VerificationForm.tsx
```

## ✅ Final Validation

Run this final test:

```bash
# Terminal 1: Start backend
cd backend
uvicorn dehalu.core.app:app

# Terminal 2: Start frontend
cd frontend
npm run dev

# Browser: Test complete flow
1. Go to http://localhost:3000
2. Submit: "Write a Python function to greet someone"
3. Watch polling in DevTools Network tab
4. Wait for completion
5. Verify results display
6. Check evidence populated

# Success if:
✓ Form submits
✓ Polling works every 2s
✓ Results show after ~30s
✓ No console errors
✓ No network errors
```

🎉 **If all tests pass, Phase 1 MVP is complete and ready for Phase 2!**
