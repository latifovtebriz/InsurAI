# InsurAI: Architecture and Processes

## Part A: System Architecture and Modular Domain Design

### 1. Architectural Vision and Core Principles

InsurAI is designed as an enterprise-grade, agent-augmented core insurance system for Property & Casualty (P&C). It provides an auditable, resilient architecture where autonomous AI agents collaborate with licensed human underwriters, adjusters, and customer service agents.

#### 1.1 Guiding Principles

1. **Deterministic Core for Finance and Law:** Premium rating, pro-rata cancellations, deductible deductions, payout allocations, statutory deadlines, and accounting entries are executed exclusively by pure, deterministic Python code using `Decimal`. No LLM generates financial amounts or statutory deadlines independently.
2. **Modular Monolith with Schema-per-Module Isolation:** To prevent distributed transaction failures while enforcing strict Domain-Driven Design (DDD) boundaries, all modules live in a single deployable repository but own isolated PostgreSQL schemas (`platform`, `party`, `product`, `policy`, `claims`, `sales`, `underwriting`, `finance`, `fraud`, `compliance`, `service`, `reinsurance`).
3. **Strict Interface Encapsulation (`public.py`):** Cross-module synchronous communication is strictly restricted to calling functions exposed via each module's `public.py`. Direct imports of internal models, repositories, or services from another module are prevented by automated architecture tests (`import-linter`).
4. **No Cross-Schema Foreign Keys:** Referential integrity across bounded contexts is maintained logically through immutable IDs and domain events, never through database foreign key constraints between different schemas.
5. **Transactional Outbox for Event-Driven Coupling:** Asynchronous events (e.g., `ClaimRegistered`, `PolicyIssued`, `ProductVersionPublished`) are written to a database outbox table in the same atomic transaction as the state change. A background dispatcher forwards events idempotently.
6. **Defense-in-Depth Guardrail Pipeline:** All agent outputs must pass through automated, deterministic guardrail interceptors (G1–G10) verifying grounding, citations, mathematical equality, and prompt injection indicators before they reach a human or database.
7. **Complete Auditability and Step Tracing:** Every agent execution (`agent_runs`), intermediate reasoning and tool call (`agent_steps`), guardrail validation, and human override is immutably logged.

---

### 2. Bounded Contexts and Module Structure

The platform is structured into the following bounded contexts:

| Module Schema | Responsibilities | Core Entities |
|---|---|---|
| `platform` | Shared technical kernel: RBAC, audit log, workflow state machines, outbox, job runner, rules engine, vector store (`kb_chunks`), agent runtime, evaluation harness. | `User`, `Role`, `AuditLog`, `OutboxEvent`, `Job`, `BusinessRule`, `KBChunk`, `AgentRun`, `AgentStep` |
| `party` | Customer and subject-matter data: natural persons, legal entities, vehicles, properties, intermediaries. | `Party`, `Individual`, `Organization`, `Vehicle`, `Property`, `Broker` |
| `product` | Product catalogs, versioning, coverage definitions, rating tables, numbered policy wording clauses (Clauses A through F). | `Product`, `ProductVersion`, `Coverage`, `TariffTable`, `WordingClause` |
| `policy` | Policy administration: issuance, policy lifecycle, endorsements, pro-rata cancellations, documents. | `Policy`, `PolicyVersion`, `Endorsement`, `Certificate` |
| `sales` | Lead generation, quote intake, quote calculation, bind requests. | `Lead`, `Quote`, `QuoteOption` |
| `underwriting` | Automated rule evaluation, referral queues, authority limits, underwriting decisions. | `UnderwritingCase`, `RuleHit`, `UnderwriterDecision` |
| `claims` | First Notice of Loss (FNOL), coverage validation, reserve management, damage assessment, payout calculation, claims workflow. | `Claim`, `ClaimDocument`, `ClaimReserve`, `ClaimPayout`, `AdjusterDecision` |
| `finance` | Installment schedules, premium invoicing, payment allocation, balanced double-entry ledger, disbursements. | `Invoice`, `Installment`, `Payment`, `LedgerAccount`, `LedgerEntry` |
| `fraud` | Rule-based fraud indicators, anomaly scoring, Special Investigation Unit (SIU) cases. | `FraudSignal`, `SIUCase`, `InvestigationNote` |
| `compliance` | KYC verification, sanction list screening (fuzzy matching), AML monitoring, regulatory reports. | `ScreeningCase`, `WatchlistEntry`, `ComplianceAlert` |
| `service` | Customer inquiries, authentication verification, complaint handling, SLA timers. | `Inquiry`, `Complaint`, `ServiceTicket` |
| `reinsurance` | Proportional and excess-of-loss treaties, risk cessions, large-loss recoveries, bordereaux. | `ReinsuranceTreaty`, `Cession`, `Bordereau` |

