# InsurAI Engineering Interview Pack & Architecture Notes

## 1. The InsurAI Architectural Story

### The Problem
Insurance core platforms are notoriously rigid legacy systems (often written in COBOL or 20-year-old monoliths). Modern attempts to modernize often fall into two traps:
1. **Unconstrained GenAI hype**: Connecting an LLM directly to core APIs without mathematical bounds, leading to hallucinated claims payouts, prompt injection exploits, and regulatory non-compliance.
2. **Over-engineered distributed microservices**: Splitting a greenfield domain into 15 microservices on Day 1, incurring distributed transaction nightmares, eventual consistency failures in accounting, and massive operational overhead.

### The InsurAI Solution: A Disciplined Modular Monolith
InsurAI is designed as an enterprise Property & Casualty (P&C) core platform operating on three architectural pillars:
1. **Modular Monolith with Enforced AST Boundaries**: 12 domain modules (`platform`, `party`, `product`, `policy`, `sales`, `underwriting`, `claims`, `finance`, `fraud`, `compliance`, `service`, `reinsurance`). Inter-module communication is strictly restricted to top-level `public.py` interfaces, verified via AST-based architecture tests.
2. **Deterministic Calculation vs. AI Reasoning Partitioning**: LLMs are utilized exclusively for qualitative reasoning (summarizing damage, extracting FNOL fields, retrieving relevant policy clauses). All financial figures, prorated dates, premiums, reserves, and disbursements are executed by deterministic Python engines using exact `Decimal` arithmetic.
3. **Guaranteed Consistency via Transactional Outbox & Double-Entry Accounting**: State mutations write outbox domain events in the same database transaction. Financial operations enforce a mathematical double-entry balance invariant ($\Delta = |Debits - Credits| == 0.00$ AZN) at all times.

---

## 2. Ten Tough Interview Questions with Honest Answers

### Q1: Why build a custom ReAct agent runtime instead of using LangChain, CrewAI, or AutoGen?
> **Answer**: Frameworks like LangChain and CrewAI introduce massive dependency graphs, breaking changes across minor versions, and opaque execution loops that are difficult to trace and audit in regulated financial environments. By implementing a hand-written ReAct loop (~200 lines in `app.modules.platform.runtime.loop`), we maintain complete control over:
> 1. Deterministic step-level database tracing (`AgentStep` table recording exact latency and token usage).
> 2. Hard budget constraints (`max_steps=5` and loop detection terminating 3 identical consecutive tool calls).
> 3. Pluggable guardrail interceptors (G1–G10) that can inspect and override recommendations before tool execution.

### Q2: How do you guarantee an autonomous LLM won't approve a \$100,000 fraudulent claim?
> **Answer**: Through three independent defensive layers:
> 1. **Autonomy Tiers**: Claims over 2,500 AZN or any property fire claims are classified as **Autonomy Level 2 (Human-in-the-Loop)**; the agent can only prepare a draft recommendation, and disbursement is impossible without an adjuster's cryptographic sign-off.
> 2. **Deterministic Payout Engine**: Even for Level 1 straight-through claims, the LLM **does not calculate the payout**. The deterministic `PayoutCalculator` computes:
>    $$\text{Payable} = \min(\text{Claimed}, \text{Sum Insured}) - \text{Deductible} - \text{Depreciation}$$
> 3. **Guardrail G2**: If the agent's proposed payable amount differs by more than 0.01 AZN from the deterministic calculation, the run is immediately rejected and downgraded to human review.

### Q3: How do you prevent hallucinations when the LLM interprets policy wording?
> **Answer**: We enforce a **Mandatory Grounding Invariant (Guardrail G1)**:
> 1. The agent must invoke the `search_policy_wording` tool during its active session.
> 2. In `search_policy_wording`, metadata filtering by **'Date in Force' at incident date** occurs *before* vector cosine similarity ranking.
> 3. Guardrail G1 inspects all clause IDs cited in the agent's final decision. If any clause was not physically retrieved during that specific session, G1 fails and downgrades the decision to `needs_human_review`.

### Q4: How do you handle accounting integrity across asynchronous event processing?
> **Answer**: We implement a **Transactional Outbox pattern** coupled with a double-entry general ledger. When a business event occurs (e.g., policy bound), the database transaction writes both the entity state and an outbox event in `platform.outbox_events` atomically. A background worker polls the outbox using `FOR UPDATE SKIP LOCKED`, guaranteeing that events are published at least once. Idempotent consumer tables (`platform.processed_events`) deduplicate events. All financial postings enforce a zero-difference invariant: $|\sum \text{Debits} - \sum \text{Credits}| == 0.00$ AZN.

