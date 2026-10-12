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
- **Agent Evaluation Benchmark Suite:** 4 evaluation suites in `evals/` covering all 8 agents (A1 through A8) with 100% pass rates on mathematical fidelity, fairness, and non-clearance invariants.

### Phase 12: Console v2, KPIs & Golden Lifecycle Journeys - 2026-10-12
- **Executive KPIs Engine (`/api/v1/metrics/executive-kpis`):** Aggregation of underwriting conversion, policy retention, claims loss ratio, cycle times, statutory complaint SLA compliance, adjuster override rates, and General Ledger double-entry balance verification ($\Delta = 0.00$ AZN).
- **12-Step Full Lifecycle Golden Journey Integration Test:** Comprehensive end-to-end integration test (`test_full_lifecycle_golden_journey.py`) verifying all 12 operational stages of the property & casualty lifecycle.
- **Turnkey Seed-to-Demo Script (`scripts/seed_demo_data.py`):** Standalone zero-friction seeding pipeline populating products, accounts, treaties, parties, policies, claims, and balanced accounting books in seconds.
- **Web Console v2 Metrics Polish:** Real-time Executive KPIs dashboard, General Ledger balanced badge, and explicit AI Autonomy Level matrix (`[L1 Automated Execution]`, `[L2 Human-in-the-Loop]`, `[L3 Advisory Copilot]`).

## [3.0.0] - Release R3 - 2026-10-12

### Added
- **Production Observability & Prometheus Exposition (Architecture 3.13):** Standard text exposition at `GET /metrics` and `GET /api/v1/metrics/prometheus` exposing HTTP business transaction volume, agent run durations, token consumption, guardrail downgrade rates, claim triage decision breakdowns, active policy totals, established claim reserves, and the General Ledger balance difference gauge ($\Delta = 0.00$ AZN).
- **Enhanced Readiness Probe (`GET /ready`):** Database pool connection verification and transactional outbox queue depth monitoring.
- **Observability Guide & Operational Runbooks (`docs/observability.md`):** Complete Prometheus metrics catalog, Service Level Objectives (SLOs), Prometheus alert rules (`GeneralLedgerImbalance`, `OutboxBacklogHigh`, `AgentSafetyDowngradeSpike`, `ComplaintSLABreachRisk`), and step-by-step incident runbooks.
- **Security Defenses & DoS Mitigation:** `MaxPayloadSizeMiddleware` rejecting oversized requests > 10MB with HTTP 413 Payload Too Large. Automatic PII and secret redaction (`sanitize_pii` in `JSONFormatter`) scrubbing credit card PANs and Authorization Bearer tokens in structured JSON logs.
- **Chaos-Style Robustness Test Suite (`test_chaos_and_robustness.py`):** Verified system fail-safe resilience against LLM timeouts, network drops, malformed non-JSON model outputs, atomic database rollbacks, and oversized payload attacks.
- **Security Mitigations Test Suite (`test_security_mitigations.py`):** Verifies G7 prompt injection defense, ReAct tool execution whitelist and argument validation, RBAC matrix authorization across 8 roles, and log PII redaction.
- **Threat Model Specification (`docs/security.md`):** Complete STRIDE analysis and OWASP Top 10 for Large Language Models (LLM01–LLM10) defensive mappings.
- **AI Governance Framework (`docs/ai-governance.md`):** Formalized 3-tier autonomy matrix (L1, L2, L3), human oversight invariants (adjuster overrides, sanctions non-clearance), explainability (G1 grounding citations), and fairness blindness (G9).
- **Engineering Interview Notes (`INTERVIEW_NOTES.md`):** 10 tough interview questions with honest answers, architectural story, 5 hardest problems solved, honest limitations, and resume bullets with real metrics.
- **Golden Demo Walkthrough Script (`DEMO_SCRIPT.md`):** 5-minute walkthrough of 4 core operational journeys with curl and UI verification steps.
- **CI/CD Pipeline Enhancement (`.github/workflows/ci.yml`):** Comprehensive GitHub Actions workflow executing secret scanner, ruff lint/format, mypy typecheck, SAST security scan (Bandit), dependency audit (pip-audit), backend test suite, and frontend production build.
- **Open Source Licensing:** Added standard MIT License (`LICENSE`).

