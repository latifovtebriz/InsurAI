"""Policy administration endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.party.public import party_service
from app.modules.platform.public import require_permission
from app.modules.policy.public import Policy, PolicyCertificate

router = APIRouter(prefix="/policies", tags=["Policies"])


class PolicyListItem(BaseModel):
    id: str
    policy_number: str
    product_code: str
    status: str
    holder_name: str | None = None
    start_date: str
    end_date: str
    sum_insured: float
    total_premium: float
    paid_premium: float


class PolicyDetailResponse(BaseModel):
    id: str
    policy_number: str
    party_id: str
    asset_id: str
    product_code: str
    product_version_id: str
    status: str
    start_date: str
    end_date: str
    sum_insured: float
    deductible: float
    total_premium: float
    paid_premium: float
    payment_schedule: list[dict[str, Any]]
    certificate_hash: str | None = None
    holder_info: dict[str, Any] | None = None


@router.get("", response_model=list[PolicyListItem])
def list_policies(
    search: str | None = Query(None, description="Search by policy number or product"),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("policy:read")),
) -> list[PolicyListItem]:
    """Retrieves policies with filtering and pagination."""
    stmt = select(Policy)
    if status_filter:
        stmt = stmt.where(Policy.status == status_filter)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(Policy.policy_number.ilike(term), Policy.product_code.ilike(term)))
    stmt = stmt.order_by(Policy.created_at.desc()).offset(offset).limit(limit)

    policies = db.scalars(stmt).all()
    results: list[PolicyListItem] = []
    for pol in policies:
        party = party_service.get_party_by_id(db, pol.party_id)
        holder_name = (
            f"{party.first_name or ''} {party.last_name or ''}".strip() or party.company_name
            if party
            else None
        )
        results.append(
            PolicyListItem(
                id=pol.id,
                policy_number=pol.policy_number,
                product_code=pol.product_code,
                status=pol.status,
                holder_name=holder_name,
                start_date=pol.start_date.isoformat(),
                end_date=pol.end_date.isoformat(),
                sum_insured=float(pol.sum_insured),
                total_premium=float(pol.total_premium),
                paid_premium=float(pol.paid_premium),
            )
        )
    return results


@router.get("/{policy_number}", response_model=PolicyDetailResponse)
def get_policy_detail(
    policy_number: str,
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("policy:read")),
) -> PolicyDetailResponse:
    """Retrieves full details for a given policy number."""
    stmt = select(Policy).where(Policy.policy_number == policy_number)
    pol = db.scalars(stmt).first()
    if not pol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_number}' not found",
        )

    # Fetch certificate hash if issued
    cert_stmt = select(PolicyCertificate).where(PolicyCertificate.policy_id == pol.id)
    cert = db.scalars(cert_stmt).first()

    # Holder info
    party = party_service.get_party_by_id(db, pol.party_id)
    holder_info: dict[str, Any] | None = None
    if party:
        h_name = f"{party.first_name or ''} {party.last_name or ''}".strip() or party.company_name or ""
        holder_info = {
            "party_id": party.id,
            "full_name": h_name,
            "party_type": party.party_type,
            "tax_id": party.tax_id,
            "email": party.email,
            "phone": party.phone,
        }

    return PolicyDetailResponse(
        id=pol.id,
        policy_number=pol.policy_number,
        party_id=pol.party_id,
        asset_id=pol.asset_id,
        product_code=pol.product_code,
        product_version_id=pol.product_version_id,
        status=pol.status,
        start_date=pol.start_date.isoformat(),
        end_date=pol.end_date.isoformat(),
        sum_insured=float(pol.sum_insured),
        deductible=float(pol.deductible),
        total_premium=float(pol.total_premium),
        paid_premium=float(pol.paid_premium),
        payment_schedule=pol.payment_schedule,
        certificate_hash=cert.document_hash if cert else None,
        holder_info=holder_info,
    )
