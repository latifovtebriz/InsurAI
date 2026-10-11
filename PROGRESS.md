# InsurAI Implementation Progress

## Current State
- **Active Phase:** Phase 7 (Claims and Claims Triage Agent A4 - Flagship Flow R1)
- **Active Task:** Task 7.1 (Claims module models, registration, payout calculator engine, and A4 ReAct Agent)
- **Status:** In Progress
- **Last Completed Step:** Phase 6 completed and tagged `phase-6-done`.
- **Next Step:** Implement claims module, FNOL registration, deterministic payout engine, Claims Triage Agent A4 with tools and guardrails, and run A4 benchmark evaluation.

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
| Phase 7 | Claims and Claims Triage Agent (A4) | In Progress | - |
| Phase 8 | Web console v1 & Release R1 | Not Started | `release-R1` pending |
| Phase 9 | Sales and underwriting (A1, A2) | Not Started | - |
| Phase 10 | Finance, renewal, reinsurance, A7 | Not Started | - |
| Phase 11 | Fraud, compliance, service, A5, A6, A8, A3 | Not Started | `release-R2` pending |
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