---

### 3. Detailed Architecture Specifications

#### 3.10 Domain Entities and Relationships

- **Party Context:**
  - `Party`: Base entity with party type (`individual` or `organization`), tax ID / FIN, email, phone, synthetic address.
  - `Vehicle`: VIN, registration number, make, model, manufacture year, engine capacity, market value.
  - `Property`: Cadastral code, address, build year, construction type, floor area, estimated value.
- **Product Context:**
  - `Product`: Code (`MOTOR_OD`, `MOTOR_TPL`, `HOME`), name, active flag.
  - `ProductVersion`: Effective date range (`effective_from`, `effective_to`), status (`draft`, `published`, `archived`), version integer. Requires four-eyes publication.
  - `WordingClause`: Associated with `ProductVersion`, structured under Section 3.3 of the master plan (Clauses A to F), containing `clause_id`, `section`, `title`, and `text`.
- **Policy Context:**
  - `Policy`: `policy_number`, `party_id`, `product_code`, `product_version_id`, `status`, `start_date`, `end_date`, `sum_insured`, `deductible`, `total_premium`.
  - State transitions: `draft` -> `quoted` -> `underwriting_review` -> `bound` -> `pending_payment` -> `active` -> `expired` / `cancelled` / `renewed`.
- **Claims Context:**
  - `Claim`: `claim_number`, `policy_id`, `incident_date`, `notification_date`, `status`, `claimed_amount`, `estimated_reserve`, `approved_payout`, `deductible_applied`.
  - Transitions: `fnol_received` -> `registered` -> `triage_in_progress` -> `awaiting_review` -> `approved` / `rejected` -> `settled` -> `closed`.

#### 3.17 Repository Directory Structure

```text
InsurAI/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application entrypoint
│   │   ├── config.py                   # Pydantic Settings
│   │   ├── api/                        # API route controllers
│   │   ├── modules/                    # Bounded context modules
│   │   │   ├── platform/               # Shared kernel: outbox, rbac, audit, agent runtime
│   │   │   ├── party/                  # party/vehicle/property
│   │   │   ├── product/                # products, versions, clauses
│   │   │   ├── policy/                 # policy admin, rating, cancellations
│   │   │   ├── claims/                 # claims intake, payout engine, A4 agent
│   │   │   ├── sales/                  # leads, quotes, A1 agent
│   │   │   ├── underwriting/           # rule engine, A2 agent
│   │   │   ├── finance/                # invoices, ledger, payments
│   │   │   ├── fraud/                  # fraud signals, SIU, A5 agent
│   │   │   ├── compliance/             # sanctions, KYC, A8 agent
│   │   │   ├── service/                # complaints, servicing, A3 & A6 agents
│   │   │   └── reinsurance/            # treaties, cessions
│   │   └── shared/                     # Pure types and utilities (no business rules)
│   ├── alembic/                        # Database migration scripts
│   ├── tests/                          # Unit, integration, and architecture tests
│   │   ├── unit/
│   │   ├── integration/
│   │   └── architecture/               # Module isolation tests (import-linter)
├── frontend/                           # React + TypeScript + Vite console
├── data/
│   └── synthetic/                      # Seed generators and synthetic datasets
├── evals/                              # LLM evaluation harness, benchmarks, reports
├── docs/                               # Architecture, master plan, ADRs, and KB
└── scripts/                            # Dev, database, and test utilities
```

---


## Part B: Business Processes (P01 through P13)

### P01: Lead Intake & Qualification
Captures prospective customer and asset information across digital channels. Checks basic eligibility (age, territory, vehicle category) and creates a qualified lead.

### P02: Quote Generation & Breakdown (Sales)
- **Input:** Party facts, asset details (vehicle/property), requested coverages, deductible options.
- **Engine:** Deterministic rating engine calculates base rate, applies vehicle age coefficient, driver experience factor, bonus-malus coefficient, taxes, and fees.
- **Output:** Itemized quote breakdown with total premium and installment schedule options. Valid for 30 days.

### P03: Underwriting Referral, Evaluation & Authority Limits
- **Trigger:** Automatic referral triggers (e.g. vehicle value $> 100,000$ AZN, driver age $< 21$, prior claim history $> 2$ claims, non-standard property construction).
- **Process:** Underwriting rule engine flags issues. Senior underwriter reviews case via Underwriting Copilot (A2).
- **Rule:** Rejections and coverage restrictions require mandatory human sign-off; authority matrix enforces monetary limits.

