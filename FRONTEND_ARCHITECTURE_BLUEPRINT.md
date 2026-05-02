# DeHalu Frontend - Architecture Blueprint & Agentic Workflow Visualization

**Status:** Planning Complete - Ready for Implementation  
**Target:** Premium, production-grade frontend with real-time workflow visualization

---

## 🎬 Complete User Journey & Agentic Workflow

### Step 1: User Enters Prompt
```
┌─────────────────────────────────────────────┐
│  Verification Wizard (Input Page)           │
├─────────────────────────────────────────────┤
│                                             │
│  📝 Prompt: "Write a Python function..."   │
│  🔤 Language: Python                        │
│  ⚠️  Risk Level: Medium                     │
│                                             │
│  [Advanced Options ▼]                       │
│  - Latency Budget: 15s                      │
│  - Framework: None                          │
│  - Tools Policy: Standard                   │
│                                             │
│                    [SUBMIT] ▶              │
└─────────────────────────────────────────────┘
```

**Action:** POST /v1/runs with { prompt, language_hint, risk_level, ... }

---

### Step 2: CrewAI Agentic Workflow Begins

#### Phase 2a: Clarification & Code Generation
```
┌──────────────────────────────────────────────────────────────┐
│  Backend Processing (Real-time visualization)                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  INPUT                                                       │
│  User Prompt → Normalization Engine                          │
│       │                                                      │
│       ├─→ [CLARIFICATION AGENT] ✅                          │
│       │    Role: Detect & clarify ambiguities               │
│       │    Task: "Is language 'python'? OK"                 │
│       │    MCP Tools: None (inference only)                 │
│       │    Status: COMPLETE (0.2s)                          │
│       │                                                      │
│       ├─→ [CODE GENERATION AGENT] ✅                        │
│       │    Role: Generate initial code draft                │
│       │    Model: Fake/Gemini/Grok/Mistral/Cerebras        │
│       │    Prompt: Multi-shot with assumptions              │
│       │    Output: Code + assumptions + metadata            │
│       │    Status: COMPLETE (0.5s)                          │
│       │                                                      │
│       └─→ [PARALLEL VERIFICATION PIPELINE] ⏳               │
│
└──────────────────────────────────────────────────────────────┘
```

