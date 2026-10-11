# Code Map

## Directory Layout & Key Entrypoints

- `backend/app/main.py`: FastAPI application entrypoint, middleware, and router registration.
- `backend/app/config.py`: Environment configuration via Pydantic Settings.
- `backend/app/modules/platform/`: Technical kernel (RBAC, audit, outbox, job runner, LLM gateway, agent runtime, guardrails).
- `backend/app/modules/party/`: Party, vehicle, property, and contact registry.
- `backend/app/modules/product/`: Product definitions, versions, tariff tables, and wording clauses A–F.
- `backend/app/modules/policy/`: Policy issuance, rating engine, endorsements, cancellations.
- `backend/app/modules/claims/`: FNOL intake, coverage verification, payout calculator, Agent A4.
- `backend/app/modules/sales/`: Leads, quotes, Agent A1.
- `backend/app/modules/underwriting/`: UW rules engine, referrals, Agent A2.
- `backend/app/modules/finance/`: Invoices, double-entry ledger, disbursements.
- `backend/app/modules/fraud/`: Fraud signals, SIU cases, Agent A5.
- `backend/app/modules/compliance/`: Sanctions screening, AML alerts, Agent A8.
- `backend/app/modules/service/`: Inquiries, complaints SLA, Agent A3 & A6.
- `backend/app/modules/reinsurance/`: Treaties, cessions, bordereaux.
- `data/synthetic/`: Deterministic data generators and seed fixtures.
- `evals/`: LLM evaluation harness and benchmark suites.
- `frontend/`: React + TypeScript + Vite console.