### P04: Policy Issuance, Pre-Bind Checks & Document Generation
- **Trigger:** Bind request upon customer acceptance and underwriting approval.
- **Process:** Freezes active product version; verifies party KYC status; generates unique policy number; computes payment schedule; moves status to `pending_payment` (or `active` if payment verified); issues PDF certificate of insurance.
- **Event:** `PolicyIssued` published to transactional outbox.

### P05: Premium Invoicing & Payment Allocation
- **Process:** Generates invoices per installment schedule. Ingests bank payments / payment gateway webhooks. Matches payment against invoice reference. Moves policy to `active`.
- **Dunning:** Automatically flags overdue installments at T+7 and T+14 days; triggers cancellation notice at T+30 days.

### P06: Policy Servicing, Endorsements, Pro-Rata Cancellation & Refunds
- **Mid-Term Adjustments (Endorsements):** Adding driver, changing registration number, modifying sum insured. Recalculates remaining period premium.
- **Cancellation:**
  - Computes unearned premium via strict daily pro-rata formula:
    $$\text{Refund} = \text{Paid Premium} \times \frac{\text{Days Remaining}}{\text{Total Policy Period}} - \text{Admin Fee}$$
  - Refund cannot exceed total paid premium. Approval workflow required for refunds $> 500$ AZN.

### P07: Renewal Review, Re-rating & Timely Notice Deadlines
- **Trigger:** Automated job runs 60 days before policy expiration (T-60).
- **Process:** Evaluates claim history during policy term; re-rates policy under current active tariff; checks non-renewal notice deadlines (statutory 30-day notice).
- **Agent A7 (Renewal Advisor):** Drafts personalized renewal proposal or non-renewal alert for underwriter review.

### P08: Claims Lifecycle: FNOL Intake, Coverage Verification, Payout Calculation & Settlement
The flagship end-to-end claim handling journey (Motor Own Damage - Kasko):
1. **FNOL Intake:** Customer submits claim statement, incident date, damage description, estimated claim amount, and document texts/photos.
2. **Extraction:** LLM extracts structured `ExtractedClaim` (policy number, incident date, incident type, stated driver, alcohol/license flags).
3. **Coverage Verification:** Checks policy status on incident date; verifies premium payment status; retrieves active policy wording clauses via knowledge base (RAG).
4. **Fraud & Risk Screening:** Invokes rule-based fraud signals (`get_fraud_signals`).
5. **Payout Calculation:** Pure Python engine applies deductible, depreciation rates, and checks constructive total loss threshold ($\ge 70\%$).
6. **Triage Recommendation (A4):** Produces structured `ClaimRecommendation` with cited clauses, evidence, risk flags, and breakdown.
7. **Guardrail Interception:** Interceptors G1–G7 evaluate recommendation; failures downgrade to `needs_human_review`.
8. **Adjuster Decision:** Adjuster confirms or overrides decision in console with mandatory justification comment.
9. **Event:** `ClaimSettled` published to outbox.

### P09: Fraud Detection, SIU Escalation & Scoring
- **Process:** Calculates transparent rule-based risk score from signals (early claim within 14 days of bind, repeated claims within 180 days, mismatched driver names, high claimed amount, police report absence).
- **Routing:** High-score claims ($> 75$) or suspected staged accidents route directly to Special Investigation Unit (SIU) cases.
- **Fairness:** Guardrail G9 ensures no protected demographic attributes are used in fraud scoring.

### P10: Customer Service, Inquiries & Complaint SLA Management
- **Inquiries:** Authenticated inquiry resolution via Assistant A6.
- **Complaints:** Dedicated complaint ticketing system with statutory SLA countdown (e.g., 5-day mandatory initial response, 15-day final resolution). Escalates automatically if SLA approaches breach.

### P11: Payout Disbursement & Double-Entry Financial Ledger
- **Process:** Approved claims generate disbursement requests.
- **Balanced Ledger:** Every financial movement creates balanced double-entry accounting records (Debits = Credits):
  - Incurred loss expense (Debit) vs Claims payable reserve (Credit).
  - Claims payable (Debit) vs Bank cash (Credit).
- **Invariant:** Absolute difference between total debits and credits across the ledger must strictly be zero.

### P12: Compliance, KYC Verification & Sanctions Screening
- **Screening:** Fuzzy name and tax ID matching against simulated OFAC / UN / local sanctions lists and politically exposed persons (PEP).
- **Rule:** Matches trigger compliance alerts. AI Assistant A8 explains match indicators to compliance officer, but is strictly prohibited from auto-clearing a positive match.

