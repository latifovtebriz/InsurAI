# Extraction Service Evaluation Report (DEV Split)

> **Notice:** `plumbing only, fake LLM, not a quality measurement`
> This run verifies parser contracts, bounded repair logic, and injection interceptor plumbing.

## Summary Metrics

| Metric | Result | Target |
|---|---|---|
| Total Cases Evaluated | 48 | $\ge 50$ |
| Schema Validity Rate | 100.0% | 100.0% |
| Policy Number Accuracy | 93.8% | $\ge 90.0$% |
| Incident Date Accuracy | 83.3% | $\ge 90.0$% |
| Claimed Amount Accuracy | 93.8% | $\ge 90.0$% |
| Prompt Injection Detection Rate | 100.0% | 100.0% |

## Evaluation Environment
- Provider: FakeLLMClient (offline plumbing mode)
- Prompt Version: `claims-fnol-extract-v1`
- Heuristic Interceptor: G7 Rule-Based Scanner Active
