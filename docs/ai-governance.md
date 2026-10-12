# InsurAI Artificial Intelligence Governance Framework

## 1. Executive Summary & Principles

InsurAI adheres to enterprise AI governance principles tailored for Property & Casualty (P&C) insurance operations. In high-stakes financial domains involving risk pricing, coverage determinations, and capital disbursements, AI cannot operate as an unconstrained black box. 

Our framework is designed in alignment with:
- **Central Bank of Azerbaijan (CBA)** regulatory standards on insurance supervision and policyholder protection.
- **European Union AI Act (Regulation EU 2024/1689)** guidelines for High-Risk AI Systems (Annex III, Section 5: Essential private services, insurance risk assessment, and claims settlement).
- **Core Ethical Principles**: Human Agency & Oversight, Technical Robustness & Safety, Privacy & Data Governance, Transparency, Diversity & Fairness, and Accountability.

---

## 2. AI Autonomy Matrix

InsurAI categorizes every business workflow into one of three strict Autonomy Tiers:

| Autonomy Tier | Operational Scope | Trigger Conditions | Human Role | Key Engine / Agent |
|---|---|---|---|---|
| **Level 1: Straight-Through Execution** | Automated quoting, standard policy issuance, low-value Motor OD claims | Claim payable $\le 2,500$ AZN, active policy verified, clean fraud score ($< 0.20$), G1-G10 passed | Post-hoc audit sample review | Rating Engine, Claims Agent A4 |
| **Level 2: Human-in-the-Loop (HITL)** | Property fire claims, Motor claims $> 2,500$ AZN, mid-term endorsements, medium fraud signals ($0.20 \le \text{score} < 0.60$) | Any high-severity peril, value above threshold, moderate anomaly | **Mandatory Human Sign-off**: Agent prepares draft decision; human underwriter/adjuster must click "Approve" or "Reject" | Agent A2, Agent A4, Agent A6 |
| **Level 3: Advisory Copilot** | Sanctions & AML screening, high fraud suspicion ($\ge 0.60$), statutory complaints, complex renewals | Watchlist partial matches, SIU trigger, statutory complaint filing | **Strict Advisory Only**: AI summarizes evidence and suggests next steps; human makes 100% of determination | Agent A8, Agent A5, Agent A3 |

---

## 3. Mandatory Human Oversight Points & Circuit Breakers

### 3.1 Non-Clearance Invariant for Sanctions (Agent A8)
- **Hard Invariant**: The automated compliance agent (A8) is strictly prohibited from clearing a sanctions or watchlist alert autonomously.
- **Enforcement**: If a customer matches a sanctions list, the system locks the policy/claim in an escrow state. Only a human `compliance_officer` possessing appropriate RBAC privileges can review secondary identification documents and clear or confirm the match.

### 3.2 Adjuster Override Tracking
- Every autonomous recommendation rendered by Claims Agent A4 or Underwriting Agent A2 can be accepted, rejected, or modified by a human adjuster or underwriter.
- When modified, the system records the adjuster's rationale and tags the event in `platform.audit_logs`.
- The aggregate **Adjuster Override Rate** is exposed in real time on the Executive KPI dashboard (`GET /api/v1/metrics/executive-kpis`), providing operational leaders immediate visibility into agent alignment.

### 3.3 Large Loss & Property Circuit Breaker
- All property fire claims (`FIRE_CONFLAGRATION`, `WATER_LEAKAGE`) and losses exceeding 2,500 AZN are automatically intercepted and routed to Senior Adjusters, preventing automated disbursement of large capital reserves.

---

## 4. Transparency, Explainability & Grounding

### 4.1 Grounded Citations (Guardrail G1)
- The platform rejects any AI claim determination that relies on hallucinated or generic assumptions.
- **Rule**: Every reason stated in an approval or denial must cite a numbered policy clause (e.g., `POL-MOTOR-SEC-04-CL-01`) that was **physically retrieved** from the effective knowledge base during that active session.

### 4.2 Step-by-Step Reasoning Tracing
- Every agent execution is persisted in `platform.agent_runs` and `platform.agent_steps`.
- Traces capture execution latency (ms), token consumption, tool invocations, parameter inputs, tool outputs, and guardrail evaluations.
- Telemetry is inspectable in the Web Console v2 Traces screen (`TracesScreen.tsx`) for full post-incident explainability.

### 4.3 Neutral Language Standard (Guardrail G8)
- AI agents in the SIU (Special Investigation Unit) workflow must report objective, observable facts only (e.g., *"Accident occurred 3 days after policy inception"*).
- The use of speculative, accusatory, or defamatory terms (*"fraudulent", "criminal", "scammer", "dishonest"*) is forbidden in autonomous outputs.

---

## 5. Algorithmic Fairness & Protected Attribute Blindness

### 5.1 Demographic Blindness (Guardrail G9)
- To prevent algorithmic bias and discriminatory pricing, protected demographic attributes are strictly quarantined:
  - **Gender**
  - **Age** (outside statutory driving license validity)
  - **Ethnicity & Nationality**
  - **Religion**
  - **Marital Status**
  - **Disability / Health Status** (in P&C property/motor lines)
- These fields are excluded from rating multipliers, underwriting risk scores, and fraud anomaly detection algorithms.

### 5.2 Objective Rating Basis
- Motor OD and Property Fire premiums are determined exclusively by objective, actuarially justified risk variables: vehicle replacement value, vehicle age, engine cubic capacity, parking location, property construction material, fire safety systems, and deductible selection.

---

## 6. Technical Robustness & Mathematical Determinism

### 6.1 Zero-Hallucination Mathematical Engines
- In InsurAI, LLMs **never** perform arithmetic calculations.
- Financial figures (premiums, depreciation, prorated refunds, claim payouts, deductible subtractions, reinsurance cessions) are computed exclusively by deterministic Python engines using exact `Decimal` arithmetic (`ROUND_HALF_UP` to 2 decimal places).
- The **G2 Guardrail** compares the agent's proposed payable amount against the deterministic payout engine; if they differ by even 0.01 AZN, the decision is rejected and downgraded.

### 6.2 Double-Entry General Ledger Mathematical Invariant
- Every policy invoice, payment receipt, claim reserve adjustment, payout disbursement, and reinsurance treaty settlement is recorded as a balanced double-entry journal transaction.
- Invariant: $\Delta = |\sum \text{Debits} - \sum \text{Credits}| == 0.00$ AZN at all times.

---

## 7. Statutory & Regulatory Alignment Note

1. **Central Bank of Azerbaijan (CBA) Supervisory Compliance**:
   - InsurAI enforces the statutory 10-business-day resolution window for policyholder complaints (Agent A3 & `ComplaintEngine`).
   - All complaint intake, investigation milestones, and determinations are logged with immutable timestamps.
2. **Data Residency & Security**:
   - All synthetic and customer records remain strictly isolated within enterprise-managed databases.
   - LLM interactions use private enterprise gateways; no user prompts or PII are retained for public model training.
3. **Audit Trail Retention**:
   - Full transactional history, agent step logs, and outbox event streams are retained to satisfy statutory audit discovery requirements.
