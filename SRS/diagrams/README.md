# DeHalu high-level design diagrams

Open **DeHalu-High-Level-Design.drawio** in draw.io / diagrams.net using **File → Open from → Device**. It contains two editable pages:

1. **System Architecture** — the browser UI, FastAPI API, PostgreSQL queue and event journal, background worker, local Ollama service, external judge providers, and optional package registries.
2. **Verification & Repair Flow** — the implementation's stage order, independent judge calls, CoVe before policy, clarification, terminal outcomes, and bounded repair loop.

The SVG files provide standalone previews for reports and presentations. The `.drawio` file uses native shapes, text, and connectors; it is not a flattened image. The design uses a system-design interview presentation with service boundaries, a database cylinder, labeled request/data paths, and a separate processing-flow view.

## Alignment with the implementation

Review date: 6 October 2026. Source: `SRS/High-Level-Design.md` and the current source tree. The core verification and mitigation architecture follows the design. The diagrams include implementation details and qualifications absent from the original phase sketch:

| Design area | Source evidence | Implementation detail |
| --- | --- | --- |
| Client and API | `frontend/lib/api.ts`, `backend/src/dehalu/api/routes.py` | Browser requests go directly to FastAPI. REST supports run history, evidence, cancellation, clarification, and JSON export; SSE replays persisted events. |
| Asynchronous processing | `backend/src/dehalu/worker.py`, `backend/src/dehalu/state/workflow.py` | A separate worker claims PostgreSQL jobs with `SKIP LOCKED`, maintains leases/heartbeats, and executes the pipeline. PostgreSQL also stores the event journal. |
| Intake and local generation | `backend/src/dehalu/services/pipeline.py`, `backend/src/dehalu/providers/llm.py` | Intake combines deterministic inference with structured local-model fallback. Missing blocking context requests clarification. Ollama streams generation and repair. |
| Claims and static checks | `backend/src/dehalu/verification/{claims,adapters,static_analysis,symbols}.py` | Structural extraction is supplemented by structured explanation claims. Parsing, Semgrep scanning, and symbol/API validation run sequentially, although the original sketch depicts separate branches. Coverage is recorded. |
| Package/API evidence | `backend/src/dehalu/verification/catalogs.py` | Small local catalogs provide evidence; incomplete catalog coverage remains uncertain. PyPI, npm, and crates.io metadata lookups are optional and disabled by default. |
| Quantitative metrics | `backend/src/dehalu/verification/metrics.py` | MiHN counts unsupported claims; the implemented MaHR includes unsupported **and uncertain** claims. TR-S, severity, uncertainty, and a weighted risk score are computed. Live Ollama responses currently mark entropy and log probabilities unavailable. |
| Judge pool and consensus | `backend/src/dehalu/providers/llm.py`, `backend/src/dehalu/verification/policy.py` | Gemini, Groq, and Mistral calls run independently in parallel with assigned roles and a shared rubric. Consensus aggregates valid results; missing/failed judges affect policy. Provider model names are configurable. |
| CoVe and policy | `backend/src/dehalu/services/pipeline.py`, `backend/src/dehalu/verification/{cove,policy}.py` | CoVe runs before **every** policy decision, rather than solely inside mitigation. Metrics are recalculated after CoVe. Blocking static/claim evidence or majority semantic failure triggers repair/reject; incomplete evidence can trigger warn. |
| Repair and final output | `backend/src/dehalu/services/pipeline.py` | Evidence constrains repair prompts. Retry limits and repeated code hashes stop repair. Every repaired artifact re-enters claim extraction and receives all verification stages. Accept/warn completes a run; reject retains the failed evidence. |
| Persistence | `backend/src/dehalu/state/{models,repository}.py`, `docker-compose.yml` | PostgreSQL 16 stores sessions, runs, generated outputs, evidence, jobs, and events through SQLAlchemy. Alembic manages schema migrations. |

This is a source-level architecture review, not a live deployment or provider-readiness test. Generated code is analyzed without execution. Semantic judgments and partial API catalogs do not guarantee runtime correctness. The policy consumes metric fields and TR-S; the aggregate risk score is reported rather than used as a standalone decision threshold.

## Validation

The draw.io and SVG files were parsed as XML. Checks verified two diagram pages, unique cell IDs, valid connector endpoints, and page bounds. SVG previews share the same component geometry and routing as the editable diagrams.
