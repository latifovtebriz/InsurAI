# Changelog

All notable changes to InsurAI will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - Release R1 - 2026-10-12

### Added
- **Web Console v1 (`frontend/`):** React 18, TypeScript, TailwindCSS single-page application with Claims Queue, FNOL Intake (4 golden demo presets), Claim Dossier, Policy Explorer, Audit Trail Diff Viewer, Operational KPIs, ReAct Trace Inspector modal, and 1-click persona logins.
- **REST API Layer (`backend/app/api/v1/`):** Full endpoint suite for `/auth`, `/policies`, `/claims`, `/traces`, `/audit`, and `/metrics`.
- **E2E Golden Journey Test:** Comprehensive 10-step lifecycle integration test verifying the complete flow from FNOL submission to financial settlement.
- **Claims Management & Triage Agent A4:** Deterministic payout engine (Clause D.2 Constructive Total Loss, deductible, Clause E.3 underinsurance), 3-day notification deadline engine, rule-based fraud detection heuristics, and Claims Triage Agent A4 with Guardrails G1–G10.
- **Policy, Party & Product Domains:** Schema-per-module isolation, deterministic rating engines (Motor OD V1/V2, Motor TPL, Home), 4-eyes governance for wordings, KYC verification, pro-rata cancellation & refund calculator.
- **Agent Runtime & Guardrails (Phase 5):** Hand-written ReAct loop, tool registry, step budgets, loop detector, persistent execution tracing (`AgentRun`, `AgentStep`), Guardrails G1–G10 pipeline.
- **Knowledge Service (Phase 4):** Clause-level chunking, date-in-force SQL pre-filtering, time-travel retrieval validation across effective-dated wordings.
- **LLM Gateway (Phase 3):** Provider-agnostic `LLMClient` protocol, `FakeLLMClient`, `RecordReplayLLMClient`, `GeminiLLMClient`, rate limiting, bounded repair, G7 injection scanner.
- **Platform Core (Phase 2):** PBKDF2/JWT auth, RBAC permissions matrix, declarative state machines, transactional outbox, resilient background job runner, RFC 7807 problem details.
- **Synthetic Dataset & Labels (Phase 1):** 136 realistic claims, 100 parties, 100 policies, effective-dated 2025/2026 wordings, held-out splits (`dev`, `test`, `smoke`).
- **Core Skeleton (Phase 0):** Modular monolith layout, AST module boundary tests, secret scanner.

## [Unreleased]
### Added
- **Sales Module (Phase 9):** Lead and Quote domain models in `"sales"` schema, 30-day quote validity, deterministic rating integration (Motor OD, Motor TPL, Home), 1-lump-sum and 4-installment schedules, KYC-lite screening hook.
- **Agent A1 (Quote Assistant):** Natural language quote intake, automatic missing-field clarification detection, Guardrail G2 mathematical equality (100% numerical fidelity matching engine), Guardrail G7 prompt injection interception.
- **Underwriting Module & Rule Engine (Phase 9):** `UnderwritingCase` model in `"underwriting"` schema, deterministic rule engine (UW-01 through UW-05), authority limits matrix (Junior, Senior, Chief), Guardrail G3 terminal decline justification enforcement.
- **Agent A2 (Underwriting Copilot):** Risk profiling, underwriting guidelines RAG, proposed conditions generation under L2 human-in-the-loop governance.
- **REST API & Web Console v2 (Phase 9):** Endpoints `/api/v1/sales/*` and `/api/v1/underwriting/*`, `QuotesScreen.tsx` (calculator, A1 chat, quote ledger), and `UnderwritingScreen.tsx` (referral queue, rule hits dossier, A2 Copilot panel, adjudication form).
- **Evaluation Suite (Phase 9):** Evaluated across 60 test scenarios with 100% G2 engine fidelity, 100% rule recall and precision, and 100% human sign-off enforcement.

- Phase 10: Finance, Renewal, Reinsurance (A7).
- Phase 11: Fraud SIU (A5), Compliance (A8), Servicing (A3), Customer Chat (A6). Tag `release-R2`.
