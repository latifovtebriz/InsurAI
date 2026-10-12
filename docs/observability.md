# InsurAI Observability, Telemetry & Alerts Guide

## 1. Overview & Architecture Reference

InsurAI implements enterprise-grade observability per **Section 3.13 of the Architecture and Processes Specification**. The telemetry stack provides deep visibility into:
1. System infrastructure health (liveness, database connectivity, event outbox latency).
2. Autonomous AI agent performance (execution latency, token consumption, guardrail intervention rates).
3. Core insurance operations (claims triage velocity, active policy volumes, loss reserves).
4. Strict mathematical invariants (General Ledger balance $\Delta = |Debits - Credits| == 0.00$ AZN).

---

## 2. Telemetry Endpoints Reference

| Endpoint | Method | Response Type | Description |
|---|---|---|---|
| `/health` | `GET` | `application/json` | **Liveness Probe**: Confirms FastAPI process is responsive. Returns `{"status": "ok", "app": "insurai"}` with `X-Correlation-ID`. |
| `/ready` | `GET` | `application/json` | **Readiness Probe**: Verifies PostgreSQL connection pool via `SELECT 1` and monitors the transactional outbox queue depth (`outbox_backlog`). Returns HTTP 503 if DB is disconnected. |
| `/metrics` | `GET` | `text/plain; version=0.0.4` | **Prometheus Exposition**: Standard text format for Prometheus scrapers, exposing core business and runtime counters. |
| `/api/v1/metrics/prometheus` | `GET` | `text/plain; version=0.0.4` | API versioned mirror of the Prometheus exposition endpoint. |
| `/api/v1/metrics/executive-kpis` | `GET` | `application/json` | Real-time JSON telemetry consumed by the Executive Dashboard in Web Console v2 (conversion rate, loss ratio, cycle times, ledger balance). |

---

## 3. Prometheus Metrics Catalog

```prometheus
# HELP http_requests_total Total number of HTTP business transactions logged.
# TYPE http_requests_total counter
http_requests_total{system="insurai"} 142

# HELP agent_run_duration_seconds Average execution duration of autonomous agent runs in seconds.
# TYPE agent_run_duration_seconds gauge
agent_run_duration_seconds{agent="all"} 0.3840

# HELP llm_token_usage_total Total tokens consumed by LLM gateway.
# TYPE llm_token_usage_total counter
llm_token_usage_total{provider="gateway"} 3850

# HELP guardrail_downgrade_total Total number of agent runs downgraded by guardrails to human review.
# TYPE guardrail_downgrade_total counter
guardrail_downgrade_total{reason="guardrail_intervention"} 4

# HELP claims_triage_decision_total Claims decisions broken down by status.
# TYPE claims_triage_decision_total counter
claims_triage_decision_total{status="approved"} 12
claims_triage_decision_total{status="rejected"} 2
claims_triage_decision_total{status="needs_human_review"} 4
claims_triage_decision_total{status="settled"} 8
claims_triage_decision_total{status="under_investigation"} 3

# HELP general_ledger_balance_difference Absolute difference between General Ledger debits and credits in AZN (invariant == 0.00).
# TYPE general_ledger_balance_difference gauge
general_ledger_balance_difference{currency="AZN"} 0.00

# HELP insurai_active_policies_total Total number of active insurance policies.
# TYPE insurai_active_policies_total gauge
insurai_active_policies_total 25

# HELP insurai_total_reserves_azn Total established claim reserves in AZN.
# TYPE insurai_total_reserves_azn gauge
insurai_total_reserves_azn{currency="AZN"} 14500.00
```

---

## 4. Service Level Objectives (SLOs)

| Metric / Objective | Target | Measurement Window | Action on Violation |
|---|---|---|---|
| **API Availability** | $\ge 99.9\%$ | Rolling 30 days | Automatic failover, container restart |
| **P95 Synchronous Latency** | $\le 200$ ms | 5-minute rolling window | Horizontal scale-out of backend workers |
| **P95 Agent Run Duration** | $\le 30$ seconds | Per workflow batch | Audit tool execution timeouts, fallback to heuristic |
| **Financial Ledger Invariant** | **$\Delta = 0.00$ AZN** (100%) | Instantaneous | Immediate system halt / emergency freeze of ledger engine |
| **Complaint Statutory SLA** | $100\%$ within 10 days | Monthly regulatory audit | Escalate pending cases to Head of Compliance |
| **LLM Gateway Success Rate** | $\ge 99.0\%$ | 15-minute rolling window | Circuit breaker trigger; fallback to offline deterministic rules |