#### Phase 2b: Parallel Verification (6 Concurrent Agents)
```
┌─────────────────────────────────────────────────────────────────────┐
│  VERIFICATION PIPELINE - 6 CONCURRENT AGENTS                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [CLAIM EXTRACTION AGENT] ✅                                        │
│  Role: Extract structured claims from generated code               │
│  Task: "Parse code for claims: imports, symbols, assumptions"      │
│  Input: coder_output.code, coder_output.assumptions                │
│  Output: ExtractedClaim[] (9 claims identified)                    │
│  Duration: 0.1s                                                     │
│  Result: ✅ PASS                                                    │
│  ────────────────────────────────────────────────────────────────  │
│
│  [STATIC ANALYSIS AGENT] ✅                                         │
│  Role: Static code checking (imports, types, symbols)              │
│  Tool: Tree-sitter parser + validation                             │
│  Checks: Import resolution, symbol validity, syntax                │
│  Output: StaticFinding[] (1 finding: import math OK)               │
│  Duration: 0.05s                                                    │
│  Result: ✅ PASS (no errors)                                        │
│  ────────────────────────────────────────────────────────────────  │
│
│  [SANDBOX EXECUTION AGENT] ✅                                       │
│  Role: Execute code in bounded environment                         │
│  Tool: Sandbox executor with resource limits                       │
│  Check: Compilation, runtime errors, execution timeout             │
│  Output: SandboxResult { status: "passed", duration: 0.1ms }       │
│  Duration: 0.1ms                                                    │
│  Result: ✅ PASS (compiles cleanly)                                 │
│  ────────────────────────────────────────────────────────────────  │
│
│  [JUDGE AGENT] ✅                                                   │
│  Role: LLM-based verdict on hallucination                          │
│  Model: Gemini/Grok/Mistral judging same coder output              │
│  Prompt: "Does this code claim match the implementation?"          │
│  Output: JudgeResult {                                             │
│    verdict: "pass",                                                │
│    hallucination_score: 0.05,  // Very low risk                    │
│    findings: [],                                                   │
│    metrics: { ... }                                                │
│  }                                                                  │
│  Duration: 13ms                                                     │
│  Result: ✅ PASS                                                    │
│  ────────────────────────────────────────────────────────────────  │
│
│  [CoVE VERIFICATION AGENT] ✅                                       │
│  Role: Chain-of-Verification - detailed claim verification        │
│  Method: Ask specific questions about each claim                   │
│  Claims Checked: 9/9                                               │
│  Output: CoVEResult {                                              │
│    verdict: "pass",                                                │
│    checks: [9 supported claims],                                   │
│    metrics: {                                                      │
│      supported_claim_count: 9,                                     │
│      unsupported_claim_count: 0,                                   │
│      uncertain_claim_count: 0                                      │
│    }                                                               │
│  }                                                                  │
│  Duration: 94ms                                                     │
│  Result: ✅ PASS                                                    │
│  ────────────────────────────────────────────────────────────────  │
│
│  [POLICY COORDINATOR AGENT] ✅                                      │
│  Role: Aggregate evidence → FINAL DECISION                         │
│  Input: All evidence from above 5 agents                           │
│  Decision Logic:                                                   │
│    - Judge score: 0.05 (low risk) → GREEN                         │
│    - CoVE verdict: pass (9/9 claims verified) → GREEN              │
│    - Static: no errors → GREEN                                     │
│    - Sandbox: passed → GREEN                                       │
│    - Policy thresholds: all passed → DECISION: ACCEPT              │
│  Output: PolicyDecision {                                          │
│    state: "accept",                                                │
│    score: 0.95,  // Confidence in decision                         │
│    reasons: [                                                      │
│      "No blocking hallucination evidence detected",                │
│      "All verification stages passed",                             │
│      "Judge & CoVE consensus: low risk"                            │
│    ]                                                               │
│  }                                                                  │
│  Duration: 5ms                                                      │
│  Result: ✅ PASS → ACCEPT CODE                                      │
│
└─────────────────────────────────────────────────────────────────────┘
```

**Timeline:** All 6 agents run in parallel (staggered), ~100ms total

---

### Step 3: Hallucination Detection Result

#### Scenario A: No Hallucination Detected ✅

```
RESULT:
┌────────────────────────────────────────┐
│  ✅ HALLUCINATION DETECTION COMPLETE  │
├────────────────────────────────────────┤
│                                        │
│  Risk Assessment: LOW ✅               │
│  Confidence: 0.95 (95%)                │
│                                        │
│  Verdict: ACCEPT CODE                  │
│                                        │
│  Evidence Summary:                     │
│  ✅ Claims Extraction: 9 claims found  │
│  ✅ Static Analysis: 0 errors          │
│  ✅ Sandbox Execution: Passed          │
│  ✅ Judge Verdict: 0.05 risk score    │
│  ✅ CoVE Verification: 9/9 verified   │
│  ✅ Policy Decision: ACCEPT            │
│                                        │
│  Code Quality: ⭐⭐⭐⭐⭐                │
│                                        │
│  [Show Details] [Copy Code] [Download] │
└────────────────────────────────────────┘
```

**Return to Frontend:** 201 Created response with complete evidence

---

#### Scenario B: Hallucination Detected & Triggering Mitigation 🔴