### Q5: What happens if the LLM provider experiences downtime, throttling, or API errors?
> **Answer**: The agent loop is wrapped in a fail-safe exception handler. Any network timeout, HTTP 429/500 error, or malformed JSON output is caught cleanly. The agent record is marked as `status="needs_human_review"`, the error message is recorded in the step trace, and the business workflow routes to human queues. The application process never crashes, and partial database mutations roll back cleanly.

### Q6: How do you defend against prompt injection inside First Notice of Loss (FNOL) statements?
> **Answer**: In P&C insurance, FNOL descriptions are untrusted user inputs. We mitigate this through:
> 1. **Structural Delimiters**: User text is strictly isolated inside `<user_statement>` blocks within prompts.
> 2. **Guardrail G7 (Prompt Injection Heuristic Scan)**: Raw text inputs are scanned against known adversarial patterns (`ignore previous`, `system override`, `approve this claim`). If matched, G7 automatically downgrades the claim to human review.
> 3. **Action Whitelisting**: The agent cannot execute arbitrary shell or SQL commands; tool execution is strictly restricted to schema-validated functions in `ToolRegistry`.

### Q7: How is algorithmic fairness ensured under EU AI Act and insurance regulations?
> **Answer**: Under EU AI Act Annex III and Central Bank of Azerbaijan guidelines, automated risk assessment must be fair and non-discriminatory. We enforce **Protected Attribute Blindness (Guardrail G9)**:
> 1. Demographic variables (gender, age outside license validity, ethnicity, religion, marital status) are quarantined and strictly excluded from rating multipliers, underwriting risk scores, and fraud anomaly detection algorithms.
> 2. Motor and Property premiums are computed solely on objective, actuarially validated variables: replacement values, cubic capacity, parking location, construction type, fire prevention systems, and deductible amounts.

### Q8: How does the platform handle mid-term endorsements and prorated premium calculations?
> **Answer**: The `EndorsementEngine` implements statutory **daily pro-rata calculations**:
> 1. It calculates elapsed and remaining days between effective date and expiry:
>    $$\text{Remaining Factor} = \frac{\text{Expiry Date} - \text{Endorsement Date}}{\text{Expiry Date} - \text{Effective Date}}$$
> 2. The delta premium (positive for vehicle/sum insured upgrades, negative for reductions) is computed to the cent.
> 3. An invoice (or refund disbursement) is generated and posted to the General Ledger with offsetting accounts receivable/payable entries.

### Q9: Why maintain dual-database compatibility (PostgreSQL/pgvector and SQLite)?
> **Answer**: Developer velocity and local environment independence. In local or offline developer environments where a PostgreSQL daemon is not installed, running integration tests or seeding demo databases would fail or block indefinitely on TCP timeouts. By utilizing SQLAlchemy's `schema_translate_map` and a lightweight socket connectivity probe, the platform runs synchronously against in-memory or file-based SQLite while supporting enterprise PostgreSQL with `pgvector` in staging and production.

### Q10: What is your testing strategy and how is code boundary hygiene enforced?
> **Answer**: Testing is organized into four distinct tiers:
> 1. **Unit Tests (115+ tests)**: Testing individual domain engines, rating algorithms, guardrails, and tools in sub-second execution.
> 2. **Architecture AST Tests**: Parsing Python abstract syntax trees to guarantee that no module imports private internal files from another module (`test_module_boundaries.py`).
> 3. **Chaos & Robustness Tests**: Validating system resilience against LLM timeouts, malformed responses, DB rollbacks, and 10MB payload attacks (`test_chaos_and_robustness.py`).
> 4. **End-to-End Integration Tests**: 12-step full lifecycle golden journey validating the complete flow from Quote to Policy to Claims, SIU Fraud, Settlement, Reinsurance Recovery, and Renewal.

---

## 3. Five Hardest Engineering Problems Solved & Technical Rationale

### 1. Mathematical General Ledger Invariant ($\Delta = 0.00$ AZN) Across 7 Transaction Types
- **Challenge**: Across diverse financial events (invoicing, customer payment, reserve establishment, claim settlement, broker commission accrual, reinsurance cession, reinsurance recovery), a single cent rounding discrepancy will violate double-entry accounting integrity.
- **Solution**: Developed a centralized `LedgerEngine` that validates $|\sum \text{Debits} - \sum \text{Credits}| == 0.00$ prior to any database commit. All monetary amounts use Python `Decimal` quantized to 2 decimal places with `ROUND_HALF_UP`.

