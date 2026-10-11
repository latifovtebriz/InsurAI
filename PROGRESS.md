# InsurAI Implementation Progress

## Current State
- **Active Phase:** Phase 0 (Foundation, tooling, Git)
- **Active Task:** Task 0.0 (Git initialization and pre-commit security verification)
- **Status:** In Progress
- **Last Completed Step:** Bootstrap and document assembly completed.
- **Next Step:** Git setup, `.gitignore` creation, verify `.env` is ignored, initial commit.

---

## Phase Status Summary

| Phase | Description | Status | Tags |
|---|---|---|---|
| Phase 0 | Foundation, tooling, Git | In Progress | - |
| Phase 1 | Domain model, synthetic data, labels | Not Started | - |
| Phase 2 | Platform core | Not Started | - |
| Phase 3 | LLM gateway and extraction | Not Started | - |
| Phase 4 | Knowledge service (RAG) | Not Started | - |
| Phase 5 | Agent runtime, guardrails, evaluation core | Not Started | - |
| Phase 6 | Party, product, policy | Not Started | - |
| Phase 7 | Claims and Claims Triage Agent (A4) | Not Started | - |
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
