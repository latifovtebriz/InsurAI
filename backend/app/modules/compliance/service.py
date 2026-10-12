"""Compliance screening service and alert adjudication workflows."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.modules.compliance.matcher import ensure_watchlist_seed, screen_entity
from app.modules.compliance.models import ComplianceAlert
from app.modules.platform.public import publish_outbox_event, record_audit_event
from sqlalchemy import select
from sqlalchemy.orm import Session


def utcnow() -> datetime:
    return datetime.now(UTC)


class ComplianceService:
    """Manages AML/sanctions screening, watchlist matching, and human officer adjudication."""

    def screen_party(
        self,
        session: Session,
        party_id: str,
        party_name: str,
        tax_id: str | None = None,
        user_id: str | None = None,
    ) -> list[ComplianceAlert]:
        """
        Screens party against sanctions watchlist.
        Creates ComplianceAlert records for any hit with match_score >= 0.65.
        """
        watchlist = ensure_watchlist_seed(session)
        matches = screen_entity(name=party_name, tax_id=tax_id, watchlist=watchlist, threshold=0.65)
        alerts: list[ComplianceAlert] = []

        for m in matches:
            # Check existing alert for this party and watchlist entity
            existing = session.scalars(
                select(ComplianceAlert).where(
                    ComplianceAlert.party_id == party_id,
                    ComplianceAlert.matched_entity_id == m["watchlist_id"],
                )
            ).first()
            if existing:
                alerts.append(existing)
                continue

            random_suffix = uuid.uuid4().hex[:6].upper()
            alert_num = f"CMP-{datetime.now(UTC).strftime('%Y%m%d')}-{random_suffix}"

            alert = ComplianceAlert(
                alert_number=alert_num,
                party_id=party_id,
                party_name=party_name,
                matched_entity_id=m["watchlist_id"],
                matched_entity_name=m["matched_name"],
                match_score=Decimal(str(m["match_score"])),
                match_reasons=m["reasons"],
                status="open",
            )
            session.add(alert)
            session.flush()

            record_audit_event(
                session=session,
                action="compliance_alert_raised",
                entity_type="compliance_alert",
                entity_id=alert.id,
                after_state={
                    "alert_number": alert.alert_number,
                    "matched_entity": m["matched_name"],
                    "match_score": str(m["match_score"]),
                },
                user_id=user_id,
            )

            publish_outbox_event(
                session=session,
                event_type="ComplianceAlertRaisedEvent",
                aggregate_type="compliance_alert",
                aggregate_id=alert.id,
                payload={
                    "alert_number": alert.alert_number,
                    "party_name": party_name,
                    "matched_name": m["matched_name"],
                    "match_score": str(m["match_score"]),
                },
            )

            alerts.append(alert)

        session.flush()
        return alerts

    def adjudicate_alert(
        self,
        session: Session,
        alert_id: str,
        decision: str,
        officer_id: str,
        decision_notes: str,
        user_id: str | None = None,
    ) -> ComplianceAlert:
        """
        Human compliance officer adjudication: confirmed_hit or false_positive_cleared_by_officer.
        """
        valid_decisions = {"confirmed_hit", "false_positive_cleared_by_officer", "under_review"}
        if decision not in valid_decisions:
            raise ValueError(f"Invalid decision '{decision}'. Must be one of {valid_decisions}.")

        alert = session.get(ComplianceAlert, alert_id)
        if not alert:
            raise ValueError(f"Compliance alert '{alert_id}' not found.")

        old_status = alert.status
        alert.status = decision
        alert.assigned_officer_id = officer_id
        alert.officer_decision_notes = decision_notes
        alert.decided_at = utcnow()

        record_audit_event(
            session=session,
            action="compliance_alert_adjudicated",
            entity_type="compliance_alert",
            entity_id=alert.id,
            before_state={"status": old_status},
            after_state={
                "status": decision,
                "officer": officer_id,
                "notes": decision_notes,
            },
            user_id=user_id,
        )

        session.flush()
        return alert


compliance_service = ComplianceService()