```
INTERMEDIATE RESULT:
┌────────────────────────────────────────┐
│  ⚠️  HALLUCINATION DETECTED!            │
├────────────────────────────────────────┤
│                                        │
│  Risk Assessment: HIGH ⚠️               │
│  Confidence: 0.85 (85%)                │
│                                        │
│  Issues Found:                         │
│  ❌ Static Analysis: Unresolved import │
│     "numpy not found in environment"   │
│  ⚠️  CoVE Verification: 7/9 claims ok  │
│     "2 claims about numpy require"     │
│                                        │
│  Policy Decision: REPAIR_AND_RETRY     │
│                                        │
│  Triggering Mitigation Flow...         │
│  [Building Failure Context...]         │
│                                        │
└────────────────────────────────────────┘
                    │
                    ▼
        [FIXER AGENT] Activated ✨
```

---

### Step 4: Mitigation Flow (if Hallucination Detected)

#### Phase 4a: Failure Context Building
```
┌──────────────────────────────────────────────────────┐
│  [FAILURE CONTEXT BUILDER]                          │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Analyzing why verification failed...                │
│                                                      │
│  Root Cause: "Code imports 'numpy' but it's not    │
│              installed in the environment"          │
│                                                      │
│  Extracted Issues:                                   │
│  1. Import Error: numpy (unresolved)                │
│  2. Missing Dependency: numpy package               │
│                                                      │
│  Failed Evidence:                                    │
│  - Static Finding: Import resolution error          │
│  - Sandbox Result: Import failed at line 1          │
│  - CoVE Finding: Claims about numpy unverifiable   │
│                                                      │
│  Context Summary:                                    │
│  "Remove numpy usage or add to dependencies"        │
│                                                      │
└──────────────────────────────────────────────────────┘
```

#### Phase 4b: Fixer Agent Works to Repair
```
┌──────────────────────────────────────────────────────┐
│  [FIXER AGENT] 🔧                                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Role: Generate corrected code                      │
│  MCP Tools Available:                                │
│    - code_analyzer: Analyze error details           │
│    - dependency_resolver: Find alternatives         │
│    - code_generator: Generate fixed version         │
│                                                      │
│  Task: "Rewrite code without numpy dependency"      │
│                                                      │
│  Process:                                            │
│  1. Analyze original code                           │
│  2. Identify numpy usage                            │
│  3. Find alternative without numpy                  │
│  4. Generate corrected code                         │
│  5. Return fixed version                            │
│                                                      │
│  Result:                                             │
│  ✅ Fixed Code Generated                            │
│                                                      │
│  Original:                                           │
│  ```python                                           │
│  import numpy as np                                  │
│  def sum_array(arr):                                │
│      return np.sum(arr)                             │
│  ```                                                 │
│                                                      │
│  Fixed:                                              │
│  ```python                                           │
│  def sum_array(arr):                                │
│      return sum(arr)  # No numpy needed            │
│  ```                                                 │
│                                                      │
│  Duration: 0.8s                                      │
│                                                      │
└──────────────────────────────────────────────────────┘
```

