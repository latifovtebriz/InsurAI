"""Agent A5: Fraud Investigator Assistant / SIU Copilot with Guardrail G8 neutral language enforcement."""

import re
from typing import Any

from app.modules.platform.public import (
    GuardrailPipeline,
    ToolCategory,
    ToolDefinition,
    ToolRegistry,
    guardrail_pipeline,
)
from pydantic import BaseModel, Field

FORBIDDEN_ACCUSATORY_TERMS = [
    r"\bfraud\b",
    r"\bfraudulent\b",
    r"\bfraudster\b",
    r"\bcriminal\b",
    r"\bcrime\b",
    r"\bscam\b",
    r"\bstaged\b",
    r"\bliar\b",
    r"\blies\b",
    r"\bcheating\b",
    r"\bfake\b",
    r"\bfabricated\b",
    r"\bguilty\b",
    r"\billegal\b",
]

NEUTRAL_REPLACEMENTS = {
    "fraud": "potential inconsistency",
    "fraudulent": "unverified",
    "fraudster": "claimant under review",
    "criminal": "party requiring review",
    "crime": "procedural discrepancy",
    "scam": "anomaly",
    "staged": "unwitnessed or unusual incident pattern",
    "liar": "claimant with conflicting statements",
    "lies": "discrepancies in testimony",
    "cheating": "non-conforming documentation",
    "fake": "unsubstantiated",
    "fabricated": "unsubstantiated",
    "guilty": "inconsistent with standard patterns",
    "illegal": "subject to regulatory review",
}


def sanitize_neutral_language(text: str) -> str:
    """
    Guardrail G8: Sanitizes text by replacing accusatory terminology with objective, neutral phrasing.
    """
    sanitized = text
    for pattern in FORBIDDEN_ACCUSATORY_TERMS:
        matches = re.findall(pattern, sanitized, re.IGNORECASE)
        for match in set(matches):
            replacement = NEUTRAL_REPLACEMENTS.get(match.lower(), "observed discrepancy")
            sanitized = re.sub(
                r"\b" + re.escape(match) + r"\b", replacement, sanitized, flags=re.IGNORECASE
            )
    return sanitized


def validate_neutral_language(text: str) -> tuple[bool, list[str]]:
    """
    Returns False and list of detected violations if text contains forbidden accusatory terms.
    """
    violations: list[str] = []
    for pattern in FORBIDDEN_ACCUSATORY_TERMS:
        found = re.findall(pattern, text, re.IGNORECASE)
        if found:
            violations.extend(found)
    return len(violations) == 0, list(set(violations))


class GetClaimTimelineArgs(BaseModel):
    claim_number: str = Field(description="Claim number to review")


class GetPartyRelationsArgs(BaseModel):
    party_id: str = Field(description="Party UUID to check cross-claim link analysis")


class FlagAnomalyArgs(BaseModel):
    claim_number: str = Field(description="Claim number")
    anomaly_type: str = Field(
        description="Category of anomaly: TIMELINE, DOCUMENTATION, SEVERITY, RELATION"
    )
    explanation: str = Field(description="Neutral description of observed discrepancy")


class SIUAnomalyAssessment(BaseModel):
    claim_number: str
    risk_score: int
    signals_detected: list[dict[str, Any]]
    timeline_summary: str
    cross_claim_notes: str
    neutral_findings_summary: str
    g8_neutral_language_verified: bool
    recommended_siu_action: str


