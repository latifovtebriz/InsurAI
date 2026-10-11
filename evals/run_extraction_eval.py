"""Evaluation harness for FNOL Claim Extraction on the dev split."""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "backend"))

from app.modules.claims.extraction import ClaimExtractionService  # noqa: E402
from app.modules.platform.llm.client import FakeLLMClient  # noqa: E402
from app.modules.platform.llm.gateway import LLMGateway  # noqa: E402


async def run_evaluation(split_name: str = "dev") -> dict[str, float]:
    data_file = repo_root / "data" / "synthetic" / f"claims_{split_name}_split.json"
    if not data_file.exists():
        print(f"Dataset split file not found: {data_file}")
        sys.exit(1)

    with open(data_file, encoding="utf-8") as f:
        scenarios = json.load(f)

    # Filter to MOTOR_OD scenarios for extraction evaluation
    od_scenarios = [s for s in scenarios if s.get("product_code") == "MOTOR_OD"]
    print(
        f"Running Extraction Evaluation on '{split_name}' split ({len(od_scenarios)} MOTOR_OD cases)..."
    )

    # Use FakeLLMClient for offline plumbing verification
    fake_client = FakeLLMClient()
    gateway = LLMGateway(client=fake_client)
    service = ClaimExtractionService(llm_gateway=gateway)

    total = len(od_scenarios)
    pol_matches = 0
    date_matches = 0
    amount_matches = 0
    schema_valid_count = 0
    injection_detected_count = 0
    injection_total = 0

    for s in od_scenarios:
        # Construct realistic intake statement with user-reported metadata
        header_lines: list[str] = []
        if s.get("policy_number") and s["category"] != "missing_key_information":
            header_lines.append(f"Policy Number: {s['policy_number']}")
        if s.get("incident_date") and s["category"] != "missing_key_information":
            header_lines.append(f"Incident Date: {s['incident_date']}")
        if s.get("claimed_amount") and s["category"] != "missing_key_information":
            header_lines.append(f"Claimed Amount: {s['claimed_amount']} AZN")
        header_lines.append(f"Description: {s['description']}")

        raw_text = "\n".join(header_lines)
        docs = [d["content_text"] for d in s.get("documents", [])]

        is_inj = s.get("is_injection_attempt", False)
        if is_inj:
            injection_total += 1

        try:
            extracted = await service.extract_claim_fnol(raw_text, docs)
            schema_valid_count += 1

            if s.get("policy_number") and extracted.policy_number == s["policy_number"]:
                pol_matches += 1

            if s.get("incident_date") and extracted.incident_date == s["incident_date"]:
                date_matches += 1

            if s.get("claimed_amount") and extracted.claimed_amount is not None:
                if abs(extracted.claimed_amount - s["claimed_amount"]) < 1.0:
                    amount_matches += 1

            if is_inj and extracted.has_injection_risk:
                injection_detected_count += 1

        except Exception as exc:
            print(f"Extraction failed on scenario {s.get('scenario_id')}: {exc}")

    metrics = {
        "total_evaluated": total,
        "schema_validity_rate": (schema_valid_count / total) * 100.0 if total else 0.0,
        "policy_number_accuracy": (pol_matches / total) * 100.0 if total else 0.0,
        "incident_date_accuracy": (date_matches / total) * 100.0 if total else 0.0,
        "claimed_amount_accuracy": (amount_matches / total) * 100.0 if total else 0.0,
        "injection_detection_rate": (
            (injection_detected_count / injection_total) * 100.0 if injection_total else 100.0
        ),
    }

    # Generate Markdown Report
    reports_dir = repo_root / "evals" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"extraction_{split_name}_report.md"

    report_content = f"""# Extraction Service Evaluation Report ({split_name.upper()} Split)

> **Notice:** `plumbing only, fake LLM, not a quality measurement`
> This run verifies parser contracts, bounded repair logic, and injection interceptor plumbing.

## Summary Metrics

| Metric | Result | Target |
|---|---|---|
| Total Cases Evaluated | {metrics["total_evaluated"]} | $\\ge 50$ |
| Schema Validity Rate | {metrics["schema_validity_rate"]:.1f}% | 100.0% |
| Policy Number Accuracy | {metrics["policy_number_accuracy"]:.1f}% | $\\ge 90.0$% |
| Incident Date Accuracy | {metrics["incident_date_accuracy"]:.1f}% | $\\ge 90.0$% |
| Claimed Amount Accuracy | {metrics["claimed_amount_accuracy"]:.1f}% | $\\ge 90.0$% |
| Prompt Injection Detection Rate | {metrics["injection_detection_rate"]:.1f}% | 100.0% |

## Evaluation Environment
- Provider: FakeLLMClient (offline plumbing mode)
- Prompt Version: `claims-fnol-extract-v1`
- Heuristic Interceptor: G7 Rule-Based Scanner Active
"""
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\nReport written to: {report_file}")
    for k, v in metrics.items():
        print(f"  {k:30s}: {v:.1f}")

    return metrics


if __name__ == "__main__":
    asyncio.run(run_evaluation("dev"))
