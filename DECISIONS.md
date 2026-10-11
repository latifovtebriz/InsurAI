# InsurAI Implementation Decisions (ADR Index)

## Architectural Decision Records (ADRs)

| ADR ID | Title | Status | Date |
|---|---|---|---|
| ADR-001 | Modular Monolith with Schema-per-Module Isolation | Accepted | 2026-10-12 |
| ADR-002 | PostgreSQL 16 with pgvector for Relational and Embedding Storage | Accepted | 2026-10-12 |
| ADR-003 | Declarative State Machine Engine for Domain Lifecycles | Accepted | 2026-10-12 |
| ADR-004 | Pure Deterministic Core for Monetary and Calculation Engines | Accepted | 2026-10-12 |
| ADR-005 | Hand-written ReAct Agent Runtime with Pluggable Guardrails | Accepted | 2026-10-12 |
| ADR-006 | Explicit Four-Tier Autonomy Model (L0–L3) with Mandatory Human-in-the-Loop | Accepted | 2026-10-12 |
| ADR-007 | Provider-Agnostic LLMClient with Fake and Record/Replay Clients | Accepted | 2026-10-12 |
| ADR-008 | Transactional Outbox Pattern for Inter-Module Event Dispatching | Accepted | 2026-10-12 |
| ADR-009 | Clause-Based Semantic Chunking with Date-in-Force Filtering | Accepted | 2026-10-12 |
| ADR-010 | Tooling and Quality Stack: Python 3.12+, uv, FastAPI, Pydantic v2, Ruff, Mypy | Accepted | 2026-10-12 |

---

### ADR-001: Modular Monolith with Schema-per-Module Isolation
- **Context:** Insurance domain logic spans multiple bounded contexts (party, product, policy, claims, finance, etc.). Distributed microservices introduce network latency, eventual consistency headaches, and operational complexity. A single unstructured monolith leads to tangled dependencies.
- **Decision:** Build as a single deployable modular monolith in Python/FastAPI. Each bounded context owns a dedicated database schema. No cross-schema foreign keys. Cross-module calls must only use `public.py` interfaces or asynchronous outbox events.
- **Consequences:** Easy local development, zero network overhead between modules, clean domain separation enforced by architecture tests.

### ADR-010: Tooling and Quality Stack
- **Context:** The project requires fast dependency resolution, strict typing, linting, formatting, and reproducible environments on Windows.
- **Decision:** Use `uv` for package management, Python 3.12+, FastAPI for REST endpoints, Pydantic v2 for data schemas, `ruff` for linting/formatting, `mypy` for static typing, and `pytest` for testing.