### P13: Reinsurance Treaties, Cessions & Bordereaux
- **Structure:** Quota-share and Excess-of-Loss (XOL) treaties.
- **Process:** Evaluates policy sum insured and claim amounts against treaty retention limits. Automatically calculates reinsurance cession amounts and generates monthly bordereaux statements for reinsurers.

---


## Part C: Autonomous Agents, Guardrails, Security & Traceability

### 3.7 Agents and Runtime Specification

#### 3.7.1 Agent Roster

| Agent ID | Name | Role & Objective | Autonomy Level | Key Tools |
|---|---|---|---|---|
| **A1** | Quote Assistant | Assists prospective customers in gathering facts, explaining coverage options, and presenting deterministic quotes. | L1 / L2 | `calculate_quote`, `get_coverage_details`, `check_vehicle_specs` |
| **A2** | Underwriting Copilot | Evaluates referral cases, summarizes risk profile, retrieves UW guidelines, and drafts proposed conditions. | L2 (Mandatory Human Sign-off) | `get_risk_history`, `search_uw_guidelines`, `propose_endorsement` |
| **A3** | Policy Servicing Assistant | Parses customer endorsement requests, drafts endorsements, calculates pro-rata premium adjustments. | L2 | `get_policy_details`, `calculate_prorata`, `propose_endorsement` |
| **A4** | Claims Triage Agent | Triage Motor OD claims, verifies coverage dates, retrieves clauses, runs payout calculations, identifies fraud signals. | L2 (Simulated L3 for micro-claims) | `get_policy`, `check_policy_active`, `get_claim_history`, `search_policy_wording`, `calculate_payout`, `get_fraud_signals`, `submit_recommendation` |
| **A5** | Fraud Assistant | Analyzes high-risk claims, generates objective anomaly summaries for SIU investigators using neutral language. | L2 | `get_claim_timeline`, `get_party_relations`, `flag_anomaly` |
| **A6** | Customer Service Assistant | Handles customer inquiries, policy lookups (after identity verification), and complaint logging. | L0 (FAQ) / L2 (Escalation) | `verify_customer`, `lookup_faq`, `create_service_ticket` |
| **A7** | Renewal Advisor | Reviews expiring policies, evaluates claim frequency, drafts renewal terms, checks notice deadlines. | L1 / L2 | `get_expiring_policies`, `calculate_renewal_rate`, `draft_renewal_notice`|
| **A8** | Compliance Explainer | Explains sanctions and watchlist fuzzy matches to compliance officers; strictly forbidden from clearing matches. | L2 | `get_watchlist_entity`, `compare_identifiers`, `draft_sar` |

#### 3.7.3 Hand-written Agent Loop

The agent runtime is implemented cleanly from scratch without heavy opaque frameworks to ensure total determinism, testability, and safety:
1. **Loop State:** `messages`, `step_count`, `token_usage`, `active_tools`.
2. **Step Budget:** Maximum iterations (default: 8 steps). If budget is reached before a terminal tool call, the run terminates safely with status `needs_human_review`.
3. **Tool Classification:**
   - `read`: Query-only tools with zero side-effects.
   - `propose`: Prepares draft records in the database requiring explicit user confirmation.
   - `terminal`: Concludes the agent execution (e.g. `submit_recommendation`).
4. **Loop Detector:** Detects repeated, identical tool invocations with identical parameters; halts execution if an infinite loop is detected.
5. **Fail-Safe Mechanism:** Any unhandled exception, LLM timeout, or JSON decoding failure automatically catches the exception, logs an incident, and safely routes the entity to human review.

#### 3.8 Claims Workflow States

The claims state machine operates with strict transition guards:
- `fnol_received`: Claim submitted, initial payload stored.
- `registered`: Policy matched, claim number assigned, preliminary reserve posted.
- `triage_in_progress`: A4 claims agent executing ReAct loop.
- `awaiting_review`: A4 completed; recommendation and evidence pending adjuster review.
- `approved`: Adjuster confirmed approval; payout finalized.
- `rejected`: Adjuster confirmed rejection; formal rejection notice issued.
- `settled`: Payment disbursed through finance module; claims reserve released.
- `closed`: Claim lifecycle concluded.

---

### 3.9 Guardrail Pipeline (G1 through G10)

Guardrails act as deterministic interceptors between agent output and external consumers:

