# Mitigation Pipeline - High Level Design

```
User Prompt
   │
   ▼
Normalization + Enhancement
   │
   ▼
Generate Code (Generator Agent)
   │
   ├───────┐
   │       ▼
   │  Reviewer Agent (optional quick pass)
   │       │
   └───────┘
       │
       ▼
Verification Pipeline
   ├── claims / judge / static / sandbox → Pass?
   │
   ├── YES → return code + report
   │
   └── NO  → Build FailureContext
              │
              ▼
         Fixer Agent (with MCP tools)
              │
              ▼
         Fixed Code
              │
              └── Loop back to Verification (max N attempts)
```