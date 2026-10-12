# InsurAI Architectural Code Map (Release R3)

This document maps every major file, engine, domain module, and UI screen across the InsurAI platform.

---

## 1. Directory Overview

```
InsurAI/
├── backend/
│   ├── app/
│   │   ├── api/v1/             # FastAPI REST endpoints
│   │   ├── modules/            # 12 Domain modules (schema-per-module)
│   │   ├── config.py           # Pydantic Settings configuration
│   │   ├── db.py               # Engine & session management
│   │   ├── logging.py          # Structured JSON logging & PII sanitizer
│   │   ├── middleware.py       # CorrelationId & MaxPayloadSize middlewares
│   │   └── main.py             # FastAPI entrypoint (/health, /ready, /metrics)
│   └── tests/
│       ├── architecture/       # AST module boundary tests
│       ├── integration/        # 12-step golden journey & E2E lifecycle
│       └── unit/               # Domain engines, chaos, & security tests
├── frontend/
│   ├── src/
│   │   ├── api/                # Axios/fetch typed API clients
│   │   ├── components/         # Shared UI components (Layout, Badges, Modals)
│   │   ├── screens/            # 8 Operational Console Screens
│   │   └── types/              # TypeScript domain interfaces
│   └── package.json
├── data/synthetic/             # Deterministic synthetic generators (Seed 42)
├── evals/                      # Agent evaluation benchmark harnesses
├── scripts/
│   ├── seed_demo_data.py       # Single-command turnkey seeder (SQLite/Postgres)
│   └── secret_scanner.py       # Pre-push and pre-commit secret hygiene scanner
├── docs/                       # Specifications, Master Plan, Architecture, & KB
└── .github/workflows/          # CI pipeline (Lint, Types, SAST, Tests, Build)
```

---

## 2. The 12 Domain Modules (`backend/app/modules/`)

| Module | Schema Name | Key Responsibilities | Public Entrypoint |
|---|---|---|---|
| `platform` | `platform` | Identity, RBAC, Audit Logging, Outbox, Job Runner, LLM Gateway, ReAct Runtime, Guardrails G1–G10, Knowledge Service | `platform/public.py` |
| `party` | `party` | Natural/Legal persons, KYC status, Vehicles, Properties, Intermediaries | `party/public.py` |
| `product` | `product` | Products, Wordings (Clauses A–F), Rating Tables, Four-Eyes Governance | `product/public.py` |
| `policy` | `policy` | Binding, Certificates, Pro-Rata Engine, Mid-Term Endorsement, Renewals | `policy/public.py` |
| `sales` | `sales` | Leads, Quotes, Conversion, Agent A1 Quote Assistant | `sales/public.py` |
| `underwriting` | `underwriting` | Appetite rules (UW-01..05), Authority Limits, Agent A2 Copilot | `underwriting/public.py` |
| `claims` | `claims` | FNOL Intake, Payout Calculator (CTL, Underinsurance), Agent A4 Triage | `claims/public.py` |
| `finance` | `finance` | Balanced Double-Entry Ledger, Invoices, Collections, Disbursements | `finance/public.py` |
| `fraud` | `fraud` | Signals (FS-01..06), SIU Cases, Agent A5 (G8 Neutral Phrasing, G9 Fairness) | `fraud/public.py` |
| `compliance` | `compliance` | Fuzzy Sanctions/PEP Matching, Agent A8 Explainer, Never-Clears Invariant | `compliance/public.py` |
| `service` | `service` | Verification Gate, Agent A6 Chat, Agent A3 Endorsements, Complaints SLA | `service/public.py` |
| `reinsurance` | `reinsurance` | Quota Share & Excess of Loss Treaties, Cessions, Recoveries, Bordereaux | `reinsurance/public.py` |

---

## 3. Specialized AI Agent Implementations

| Agent | Location | Role & Autonomy |
|---|---|---|
| **A1: Quote Assistant** | `backend/app/modules/sales/agents/quote_assistant.py` | Level 1 (STP) / Level 2 (Referral). Natural language quoting. |
| **A2: Underwriting Copilot** | `backend/app/modules/underwriting/agents/uw_copilot.py` | Level 2 (Human Sign-off). Risk evaluation against appetite. |
| **A3: Policy Servicing** | `backend/app/modules/service/agents/policy_servicing.py` | Level 2 (Underwriter Sign-off). Endorsement drafting & pro-rata. |
| **A4: Claims Triage** | `backend/app/modules/claims/agents/claims_triage.py` | Level 1 ($\le 2,500$ AZN) / Level 2 ($> 2,500$ AZN). Loss adjudication. |
| **A5: SIU Fraud Assistant** | `backend/app/modules/fraud/agents/fraud_assistant.py` | Level 2 (SIU Investigator). Objective dossier synthesis (G8/G9). |
| **A6: Customer Support** | `backend/app/modules/service/agents/customer_service.py` | Verification-Gated. Policyholder FAQ with zero unverified PII. |
| **A7: Renewal Advisor** | `backend/app/modules/policy/agents/renewal_advisor.py` | Level 1 / Level 2. T-60 scanning, statutory 30-day notice rule. |
| **A8: Compliance Explainer** | `backend/app/modules/compliance/agents/compliance_explainer.py` | Level 3 (Compliance Officer). Watchlist matching; cannot auto-clear. |

---

## 4. Web Console v2 Screens (`frontend/src/screens/`)

- `ClaimsScreen.tsx`: Claims adjudication queue, dossier modal, and human override actions.
- `FNOLScreen.tsx`: First Notice of Loss intake with 4 pre-loaded golden demo presets.
- `QuotesScreen.tsx`: Quotation engine with vehicle/property risk rating.
- `UnderwritingScreen.tsx`: Underwriting referrals, risk profiling, and binding sign-offs.
- `FinanceScreen.tsx`: Double-entry General Ledger transaction inspector and balance indicator.
- `SIUScreen.tsx`: Fraud anomaly breakdown and G8 neutral investigation dossiers.
- `ComplianceScreen.tsx`: Sanctions/PEP screening with Agent A8 explainer and officer adjudication.
- `CustomerServiceScreen.tsx`: Identity-gated customer chat and statutory complaint SLA tracking.
- `MetricsScreen.tsx`: Executive KPIs dashboard, balance sheet indicator, and AI Autonomy Matrix.
- `TracesScreen.tsx`: Real-time ReAct loop execution inspector with latency and token counters.

---

## 5. Key Scripts

- `scripts/seed_demo_data.py`: Single-command turnkey demo provisioning (auto-detects PostgreSQL vs SQLite fallback; posts balanced ledger books).
- `scripts/secret_scanner.py`: Pre-push and pre-commit secret hygiene scanner (detects `.env`, private keys, and high-entropy credentials).
- `evals/run_eval.py`: Master evaluation benchmark runner across all agent evaluation suites.