---

## 5. Alert Rules Configuration (`prometheus-alerts.yml`)

```yaml
groups:
  - name: insurai_critical_alerts
    rules:
      # P1 - Critical Financial Integrity
      - alert: GeneralLedgerImbalance
        expr: general_ledger_balance_difference{currency="AZN"} > 0.00
        for: 0m
        labels:
          severity: critical
          tier: p1
        annotations:
          summary: "General Ledger imbalance detected!"
          description: "General Ledger debits and credits differ by {{ $value }} AZN. Double-entry accounting invariant violated."
          runbook_url: "docs/observability.md#runbook-p1-ledger-imbalance"

      # P1 - System Outage / Database Disconnection
      - alert: DatabaseDisconnected
        expr: probe_success{instance="http://backend:8000/ready"} == 0
        for: 1m
        labels:
          severity: critical
          tier: p1
        annotations:
          summary: "InsurAI backend ready probe failing"
          description: "Database connection failed or backend unresponsive for > 1 minute."
          runbook_url: "docs/observability.md#runbook-p1-db-unreachable"

      # P2 - Transactional Outbox Lag
      - alert: OutboxBacklogHigh
        expr: insurai_outbox_backlog_total > 100
        for: 5m
        labels:
          severity: warning
          tier: p2
        annotations:
          summary: "Outbox event publishing backlog > 100"
          description: "Transactional outbox events are accumulating without being published to subscribers."
          runbook_url: "docs/observability.md#runbook-p2-outbox-lag"

      # P2 - Agent Safety Downgrade Spike
      - alert: AgentSafetyDowngradeSpike
        expr: rate(guardrail_downgrade_total[10m]) / rate(http_requests_total[10m]) > 0.25
        for: 5m
        labels:
          severity: warning
          tier: p2
        annotations:
          summary: "Spike in agent guardrail downgrades (> 25%)"
          description: "Over 25% of agent executions are being downgraded to human review by safety guardrails."
          runbook_url: "docs/observability.md#runbook-p2-guardrail-spike"

      # P2 - Statutory Complaint SLA Breach Risk
      - alert: ComplaintSLABreachRisk
        expr: insurai_complaints_approaching_sla_total > 0
        for: 1h
        labels:
          severity: warning
          tier: p2
        annotations:
          summary: "Customer complaints nearing 10-day statutory limit"
          description: "Unresolved complaints are at day 8+ without final determination."
          runbook_url: "docs/observability.md#runbook-p2-complaint-sla"
```

---

## 6. Incident Runbooks

### Runbook P1: Ledger Imbalance (`GeneralLedgerImbalance`)
1. **Immediate Action**: Freeze automated payout and disbursement engines (`DisbursementEngine.freeze()`).
2. **Identification**: Query `platform.audit_logs` for `action='POST_LEDGER_TRANSACTION'` with the correlation ID matching the triggering event.
3. **Verification**: Execute `SELECT transaction_id, SUM(debit) - SUM(credit) FROM finance.general_ledger_entries GROUP BY transaction_id HAVING SUM(debit) != SUM(credit);`.
4. **Remediation**: Post an offsetting correcting journal entry with authorized finance officer sign-off. Do not edit existing rows.

### Runbook P1: Database Unreachable (`DatabaseDisconnected`)
1. Verify PostgreSQL container/instance status: `docker compose ps` or provider status dashboard.
2. Check PostgreSQL connection pool exhaustion: `SELECT count(*) FROM pg_stat_activity;`.
3. If PostgreSQL restarted, verify backend connection pool reconnection via `/ready`.

### Runbook P2: Outbox Publishing Lag (`OutboxBacklogHigh`)
1. Check background worker process logs: `scripts/run_outbox_publisher.py` or Celery/cron tasks.
2. Inspect `platform.outbox_events` table for rows where `status='failed'`.
3. Check dead-letter queue or retry counters; re-trigger publishing of pending events once message broker connectivity is restored.

### Runbook P2: Guardrail Downgrade Spike (`AgentSafetyDowngradeSpike`)
1. Inspect `platform.agent_runs` table where `status='needs_human_review'`.
2. Check `agent_steps` log for triggering guardrail rule (e.g., G3 Hallucination, G4 Ambiguity, G7 Prompt Injection, G10 Discrepancy).
3. If prompt injection detected, review incoming FNOL descriptions for adversarial payloads.
