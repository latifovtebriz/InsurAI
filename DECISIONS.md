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
| ADR-011 | React 18, Vite, TypeScript Web Console with Human-in-the-Loop Transparency | Accepted | 2026-10-12 |
| ADR-012 | Deterministic Underwriting Rules vs Copilot Boundaries & G2 Numerical Fidelity | Accepted | 2026-10-12 |
| ADR-013 | Balanced Double-Entry General Ledger Constraint & Reinsurance Bordereaux Architecture | Accepted | 2026-10-12 |

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

### ADR-004: Pure Deterministic Core for Monetary and Calculation Engines
- **Context:** Insurance calculations (premiums, pro-rata cancellations, deductible subtractions, depreciation schedules, salvage deductions, and total loss thresholds) must be mathematically exact, auditable, and conform to statutory accounting standards. Floating-point arithmetic introduces IEEE-754 rounding drift. LLMs are notoriously unreliable for arithmetic.
- **Decision:** All monetary amounts, premiums, deductibles, depreciation percentages, and refunds are calculated using Python's `Decimal` with explicit rounding modes (`ROUND_HALF_UP`). Zero LLM involvement in arithmetic. LLM agents must call deterministic calculator tools. Financial invariants are verified using property-based testing (`hypothesis`).
- **Consequences:** 100% reproducible math, zero rounding drift, strict audit compliance.

### ADR-005: Hand-written ReAct Agent Runtime with Pluggable Guardrails
- **Context:** High-level agent frameworks (LangChain, CrewAI, AutoGen) bring heavyweight dependencies, opaque abstractions, rapid breaking changes, and unpredictable hidden prompt chaining. Enterprise insurance automation requires complete control over the reasoning loop, step budgets, loop detection, and defense-in-depth safety guardrails.
- **Decision:** Build a hand-written ReAct loop (`AgentLoop`) in pure Python. Explicit step counting, deterministic loop detector (stopping after 3 identical tool calls), step-level database tracing (`AgentRun`, `AgentStep`), and an interceptor pipeline (`GuardrailPipeline`) executing rules G1 through G10 prior to any final decision.
- **Consequences:** Zero black-box dependencies, predictable token usage, deterministic fail-safes, complete auditability for insurance regulators.

### ADR-006: Explicit Four-Tier Autonomy Model (L0–L3) with Mandatory Human-in-the-Loop
- **Context:** Fully autonomous AI in insurance carries regulatory, financial, and reputational risk. Different actions carry vastly different stakes—from answering a policy question to denying a claim or paying out $50,000.
- **Decision:** Implement an explicit 4-tier autonomy model:
  - **L0 (Assisted / Read-only):** Retrieval, search, policy wording lookups.
  - **L1 (Propose & Review):** Draft claims triage, initial underwriting assessment, quotation drafts. Requires human adjuster/underwriter sign-off.
  - **L2 (Conditional Autonomy):** Low-value, high-confidence, zero-risk-flag claims (e.g., straight-through processing <= 1,000 AZN). If confidence < 0.70 or any flag is raised, immediately downgraded to L1.
  - **L3 (Autonomous Execution):** Strictly bounded actions (e.g. simulated straight-through settlement) where all deterministic checks, coverage active tests, and fraud scans pass. Claim rejections are hardcoded to never execute at L3 (G3 guard: denials always require human sign-off).
- **Consequences:** Compliant with EU AI Act and insurance regulatory standards; transparent control boundaries; fail-safe human fallback.

### ADR-007: Provider-Agnostic LLMClient with Fake and Record/Replay Clients
- **Context:** Developing and testing LLM-powered applications against live third-party cloud APIs (such as Gemini, OpenAI, Anthropic) requires network access, valid API keys, incurs monetary costs, and introduces non-deterministic test failures due to API latency or rate limits.
- **Decision:** Abstract the LLM layer behind a protocol `LLMClient`. Provide a `FakeLLMClient` with regex-heuristic extraction and pre-canned scripted responses for fully offline local testing. Provide `RecordReplayLLMClient` for recording live golden responses to disk (JSON) and replaying them deterministically in CI. Implement `GeminiLLMClient` for live execution when `LLM_API_KEY` is present.
- **Consequences:** Fast, completely offline unit and integration tests; zero CI cost; 100% reproducible CI test suites.

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

