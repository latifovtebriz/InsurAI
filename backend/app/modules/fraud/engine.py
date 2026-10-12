"""Rule-based transparent fraud risk scoring engine with Guardrail G9 fairness enforcement."""

from datetime import date
from decimal import Decimal
from typing import Any

FORBIDDEN_DEMOGRAPHIC_ATTRIBUTES = {
    "race",
    "ethnicity",
    "gender",
    "religion",
    "nationality",
    "marital_status",
    "zip_code",
    "postal_code",
    "sexual_orientation",
}


FRAUD_SIGNAL_DEFINITIONS = [
    {
        "code": "FS-01",
        "name": "Early Claim Inception Window",
        "weight": 25,
        "description": "Claim occurred within 14 days of policy binding date.",
    },
    {
        "code": "FS-02",
        "name": "Disproportionate Claim Severity",
        "weight": 20,
        "description": "Claimed amount exceeds 80% of total policy sum insured.",
    },
    {
        "code": "FS-03",
        "name": "Frequency Anomaly (Repeat Claims)",
        "weight": 30,
        "description": "Two or more prior claims submitted within preceding 180 days.",
    },
    {
        "code": "FS-04",
        "name": "Absence of Official Police Protocol",
        "weight": 15,
        "description": "No formal traffic police / authority accident protocol submitted for collision.",
    },
    {
        "code": "FS-05",
        "name": "Delayed Notification Window",
        "weight": 15,
        "description": "Notification submitted more than 3 business days after incident date.",
    },
    {
        "code": "FS-06",
        "name": "Nighttime Single-Vehicle Incident",
        "weight": 10,
        "description": "Incident occurred between 01:00 and 05:00 with no independent third-party witnesses.",
    },
]


class FairnessViolationError(ValueError):
    """Raised by Guardrail G9 when forbidden demographic attributes are passed to fraud scoring."""

    pass


def evaluate_fraud_signals(
    policy_start_date: date,
    incident_date: date,
    notification_date: date,
    claimed_amount: Decimal,
    sum_insured: Decimal,
    prior_claims_count: int = 0,
    has_police_report: bool = True,
    incident_hour: int | None = None,
    unwitnessed_single_vehicle: bool = False,
    metadata: dict[str, Any] | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """
    Computes transparent, explainable fraud score (0-100) and triggered signal set.
    Strictly verifies Guardrail G9 (no protected demographic attributes).
    """
    # Guardrail G9 Fairness Check
    if metadata:
        for key in metadata:
            if key.lower() in FORBIDDEN_DEMOGRAPHIC_ATTRIBUTES:
                raise FairnessViolationError(
                    f"Guardrail G9 violation: Protected demographic attribute '{key}' cannot be used in fraud risk scoring."
                )

    triggered_signals: list[dict[str, Any]] = []

    # FS-01: Early claim
    days_from_start = (incident_date - policy_start_date).days
    if 0 <= days_from_start <= 14:
        triggered_signals.append(
            {
                "code": "FS-01",
                "name": "Early Claim Inception Window",
                "weight": 25,
                "description": f"Incident occurred {days_from_start} day(s) after policy inception.",
            }
        )

    # FS-02: High severity ratio
    if sum_insured > Decimal("0.00") and (claimed_amount / sum_insured) >= Decimal("0.80"):
        severity_pct = float(round((claimed_amount / sum_insured) * 100, 1))
        triggered_signals.append(
            {
                "code": "FS-02",
                "name": "Disproportionate Claim Severity",
                "weight": 20,
                "description": f"Claimed amount represents {severity_pct}% of total sum insured.",
            }
        )

    # FS-03: Repeat claims
    if prior_claims_count >= 2:
        triggered_signals.append(
            {
                "code": "FS-03",
                "name": "Frequency Anomaly (Repeat Claims)",
                "weight": 30,
                "description": f"{prior_claims_count} prior claims recorded within past term.",
            }
        )

    # FS-04: Missing police report
    if not has_police_report:
        triggered_signals.append(
            {
                "code": "FS-04",
                "name": "Absence of Official Police Protocol",
                "weight": 15,
                "description": "Official traffic police report or formal authority documentation is missing.",
            }
        )

    # FS-05: Late notification
    notification_delay = (notification_date - incident_date).days
    if notification_delay > 3:
        triggered_signals.append(
            {
                "code": "FS-05",
                "name": "Delayed Notification Window",
                "weight": 15,
                "description": f"FNOL submitted {notification_delay} days post-incident (exceeds 3-day window).",
            }
        )

    # FS-06: Nighttime single vehicle
    if incident_hour is not None and (1 <= incident_hour <= 5) and unwitnessed_single_vehicle:
        triggered_signals.append(
            {
                "code": "FS-06",
                "name": "Nighttime Single-Vehicle Incident",
                "weight": 10,
                "description": f"Occurred at {incident_hour:02d}:00 without independent witness corroboration.",
            }
        )

    total_score = min(100, sum(s["weight"] for s in triggered_signals))
    return total_score, triggered_signals
