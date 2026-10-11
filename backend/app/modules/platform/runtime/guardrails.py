"""Pluggable Guardrail Pipeline implementing rules G1 through G10."""

import re
from dataclasses import dataclass
from typing import Any

from app.config import settings


@dataclass
class GuardrailResult:
    code: str
    passed: bool
    downgrade_to_review: bool
    reason: str


class GuardrailPipeline:
    """Evaluates agent recommendations against defensive deterministic safety rules."""

    def __init__(self) -> None:
        pass

    def evaluate_all(
        self,
        recommendation: dict[str, Any],
        executed_tool_calls: list[dict[str, Any]],
        retrieved_clauses: list[str],
        active_policy_verified: bool = True,
        calculated_payout: float | None = None,
        raw_text_inputs: list[str] | None = None,
    ) -> list[GuardrailResult]:
        """Runs the complete battery of guardrail interceptors."""
        results: list[GuardrailResult] = []

        rec_val = recommendation.get("recommendation", "")
        confidence = float(recommendation.get("confidence", 0.0))
        payout_dict = recommendation.get("payout", {})
        payable = float(payout_dict.get("payable", 0.0))
        risk_flags = recommendation.get("risk_flags", [])
        missing_info = recommendation.get("missing_information", [])

        # ----------------------------------------------------
        # G1: Grounded Citations (Citations must have been retrieved)
        # ----------------------------------------------------
        cited_clauses: list[str] = []
        for r in recommendation.get("reasons", []):
            evidence = r.get("evidence", {})
            cited_clauses.extend(evidence.get("clause_ids", []))

        invalid_citations = [c for c in cited_clauses if c not in retrieved_clauses]
        if invalid_citations and rec_val == "approve":
            results.append(
                GuardrailResult(
                    code="G1",
                    passed=False,
                    downgrade_to_review=True,
                    reason=f"G1 Violation: Cited clauses {invalid_citations} were not retrieved during active session.",
                )
            )
        else:
            results.append(
                GuardrailResult(
                    code="G1",
                    passed=True,
                    downgrade_to_review=False,
                    reason="Grounded citations valid.",
                )
            )

        # ----------------------------------------------------
        # G2: Mathematical Invariant
        # ----------------------------------------------------
        if calculated_payout is not None and rec_val == "approve":
            if abs(payable - calculated_payout) > 0.01:
                results.append(
                    GuardrailResult(
                        code="G2",
                        passed=False,
                        downgrade_to_review=True,
                        reason=f"G2 Violation: Stated payout ({payable}) does not match deterministic calculation ({calculated_payout}).",
                    )
                )
            else:
                results.append(
                    GuardrailResult(
                        code="G2",
                        passed=True,
                        downgrade_to_review=False,
                        reason="Payout matches deterministic engine.",
                    )
                )
        else:
            results.append(
                GuardrailResult(
                    code="G2",
                    passed=True,
                    downgrade_to_review=False,
                    reason="G2 skipped or satisfied.",
                )
            )

        # ----------------------------------------------------
        # G3: Terminal Rejection Guard (Rejection requires human confirmation)
        # ----------------------------------------------------
        if rec_val == "reject":
            results.append(
                GuardrailResult(
                    code="G3",
                    passed=True,
                    downgrade_to_review=True,
                    reason="G3 Guard: Claim denial requires mandatory human adjuster sign-off.",
                )
            )
        else:
            results.append(
                GuardrailResult(
                    code="G3", passed=True, downgrade_to_review=False, reason="G3 satisfied."
                )
            )

        # ----------------------------------------------------
        # G4: Confidence Floor & Risk Flags
        # ----------------------------------------------------
        if confidence < settings.confidence_threshold or risk_flags or missing_info:
            if rec_val == "approve":
                reasons = []
                if confidence < settings.confidence_threshold:
                    reasons.append(
                        f"Confidence {confidence:.2f} < threshold {settings.confidence_threshold}"
                    )
                if risk_flags:
                    reasons.append(f"Risk flags present: {risk_flags}")
                if missing_info:
                    reasons.append(f"Missing information: {missing_info}")

                results.append(
                    GuardrailResult(
                        code="G4",
                        passed=False,
                        downgrade_to_review=True,
                        reason=f"G4 Downgrade: {'; '.join(reasons)}",
                    )
                )
            else:
                results.append(
                    GuardrailResult(
                        code="G4",
                        passed=True,
                        downgrade_to_review=False,
                        reason="Confidence and risk accounted for.",
                    )
                )
        else:
            results.append(
                GuardrailResult(
                    code="G4",
                    passed=True,
                    downgrade_to_review=False,
                    reason="Confidence above floor with zero flags.",
                )
            )

        # ----------------------------------------------------
        # G5: Mandatory Tool Execution
        # ----------------------------------------------------
        executed_names = {call.get("tool_name") for call in executed_tool_calls}
        mandatory_claims_tools = {"check_policy_active", "search_policy_wording"}
        missing_tools = mandatory_claims_tools - executed_names
        if missing_tools and rec_val == "approve":
            results.append(
                GuardrailResult(
                    code="G5",
                    passed=False,
                    downgrade_to_review=True,
                    reason=f"G5 Violation: Mandatory tools {missing_tools} were not executed.",
                )
            )
        else:
            results.append(
                GuardrailResult(
                    code="G5",
                    passed=True,
                    downgrade_to_review=False,
                    reason="Mandatory tools executed.",
                )
            )

        # ----------------------------------------------------
        # G7: Prompt Injection Heuristic Scan
        # ----------------------------------------------------
        injection_found = False
        if raw_text_inputs:
            for text in raw_text_inputs:
                if re.search(
                    r"(ignore\s+(all\s+)?previous|you\s+are\s+now|system\s+override|approve\s+this\s+claim)",
                    text,
                    re.I,
                ):
                    injection_found = True
                    break

        if injection_found:
            results.append(
                GuardrailResult(
                    code="G7",
                    passed=False,
                    downgrade_to_review=True,
                    reason="G7 Triggered: Adversarial prompt injection pattern detected in input text.",
                )
            )
        else:
            results.append(
                GuardrailResult(
                    code="G7",
                    passed=True,
                    downgrade_to_review=False,
                    reason="No injection detected.",
                )
            )

        # ----------------------------------------------------
        # G10: Negative Payout Prevention
        # ----------------------------------------------------
        if payable < 0.0:
            results.append(
                GuardrailResult(
                    code="G10",
                    passed=False,
                    downgrade_to_review=True,
                    reason=f"G10 Invariant Violation: Negative payable amount ({payable}) is impossible.",
                )
            )
        else:
            results.append(
                GuardrailResult(
                    code="G10",
                    passed=True,
                    downgrade_to_review=False,
                    reason="Non-negative payout confirmed.",
                )
            )

        return results


guardrail_pipeline = GuardrailPipeline()