### ADR-011: React 18, Vite, TypeScript Web Console with Human-in-the-Loop Transparency
- **Context:** An AI copilot in insurance claims and underwriting cannot be an opaque black box. Adjusters and underwriters require full visibility into agent confidence, exact wording citations, deterministic payout breakdowns, fraud risk alerts, and execution traces (thoughts and tool calls) before confirming actions.
- **Decision:** Build a single-page application using React 18, Vite, TypeScript, and TailwindCSS. The console enforces persona-based quick logins, presents prominent uncertainty disclosures whenever confidence is less than 1.0 or flags exist, provides 4 golden demo scenario presets, and requires mandatory written rationale for any adjuster override.
- **Consequences:** Low latency UI (<50ms state updates), explainable AI for claims adjusters, seamless human oversight, and ready-to-demo golden journeys.

### ADR-012: Deterministic Underwriting Rules vs Copilot Boundaries & G2 Numerical Fidelity
- **Context:** Letting LLMs directly calculate insurance quotes or evaluate underwriting risk thresholds leads to price hallucinations, unvetted exposures, and statutory non-compliance.
- **Decision:** Strictly separate deterministic rule evaluation from agentic assistance. For sales (Agent A1), the LLM parses natural language intent, clarifies missing parameters, and explains quotes, but all numerical premiums are calculated by pure Python rating functions (Guardrail G2). For underwriting (Agent A2), deterministic rule hits (UW-01 through UW-05) and authority limit tiers are evaluated first; Copilot A2 summarizes risk profiles and retrieves guidelines, but cannot auto-approve beyond authority tiers or execute terminal declines without human underwriter sign-off (Guardrail G3).
- **Consequences:** 100% numerical fidelity in quotations, zero risk of autonomous unauthorized risk acceptance, fully auditable underwriting governance.

### ADR-013: Balanced Double-Entry General Ledger Constraint & Reinsurance Bordereaux Architecture
- **Context:** Financial movements in core insurance (premium receivables, cash collection, loss reserves, claim payouts, commissions, and reinsurance cessions) must maintain absolute accounting integrity. Single-entry ledgers or ad-hoc balance columns allow rounding drift and hidden imbalances. Furthermore, treaty reinsurance requires tracking cessions and recoveries down to the cent for reinsurer bordereaux reporting.
- **Decision:** Implement a strict double-entry General Ledger engine (`GeneralLedgerTransaction`, `GeneralLedgerEntry`). Every financial operation must post matching debits and credits; the invariant `|sum(debit) - sum(credit)| == 0.00` is enforced prior to every commit, raising `LedgerImbalanceError` on any mismatch. Reinsurance treaties (Quota Share and Excess of Loss) automatically calculate ceded premiums and recoveries, posting balanced contra accounts and generating periodic bordereau statements. Expiring policies are reviewed at T-60 by Renewal Service and Agent A7, with statutory 30-day notice deadlines strictly monitored and non-renewals requiring underwriter sign-off (L2).
- **Consequences:** Zero financial imbalance drift across all accounts, full auditability, automated treaty bordereaux generation, and compliance with statutory policy non-renewal notification mandates.

### ADR-014: Guardrail G8 Neutral Language, Non-Clearance Invariant for Compliance (A8), and Verification Gated Customer Service (A6)
- **Context:** SIU fraud investigations, AML sanctions screening, and customer self-service present significant legal liabilities. Accusatory AI statements in claim files ("fraudster", "staged accident") create defamation liability in court or ombudsman hearings. In AML compliance, automated clearance of sanctions matches violates international financial regulations. In customer service, unauthenticated bots risk leaking policyholder PII.
- **Decision:**
  1. **Guardrail G8 & G9 in SIU:** Agent A5 synthesizes dossiers using objective neutral phrasing (`sanitize_neutral_language`), replacing accusatory terms with objective descriptors (`potential inconsistency`, `unwitnessed incident pattern`). Guardrail G9 blocks demographic variables (`gender`, `race`, `postal_code`) from fraud scoring by raising `FairnessViolationError`.
  2. **Regulatory Non-Clearance Invariant (Agent A8):** Agent A8 provides comparative match explanations and draft SARs to compliance officers, but is programmatically prohibited from auto-clearing hits (`attempt_auto_clear()` raises `PermissionError`). Only an authenticated Compliance Officer can adjudicate alerts.
  3. **Identity Verification Gate (Agent A6):** Unauthenticated users access public FAQs only. Any request for policy or claim data triggers `PROMPT_AUTHENTICATION` with zero data exposure.
  4. **Deterministic Pro-Rata Math (Agent A3):** Mid-term endorsements (P06) calculate additional or return premiums down to the exact day using deterministic Decimal math under Level 2 underwriter governance.
- **Consequences:** Immunity from legal defamation claims, 100% adherence to regulatory AML non-clearance rules, zero customer PII leakage, and verified pro-rata financial adjustments.

