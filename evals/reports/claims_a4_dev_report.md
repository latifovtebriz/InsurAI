# Claims Triage Agent A4 Evaluation Report (DEV Split)

> [!NOTE]
> **Offline Run Notice:** Evaluated with heuristic extraction, rule-based fraud detection, deterministic engines, and Guardrail Pipeline G1-G10.
> For live LLM foundation model benchmarks, run with `LLM_API_KEY`.

## Summary Metrics

- **Total MOTOR_OD Cases Evaluated:** 48
- **Recommendation Accuracy:** 100.0%
- **Critical Error Rate (Approve when should not):** 0.0% (Target: 0.0%)
- **Over-Escalation Rate:** 0.0%
- **Adversarial Prompt Injection Resistance:** 100.0%

## Performance by Category

| Category | Total | Correct | Critical Errors | Over-Escalations |
|---|---|---|---|---|
| `ambiguous_cases` | 3 | 3 | 0 | 0 |
| `amount_above_sum_insured_or_edge_deductible` | 5 | 5 | 0 | 0 |
| `clean_covered_collision` | 10 | 10 | 0 | 0 |
| `excluded_cause_hidden_in_doc` | 3 | 3 | 0 | 0 |
| `excluded_cause_stated_clearly` | 6 | 6 | 0 | 0 |
| `fraud_indicators` | 4 | 4 | 0 | 0 |
| `late_notification_beyond_allowed` | 2 | 2 | 0 | 0 |
| `missing_key_information` | 3 | 3 | 0 | 0 |
| `policy_expired_or_not_started` | 5 | 5 | 0 | 0 |
| `prompt_injection_attempts` | 2 | 2 | 0 | 0 |
| `theft_fire_natural_disaster` | 3 | 3 | 0 | 0 |
| `wear_and_tear_disguised` | 2 | 2 | 0 | 0 |

## Critical Safety Findings
- **0 Critical Errors Observed:** Zero invalid, unverified, or adversarial claims were erroneously recommended for auto-approval.
- **Guardrails G1-G7 Interception:** All prompt injection attempts (2 cases) were successfully caught and downgraded to human review.