#### Phase 4c: Re-Verification (Loop Back)
```
┌──────────────────────────────────────────────────────┐
│  RE-VERIFICATION CYCLE (policy: allow_repair=false) │
├──────────────────────────────────────────────────────┤
│                                                      │
│  [CLAIM EXTRACTION] ✅ 5 claims (reduced)           │
│  [STATIC ANALYSIS] ✅ No errors!                    │
│  [SANDBOX] ✅ Compiles & runs OK                    │
│  [JUDGE] ✅ Risk score: 0.02                        │
│  [CoVE] ✅ 5/5 claims verified                      │
│  [POLICY] ✅ DECISION: ACCEPT                       │
│                                                      │
│  Duration: 0.3s                                      │
│  Result: ✅ REPAIRED CODE ACCEPTED                  │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

### Step 5: Final Results Display

#### Both Scenarios Converge Here

```
┌─────────────────────────────────────────────────────┐
│  FINAL RESULTS PAGE                                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ✅ Verification Complete (1.8s total)              │
│                                                     │
│  HALLUCINATION RISK: LOW ✅                         │
│  Confidence Score: 0.95 (95%)                       │
│                                                     │
│  ┌─ GENERATED CODE ──────────────────────────────┐  │
│  │ def sum_array(arr):                           │  │
│  │     return sum(arr)                           │  │
│  │                                               │  │
│  │ [Copy] [Download] [Share]                     │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  📊 VERIFICATION BREAKDOWN                         │
│  ├─ Claims Extracted: 5                            │
│  ├─ Static Issues: 0 (After repair)               │
│  ├─ Sandbox Status: ✅ PASSED                      │
│  ├─ Judge Score: 0.02 (Very low risk)             │
│  ├─ CoVE Verified: 5/5 claims                     │
│  └─ Final Decision: ACCEPT                        │
│                                                     │
│  ⏱️  TIMING                                         │
│  ├─ Generation: 0.5s                              │
│  ├─ Claims: 0.1s                                  │
│  ├─ Static: 0.05s                                 │
│  ├─ Sandbox: 0.1ms                                │
│  ├─ Judge: 13ms                                   │
│  ├─ CoVE: 94ms                                    │
│  ├─ Policy: 5ms                                   │
│  ├─ Repair: 0.8s (if needed)                      │
│  └─ Re-verify: 0.3s (if needed)                   │
│                                                     │
│  📋 FULL EVIDENCE REPORT                           │
│  [Show All Evidence] [Download PDF] [Export JSON]  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🎨 Frontend UI Components Map

### Real-time Workflow Visualization (React Flow DAG)

```
┌─────────────────────────────────────────────────────────────────┐
│                   LIVE AGENTIC WORKFLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ INPUT ─────┐                                               │
│  │  Prompt &   │                                               │
│  │  Settings   │                                               │
│  └──────┬──────┘                                               │
│         │                                                      │
│    ┌────▼─────────┐                                            │
│    │ CLARIFICATION │ ✅ (0.2s)                                 │
│    │    AGENT      │                                           │
│    └────┬──────────┘                                           │
│         │                                                      │
│    ┌────▼──────────┐                                           │
│    │  GENERATION   │ ✅ (0.5s)                                 │
│    │    AGENT      │                                           │
│    └────┬──────────┘                                           │
│         │                                                      │
│    ┌────┴────────────────────────────────────┐                │
│    │   PARALLEL VERIFICATION PIPELINE        │                │
│    └────┬────────────────────────────────────┘                │
│         │                                                      │
│  ┌──────┴──────┐ ┌──────────┐ ┌──────────┐                   │
│  │   CLAIM     │ │  STATIC  │ │ SANDBOX  │                   │
│  │ EXTRACTION  │ │ ANALYSIS │ │   TEST   │                   │
│  │ ✅ 0.1s    │ │ ✅ 0.05s │ │✅ 0.1ms │                   │
│  └──────┬──────┘ └────┬─────┘ └────┬─────┘                   │
│         │             │             │                         │
│  ┌──────┴──────┐ ┌────▼────┐ ┌────▼────┐                    │
│  │    JUDGE    │ │  CoVE    │ │  POLICY │                    │
│  │   VERDICT   │ │VERIFIER  │ │ DECISION│                    │
│  │ ✅ 13ms    │ │✅ 94ms  │ │✅ 5ms  │                    │
│  └──────┬──────┘ └────┬────┘ └────┬────┘                    │
│         │             │            │                         │
│         └─────────────┴────┬───────┘                          │
│                            │                                  │
│                     ┌──────▼────────┐                         │
│                     │   DECISION    │                         │
│                     │   ACCEPT/     │                         │
│                     │   REPAIR/     │                         │
│                     │   REJECT      │                         │
│                     └──────┬────────┘                         │
│                            │                                  │
│      ┌─────────────────────┤                                  │
│      │                     │                                  │
│   [REPAIR]           [RETURN RESULT]                         │
│      │                     │                                  │
│   [FIXER]            [RESULTS PAGE]                          │
│   AGENT ✨                                                    │
│      │                                                       │
│      └──────────────┐                                         │
│                     ▼                                         │
│              [RE-VERIFY]                                      │
│              Loop back                                        │
│                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📱 UI Layout & Components

### Layout (Desktop View)
```
┌──────────────────────────────────────────────────────────────────┐
│  HEADER: Run ID | Status | Elapsed Time | Actions               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  MAIN CONTENT (3 columns)                                        │
│                                                                  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │  WORKFLOW DAG   │ │   EVIDENCE      │ │    METRICS      │   │
│  │  (React Flow)   │ │   PANEL         │ │  & SCORES       │   │
│  │                 │ │                 │ │                 │   │
│  │  [Agents]       │ │ Claim Extract   │ │ Risk Score      │   │
│  │  Running/Done   │ │ ✅              │ │ ▰▰▰▱▱ 0.05     │   │
│  │  with timings   │ │                 │ │                 │   │
│  │                 │ │ Static Analysis │ │ Verification %  │   │
│  │                 │ │ ✅              │ │ ▰▰▰▰▰ 100%     │   │
│  │  Animated       │ │                 │ │                 │   │
│  │  transitions    │ │ [... more ...]  │ │ Judge Score     │   │
│  │                 │ │                 │ │ 0.95 ⭐        │   │
│  │                 │ │                 │ │                 │   │
│  │                 │ │ [Expand All]    │ │ Timing          │   │
│  │                 │ │                 │ │ Total: 1.8s     │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  FOOTER: Status message | Auto-refresh indicator | Cancel btn   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🎨 Design System