### 2. Zero-Leak Pre-Push Secret and Hygiene Scanner
- **Challenge**: LLM-assisted workflows frequently risk accidental commitment of local `.env` files, API keys, or private keys to public repositories.
- **Solution**: Implemented `scripts/secret_scanner.py`, an automated scanner that inspects git-tracked files against entropy heuristics, private key regexes, and `.env` ignore rules. Integrated as a non-bypassable pre-push hook and CI step.

### 3. Pluggable Guardrail Interception Pipeline (G1–G10)
- **Challenge**: Balancing LLM flexibility with strict insurance business rules without polluting agent prompts with dozens of edge-case instructions.
- **Solution**: Implemented a standalone, deterministic `GuardrailPipeline` that intercepts terminal agent tool submissions. Guardrails evaluate grounded citations (G1), math invariants (G2), coverage consistency (G3), ambiguity (G4), mandatory tools (G5), confidence thresholds (G6), prompt injection (G7), neutral language (G8), fairness blindness (G9), and non-negative payouts (G10).

### 4. Fast-Fallback Socket Probing for Dual Database Support
- **Challenge**: On Windows development machines lacking a running PostgreSQL service, SQLAlchemy connection attempts to localhost block for 30–60 seconds on OS TCP timeouts before failing.
- **Solution**: Engineered a non-blocking 0.5-second socket probe (`is_postgres_running()`) in CLI scripts and test runners. If unreachable, the system instantly switches to SQLite with `schema_translate_map`, avoiding developer friction.

### 5. Effective-Dated Policy Wording Invariant
- **Challenge**: In insurance claims, a policy wording version updated in 2026 cannot be applied to an incident that occurred under a 2024 policy contract.
- **Solution**: Enforced a mandatory two-stage retrieval in `KnowledgeService`: SQL metadata filtering by `effective_from <= incident_date <= effective_to` occurs strictly prior to vector similarity ranking.

---

## 4. Honest Limitations & What Would Change in Production

1. **Synthetic Data**: All policyholders, vehicles, addresses, claims, and financial accounts are deterministically generated synthetic fixtures. In production, this would integrate with core enterprise data warehouses (SAP, Guidewire, Duck Creek) and external identity providers (ASAN Imza / Digital ID in Azerbaijan).
2. **Offline Fake LLM vs Live Production Model**: Development and offline test suites run against `FakeLLMClient` and deterministic fake embeddings (768 dimensions) to ensure zero API key dependencies and zero external cost. In production, the gateway switches to Google Gemini 1.5 Pro / Flash via vertex AI with semantic caching.
3. **Queue Infrastructure**: The current outbox worker runs as a database-backed skip-locked worker. In high-volume production (> 10,000 transactions/sec), the outbox publisher would stream to Apache Kafka or AWS SQS with distributed consumer groups.
4. **Multimodal Computer Vision**: Currently, damage severity is extracted from textual repair estimates and surveyor reports. Production would integrate computer vision models (e.g. Gemini Vision) to inspect damaged vehicle photographs for fraud detection (e.g. metadata tampering, rust on fresh collision panels).

---

## 5. Resume Bullets with Real Metrics (Appendix G.12 Alignment)

- **Enterprise P&C Platform Architecture**: Architected and delivered an autonomous Property & Casualty insurance core platform featuring 12 isolated domain modules, 8 specialized AI agents (A1–A8), and a real-time React/Vite operator console managing policy, claims, and underwriting lifecycles.
- **Deterministic AI Guardrail System**: Engineered a 10-point deterministic safety pipeline (G1–G10) and custom ReAct agent runtime with token budgets, loop detection, and prompt injection defenses; eliminated hallucinated payouts and enforced 100% grounded policy citations.
- **Double-Entry General Ledger & Reinsurance Engine**: Implemented an automated financial accounting engine enforcing a strict double-entry balance invariant ($\Delta = 0.00$ AZN) across premium invoices, settlements, and quota-share reinsurance treaties spanning 13 chart-of-accounts.
- **Rigorous Verification & CI/CD**: Established a comprehensive test suite (120+ unit, integration, and AST boundary tests) achieving 100% clean mypy/ruff compliance, automated SAST vulnerability scanning, and sub-10s turnkey demo data seeding.
