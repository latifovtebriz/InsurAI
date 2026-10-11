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

### ADR-002: PostgreSQL 16 with pgvector for Relational and Embedding Storage
- **Context:** InsurAI requires ACID relational guarantees for insurance ledger and policy transactions, alongside semantic vector search over policy wording clauses. Maintaining separate vector databases (e.g. Pinecone, Qdrant) adds operational complexity, dual-write consistency issues, and cross-system latency.
- **Decision:** Standardize on PostgreSQL 16 with the `pgvector` extension. Store domain tables in isolated schemas (`platform`, `claims`, etc.) and vector chunks in `platform.kb_chunks`.
- **Consequences:** Single database for backups, ACID transactions bridging relational policies and vector embeddings, effective-dated relational filtering executed directly in SQL prior to vector cosine distance calculation.

### ADR-003: Declarative State Machine Engine for Domain Lifecycles
- **Context:** Insurance policies, claims, quotes, and invoices must follow strict statutory and contractual lifecycles. Ad-hoc boolean flags or scattered status updates lead to illegal state transitions (e.g., settling an unpaid or closed claim).
- **Decision:** Implement a declarative state machine engine (`StateMachineDefinition`) with explicit transitions, triggers, guards, and hooks. State mutations must pass through the workflow engine; illegal transitions raise `InvalidStateTransitionError` and execute zero database writes.
- **Consequences:** Total auditability of lifecycle mutations, impossible to bypass domain rules, simplified testing.

### ADR-008: Transactional Outbox Pattern for Inter-Module Event Dispatching
- **Context:** When a domain entity changes state (e.g. `ClaimRegistered`, `PolicyIssued`), downstream modules and background workers must be notified. Publishing directly to external message brokers within an active HTTP request risks dual-write inconsistencies if the database commit fails after the message is sent.
- **Decision:** Implement the Transactional Outbox pattern. Domain events are inserted into `platform.outbox_events` within the exact same database transaction as the entity state update. A background dispatcher (`OutboxDispatcher`) polls pending events and delivers them to registered consumers with deduplication via `platform.processed_events`.
- **Consequences:** At-least-once delivery guarantee, zero ghost events on transaction rollback, idempotent consumer processing.

### ADR-009: Clause-Based Semantic Chunking with Date-in-Force Filtering
- **Context:** Standard fixed-token window RAG (e.g., 512 tokens with 50-token overlap) arbitrarily slices legal sentences, destroying legal coherence and clause references. Furthermore, policy wordings change over time across versions. Searching across all versions simultaneously leads to retrieving outdated clauses for modern claims or modern clauses for historical incidents.
- **Decision:** Chunk documents strictly at the numbered clause boundary (`clause_id`). Embed `title + "\n" + text`. Before calculating vector similarity, enforce a strict relational filter in SQL where `product_code == requested` and `effective_from <= incident_date <= effective_to`. Return structured `Citation` objects.
- **Consequences:** Guaranteed preservation of complete legal clauses, zero cross-version leakage, 100% accurate time-travel retrieval.

### ADR-010: Tooling and Quality Stack
- **Context:** The project requires fast dependency resolution, strict typing, linting, formatting, and reproducible environments on Windows.
- **Decision:** Use `uv` for package management, Python 3.12+, FastAPI for REST endpoints, Pydantic v2 for data schemas, `ruff` for linting/formatting, `mypy` for static typing, and `pytest` for testing.