- **G1 (Grounded Citations):** Every cited `clause_id` must exist in the database and must have been retrieved in the current run's knowledge search tool results.
- **G2 (Mathematical Invariant):** Any payout amount, deductible, or premium stated in agent output must exactly match the output of the corresponding deterministic engine execution.
- **G3 (Terminal Rejection Guard):** No claim or quote rejection can be finalized autonomously; human approval is mandatory.
- **G4 (Confidence & Risk Floor):** If confidence score $< 0.75$, or high-severity risk flags are present, or missing information is non-empty, outcome must be `needs_human_review`.
- **G5 (Mandatory Tool Execution):** For claim triage, `check_policy_active` and `search_policy_wording` must have been executed. If missing, downgrade to `needs_human_review`.
- **G6 (Simulated L3 Auto-Approve Bounds):** Auto-approval simulated only if: claimed amount $\le 500$ AZN, confidence $\ge 0.85$, zero fraud flags, policy verified active, valid citation evidence.
- **G7 (Prompt Injection Heuristic):** Scans inputs for adversarial jailbreak/manipulation patterns; flags suspicious records for immediate human review.
- **G8 (Neutral Language Guard):** In fraud analysis, ensures statements remain strictly factual and non-accusatory.
- **G9 (Protected Attribute Blindness):** Enforces that gender, race, religion, or protected demographics are never passed into underwriting or fraud scoring features.
- **G10 (Negative Payout Prevention):** Ensures deductible can never result in a negative payable payout.

---

### 3.12 Role-Based Access Control (RBAC) Matrix

| Role | Allowed Module Actions | Description |
|---|---|---|
| `customer` | `policy:read_own`, `claims:create`, `service:read_own` | End customer portal access |
| `broker` | `sales:create_quote`, `policy:read_assigned` | Intermediary sales agent |
| `underwriter` | `sales:review`, `underwriting:*`, `product:read` | Evaluates and binds risks |
| `adjuster` | `claims:*`, `policy:read`, `fraud:read` | Investigates and settles claims |
| `finance_officer` | `finance:*`, `claims:read` | Invoices, disbursements, ledger |
| `compliance_officer`| `compliance:*`, `party:read` | Sanctions and KYC review |
| `siu_investigator` | `fraud:*`, `claims:read` | Fraud investigation |
| `admin` | `platform:*`, `product:*`, `*` | Platform administration |

---

### 3.13 Observability and Metrics Endpoints

- `GET /health`: Liveness probe; returns 200 OK immediately.
- `GET /ready`: Readiness probe; executes a `SELECT 1` on PostgreSQL and verifies schema readiness.
- `GET /metrics`: Prometheus-compatible operational metrics:
  - `http_requests_total`
  - `agent_run_duration_seconds`
  - `llm_token_usage_total`
  - `guardrail_downgrade_total`
  - `claims_triage_decision_total`

---

### 4. Traceability Matrix

| Process / Capability | Master Plan Phase | Key Code Module | Key Agent / Engine |
|---|---|---|---|
| Repository & Environment Skeleton | Phase 0 | `platform` | Health/Ready API |
| Synthetic World & Labels | Phase 1 | `data/synthetic` | Deterministic Generator |
| Platform Kernel, RBAC & Outbox | Phase 2 | `platform` | Outbox, Workflow, RBAC |
| LLM Gateway & FNOL Extraction | Phase 3 | `platform/llm`, `claims` | Gateway, Extractor |
| Grounded Policy RAG | Phase 4 | `platform/knowledge` | Vector Chunking, Effective Filter |
| Agent Runtime & Guardrails | Phase 5 | `platform/runtime` | ReAct Loop, G1-G10 Pipeline |
| Policy Administration & Rating | Phase 6 | `product`, `policy` | Rating Engine, Pro-Rata Engine |
| Claims Triage (Motor OD) | Phase 7 | `claims` | Agent A4, Payout Calculator |
| Adjuster Console v1 | Phase 8 | `frontend` | React/Vite Console (R1) |
| Sales & Underwriting | Phase 9 | `sales`, `underwriting` | Agent A1, Agent A2 |
| Finance & Double-Entry Ledger | Phase 10 | `finance`, `reinsurance` | Ledger Engine, Agent A7 |
| Fraud, Compliance & Service | Phase 11 | `fraud`, `compliance`, `service`| A3, A5, A6, A8 (R2) |
| Console v2 & End-to-End Journeys | Phase 12 | `frontend`, `tests/e2e` | KPI Dashboards |
| Observability, Security & Governance | Phase 13 | `platform/security`, `docs` | Threat Model, AI Gov (R3) |

---