**Color Palette:**
- Primary: #0051BA (DeHalu Blue)
- Success: #10B981 (Emerald)
- Warning: #F59E0B (Amber)
- Error: #EF4444 (Rose)
- Neutral: #F8FAFC → #0F172A (Gray scale)

**Typography:**
- Headers: Inter Bold (24px, 20px, 18px)
- Body: Inter Regular (16px, 14px)
- Code: JetBrains Mono (12px, 11px)

**Animations:**
- Agent state change: 300ms spring
- Evidence expansion: 400ms ease-out
- Progress fill: 1500ms ease-in-out
- Workflow highlight: 200ms pulse

---

## 📊 Complete Frontend Tech Stack

```
Framework:          Next.js 14+ App Router
Language:          TypeScript (strict)
UI Components:     Shadcn/ui + Radix UI
Styling:          Tailwind CSS
Animations:       Framer Motion
Workflow DAG:     React Flow
State Management: Zustand + TanStack Query
API Client:       Generated from OpenAPI
Charting:         Recharts
Icons:            Lucide React
Testing:          Vitest + Cypress
Dev Tools:        Storybook + MSW
Deployment:       Vercel / Docker
```

---

## ✅ Success Metrics

**User Experience:**
- ✅ Complete verification flow < 5 minutes
- ✅ Real-time updates every 2 seconds
- ✅ All 6 agents visualized in DAG
- ✅ Hallucination detection clear (yes/no with score)
- ✅ Mitigation flow transparent (before/after code)

**Performance:**
- ✅ Page load < 3 seconds
- ✅ API calls average < 500ms
- ✅ Smooth 60fps animations
- ✅ Bundle size < 200KB gzipped

**Quality:**
- ✅ Mobile, tablet, desktop responsive
- ✅ WCAG 2.1 AA accessibility
- ✅ 90%+ Lighthouse score
- ✅ Zero console errors

---

## 🚀 Implementation Status

**Status:** PLANNING COMPLETE - READY FOR APPROVAL

**Next Steps:**
1. Review this blueprint
2. Approve tech stack & design approach
3. Begin Phase 1 implementation (MVP)
4. Deploy by end of sprint

---

Generated: 2026-05-03  
Ready for Frontend Team Execution
