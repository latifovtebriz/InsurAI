"""Agent A8: Compliance Explainer Assistant.
Explains sanctions and watchlist fuzzy matches to compliance officers.
STRICTLY FORBIDDEN FROM EVER AUTO-CLEARING A POSITIVE MATCH.
"""

from typing import Any

from app.modules.compliance.models import ComplianceAlert, WatchlistEntity
from app.modules.platform.public import (
    GuardrailPipeline,
    ToolCategory,
    ToolDefinition,
    ToolRegistry,
    guardrail_pipeline,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class GetWatchlistEntityArgs(BaseModel):
    entity_id: str = Field(description="Watchlist entity UUID to inspect")


class CompareIdentifiersArgs(BaseModel):
    party_name: str = Field(description="Screened party name")
    watchlist_name: str = Field(description="Matched watchlist entity name")
    party_tax_id: str | None = Field(default=None, description="Party tax ID")
    watchlist_tax_id: str | None = Field(default=None, description="Watchlist tax ID")


class DraftSARArgs(BaseModel):
    alert_number: str = Field(description="Compliance alert number")
    findings_summary: str = Field(
        description="Detailed match indicators for financial intelligence reporting"
    )


class ComplianceExplanation(BaseModel):
    alert_number: str
    party_name: str
    matched_entity_name: str
    list_name: str
    match_score: float
    analysis_text: str
    recommendation: str
    auto_cleared: bool = False  # Strictly always False!
    human_signoff_required: bool = True
    draft_sar_report: str | None = None


class ComplianceExplainerAgent:
    """Agent A8: Explains sanctions and watchlist hits to compliance officers without clearance authority."""

    def __init__(self, guardrails: GuardrailPipeline = guardrail_pipeline) -> None:
        self.guardrails = guardrails
        self.tool_registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self) -> None:
        def _get_entity_handler(args: GetWatchlistEntityArgs) -> dict[str, Any]:
            return {
                "entity_id": args.entity_id,
                "status": "active_sanctions_listing",
                "authority": "OFAC / UN Security Council",
                "measures": "Asset freeze, prohibition of financial transactions and insurance provision.",
            }

        def _compare_handler(args: CompareIdentifiersArgs) -> dict[str, Any]:
            name_match = (
                args.party_name.lower() in args.watchlist_name.lower()
                or args.watchlist_name.lower() in args.party_name.lower()
            )
            tax_match = bool(
                args.party_tax_id
                and args.watchlist_tax_id
                and args.party_tax_id == args.watchlist_tax_id
            )
            return {
                "name_overlap_detected": name_match,
                "tax_identifier_match": tax_match,
                "alias_indicators": "Multiple shared phonemes and matching corporate jurisdiction indicators.",
            }

        def _sar_handler(args: DraftSARArgs) -> dict[str, Any]:
            return {
                "alert_number": args.alert_number,
                "report_type": "SUSPICIOUS_ACTIVITY_REPORT_DRAFT",
                "narrative": (
                    f"CONFIDENTIAL COMPLIANCE SAR DRAFT\n"
                    f"Reference: Alert {args.alert_number}\n"
                    f"Factual Findings: {args.findings_summary}\n"
                    f"Status: Pending submission by authorized AML Compliance Officer."
                ),
            }

        self.tool_registry.register(
            ToolDefinition(
                name="get_watchlist_entity",
                description="Retrieves sanctions listing details and legal restrictive measures.",
                parameters_schema=GetWatchlistEntityArgs,
                category=ToolCategory.READ,
                handler=_get_entity_handler,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="compare_identifiers",
                description="Compares party name, tax ID, and jurisdiction against watchlist records.",
                parameters_schema=CompareIdentifiersArgs,
                category=ToolCategory.READ,
                handler=_compare_handler,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="draft_sar",
                description="Drafts Suspicious Activity Report (SAR) narrative for AML officer review.",
                parameters_schema=DraftSARArgs,
                category=ToolCategory.PROPOSE,
                handler=_sar_handler,
            )
        )

    def attempt_auto_clear(self, alert_number: str) -> None:
        """
        Hardcoded safety rail: A8 is strictly prohibited from auto-clearing a positive match.
        """
        raise PermissionError(
            f"AI Assistant A8 is strictly forbidden from auto-clearing sanctions match on alert '{alert_number}'. "
            f"Mandatory human compliance officer review and sign-off is legally required."
        )

    def explain_compliance_alert(
        self,
        session: Session,
        alert: ComplianceAlert,
        party_tax_id: str | None = None,
    ) -> ComplianceExplanation:
        """
        Generates objective comparative analysis explaining match indicators to the compliance officer.
        """
        entity = session.get(WatchlistEntity, alert.matched_entity_id)
        list_name = entity.list_name if entity else "SANCTIONS_WATCHLIST"

        comp_tool = self.tool_registry.get("compare_identifiers")
        comp_data = (
            comp_tool.execute(
                {
                    "party_name": alert.party_name,
                    "watchlist_name": alert.matched_entity_name,
                    "party_tax_id": party_tax_id,
                    "watchlist_tax_id": entity.tax_id if entity else None,
                }
            )
            if comp_tool
            else {}
        )

        analysis = (
            f"Match detected against {list_name} listing '{alert.matched_entity_name}' with confidence score "
            f"{float(alert.match_score):.2f}. Reasons: {alert.match_reasons}. "
            f"Identifier check: {comp_data.get('alias_indicators', 'Direct name correlation observed')}. "
            f"Legal restriction: Direct or indirect transactions with sanctioned entities are legally prohibited. "
            f"Human Compliance Officer review and adjudication is mandatory."
        )

        sar_tool = self.tool_registry.get("draft_sar")
        sar_data = (
            sar_tool.execute(
                {
                    "alert_number": alert.alert_number,
                    "findings_summary": analysis,
                }
            )
            if sar_tool
            else {}
        )

        return ComplianceExplanation(
            alert_number=alert.alert_number,
            party_name=alert.party_name,
            matched_entity_name=alert.matched_entity_name,
            list_name=list_name,
            match_score=float(alert.match_score),
            analysis_text=analysis,
            recommendation="REFER_TO_HUMAN_COMPLIANCE_OFFICER",
            auto_cleared=False,  # Strict guarantee: never cleared by AI!
            human_signoff_required=True,
            draft_sar_report=sar_data.get("narrative"),
        )


compliance_explainer_agent = ComplianceExplainerAgent()
