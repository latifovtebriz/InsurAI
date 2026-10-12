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

## [2.0.0] - Release R2 - 2026-10-12

### Added
- **Fraud Detection & SIU (Phase 11):** `fraud` module in schema `"fraud"`, 6 transparent risk signals (FS-01..FS-06), automatic SIU case routing at score >= 70, Guardrail G9 fairness check (`FairnessViolationError` on protected demographics).
- **Agent A5 (SIU Assistant):** Objective findings dossier synthesis with Guardrail G8 neutral language enforcement (`validate_neutral_language`, `sanitize_neutral_language`), stripping all accusatory defamation risks.
- **Compliance & Sanctions Screening (Phase 11):** `compliance` module in schema `"compliance"`, fuzzy string matching against OFAC SDN, UN Sanctions, and PEP watchlists via token Jaccard, containment, and character bigrams.
- **Agent A8 (Compliance Explainer):** Comparative match analysis and draft Suspicious Activity Reports (SAR). Hardcoded regulatory invariant: AI can never clear a sanctions match (`attempt_auto_clear()` strictly raises `PermissionError`), requiring human compliance officer adjudication.
- **Customer Service (Agent A6) & Verification Gate (Phase 11):** Strict identity verification gate: unauthenticated guests receive public FAQs only, while policyholder data requests are blocked with zero PII exposure (`action_taken="PROMPT_AUTHENTICATION"`).
- **Policy Servicing (Agent A3) & Mid-Term Endorsements (Phase 11):** Mid-term endorsement process (P06) with deterministic Decimal pro-rata premium adjustments down to the exact day, requiring Level 2 underwriter approval.
- **Complaints & Statutory SLAs (Phase 11):** 5-day initial response and 15-day resolution deadline tracking with automatic Ombudsman breach escalation.
- **Web Console v2 Screens (Phase 11):** `SIUScreen.tsx` (fraud score breakdown, G8 neutral dossier), `ComplianceScreen.tsx` (sanctions screening, A8 explainer, officer adjudication), and `CustomerServiceScreen.tsx` (verification gate chat simulator, A3 endorsement drafting, complaints SLA tracker).
- **Finance, Renewal & Reinsurance (Phase 10):** Balanced double-entry ledger (Debits == Credits invariant across 100% of postings), installment invoicing, automated dunning (T+7, T+14, T+30), Quota Share and Excess of Loss treaties, bordereaux generator, T-60 renewal scanning with statutory 30-day notice monitoring, Agent A7 Renewal Advisor.
- **Sales & Underwriting (Phase 9):** Sales module, deterministic rating engines (G2 math equality), Agent A1 Quote Assistant, Underwriting rule engine (UW-01..05), authority tiers, Agent A2 Underwriting Copilot.
- **Agent Evaluation Benchmark Suite:** 4 evaluation suites in `evals/` covering all 8 agents (A1 through A8) with 100% pass rates on mathematical fidelity, fairness, and non-clearance invariants.

