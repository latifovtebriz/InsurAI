# InsurAI Implementation Progress

## Current State
- **Active Phase:** Phase 11 (Fraud, Compliance, Service, A5, A6, A8, A3 - Release R2)
- **Active Task:** Task 11.1 (`fraud` module P09, SIU routing, A5 Fraud Agent with G8 neutral language)
- **Status:** In Progress
- **Last Completed Step:** Phase 10 completed. Built Finance double-entry ledger (Debits == Credits invariant), Invoicing, Payments, Dunning, Reinsurance treaties (QS/XOL), Bordereaux, Policy Renewal (P07), Agent A7 Renewal Advisor, REST APIs, and UI screens. Tagged `phase-10-done`.
- **Next Step:** Implement Phase 11 modules: fraud SIU (A5), compliance screening (A8), policy servicing (A3), customer service chat (A6), and tag `release-R2`.

---

## Phase Status Summary

| Phase | Description | Status | Tags |
|---|---|---|---|
| Phase 0 | Foundation, tooling, Git | Completed | `phase-0-done` |
| Phase 1 | Domain model, synthetic data, labels | Completed | `phase-1-done` |
| Phase 2 | Platform core | Completed | `phase-2-done` |
| Phase 3 | LLM gateway and extraction | Completed | `phase-3-done` |
| Phase 4 | Knowledge service (RAG) | Completed | `phase-4-done` |
| Phase 5 | Agent runtime, guardrails, evaluation core | Completed | `phase-5-done` |
| Phase 6 | Party, product, policy | Completed | `phase-6-done` |
| Phase 7 | Claims and Claims Triage Agent (A4) | Completed | `phase-7-done` |
| Phase 8 | Web console v1 & Release R1 | Completed | `phase-8-done`, `release-R1` |
| Phase 9 | Sales and underwriting (A1, A2) | Completed | `phase-9-done` |
| Phase 10 | Finance, renewal, reinsurance, A7 | Completed | `phase-10-done` |
| Phase 11 | Fraud, compliance, service, A5, A6, A8, A3 | In Progress | `release-R2` pending |
| Phase 12 | Console v2, KPIs, end-to-end journeys | Not Started | - |
| Phase 13 | Observability, security, governance, polish | Not Started | `release-R3` pending |
| Phase 14 | Deployment (Postponed) | Postponed | - |
| Phase 15 | Stretch (Postponed) | Postponed | - |

---

## Deferred Items & External Actions for Learner
- **DEFERRED (needs LLM_API_KEY):** Live Gemini API calls and evaluation benchmarks. System runs with FakeLLMClient. Command for morning:
  `python -m evals.run_eval --split dev --provider gemini`
- **DEFERRED (needs Docker Desktop):** Full multi-container composition. Run in morning:
  `docker compose up -d`
- **PUSH PENDING:** Remote push status tracked per phase tag.