class FraudAssistantAgent:
    """Agent A5: Analyzes high-risk claims, generates objective anomaly summaries using Guardrail G8 neutral language."""

    def __init__(self, guardrails: GuardrailPipeline = guardrail_pipeline) -> None:
        self.guardrails = guardrails
        self.tool_registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self) -> None:
        def _timeline_handler(args: GetClaimTimelineArgs) -> dict[str, Any]:
            return {
                "claim_number": args.claim_number,
                "policy_bound": "2026-01-01",
                "incident_occurred": "2026-01-08 (T+7 days)",
                "fnol_notified": "2026-01-14 (T+6 days notification delay)",
                "observation": "Inception-to-loss duration is 7 calendar days; FNOL reported with 6-day notification interval.",
            }

        def _relations_handler(args: GetPartyRelationsArgs) -> dict[str, Any]:
            return {
                "party_id": args.party_id,
                "prior_claims_count_180d": 2,
                "shared_driver_occurrences": 1,
                "cross_policy_relationships": "Party associated with 2 prior property damage claims in past 6 months.",
            }

        def _anomaly_handler(args: FlagAnomalyArgs) -> dict[str, Any]:
            # Enforce Guardrail G8 on input explanation
            sanitized_explanation = sanitize_neutral_language(args.explanation)
            return {
                "claim_number": args.claim_number,
                "anomaly_type": args.anomaly_type,
                "recorded_explanation": sanitized_explanation,
                "status": "flagged_for_investigator",
            }

        self.tool_registry.register(
            ToolDefinition(
                name="get_claim_timeline",
                description="Retrieves chronological timeline of policy inception, loss date, and notification date.",
                parameters_schema=GetClaimTimelineArgs,
                category=ToolCategory.READ,
                handler=_timeline_handler,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="get_party_relations",
                description="Checks cross-claim frequency and multi-claim relationships across policies.",
                parameters_schema=GetPartyRelationsArgs,
                category=ToolCategory.READ,
                handler=_relations_handler,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="flag_anomaly",
                description="Records an objective discrepancy for special investigation review using neutral phrasing.",
                parameters_schema=FlagAnomalyArgs,
                category=ToolCategory.PROPOSE,
                handler=_anomaly_handler,
            )
        )

    def assess_claim_for_siu(
        self,
        claim_number: str,
        risk_score: int,
        triggered_signals: list[dict[str, Any]],
        investigator_notes: str = "",
    ) -> SIUAnomalyAssessment:
        """
        Synthesizes objective SIU dossier with Guardrail G8 neutral language enforcement.
        """
        # Execute tools
        timeline_tool = self.tool_registry.get("get_claim_timeline")
        timeline_data = (
            timeline_tool.execute({"claim_number": claim_number}) if timeline_tool else {}
        )

        relations_tool = self.tool_registry.get("get_party_relations")
        relations_data = relations_tool.execute({"party_id": "PARTY-REF"}) if relations_tool else {}

        raw_summary = (
            f"Review of claim {claim_number} shows an overall risk score of {risk_score}/100. "
            f"{len(triggered_signals)} risk signal(s) noted: {', '.join(s['name'] for s in triggered_signals)}. "
            f"Timeline check: {timeline_data.get('observation', 'Timeline verified')}. "
            f"History check: {relations_data.get('cross_policy_relationships', 'Standard history')}. "
            f"Notes: {investigator_notes if investigator_notes else 'Standard verification recommended.'}"
        )

        # Enforce Guardrail G8: Neutral Language
        sanitized_summary = sanitize_neutral_language(raw_summary)
        is_neutral, violations = validate_neutral_language(sanitized_summary)

        if risk_score >= 70:
            recommended_action = "Escalate to Field SIU Investigator for document corroboration."
        elif risk_score >= 40:
            recommended_action = "Request original police report and independent repair estimate."
        else:
            recommended_action = "Proceed with standard claims adjudication."

        return SIUAnomalyAssessment(
            claim_number=claim_number,
            risk_score=risk_score,
            signals_detected=triggered_signals,
            timeline_summary=timeline_data.get("observation", "Timeline normal"),
            cross_claim_notes=relations_data.get("cross_policy_relationships", "No anomalies"),
            neutral_findings_summary=sanitized_summary,
            g8_neutral_language_verified=is_neutral,
            recommended_siu_action=recommended_action,
        )


fraud_assistant_agent = FraudAssistantAgent()
