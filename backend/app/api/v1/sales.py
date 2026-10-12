"""Sales and quotation endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.platform.public import require_permission
from app.modules.sales.public import (
    Quote,
    quote_assistant_agent,
    sales_service,
)

router = APIRouter(prefix="/sales", tags=["Sales & Quotation"])


class CreateQuoteRequest(BaseModel):
    product_code: str = "MOTOR_OD"
    vehicle_value: float = 30000.0
    vehicle_age: int = 2
    driver_age: int = 30
    prior_claims_count: int = 0
    deductible: float = 200.0
    lead_id: str | None = None
    party_id: str | None = None


class QuoteSummaryResponse(BaseModel):
    id: str
    quote_number: str
    product_code: str
    status: str
    sum_insured: float
    total_premium: float
    valid_until: str
    underwriting_case_id: str | None = None
    created_at: str


class QuoteDetailResponse(BaseModel):
    id: str
    quote_number: str
    product_code: str
    status: str
    sum_insured: float
    deductible: float
    total_premium: float
    rating_inputs: dict[str, Any]
    breakdown: dict[str, Any]
    installment_options: list[dict[str, Any]]
    valid_until: str
    underwriting_case_id: str | None = None
    created_at: str


class ChatQuoteRequest(BaseModel):
    message: str


class ChatQuoteResponse(BaseModel):
    status: str
    message: str
    missing_fields: list[str]
    extracted: dict[str, Any] | None = None
    quote_result: dict[str, Any] | None = None
    risk_flag: str | None = None


@router.post("/quotes", response_model=QuoteDetailResponse, status_code=status.HTTP_201_CREATED)
def create_quote(
    req: CreateQuoteRequest,
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("sales:read")),
) -> QuoteDetailResponse:
    """Generates an itemized insurance quote using deterministic rating."""
    rating_inputs = {
        "vehicle_value": req.vehicle_value,
        "vehicle_age": req.vehicle_age,
        "driver_age": req.driver_age,
        "prior_claims_count": req.prior_claims_count,
        "deductible": req.deductible,
    }
    quote = sales_service.generate_quote(
        db=db,
        product_code=req.product_code,
        rating_inputs=rating_inputs,
        lead_id=req.lead_id,
        party_id=req.party_id,
    )
    db.commit()

    return QuoteDetailResponse(
        id=quote.id,
        quote_number=quote.quote_number,
        product_code=quote.product_code,
        status=quote.status,
        sum_insured=float(quote.sum_insured),
        deductible=float(quote.deductible),
        total_premium=float(quote.total_premium),
        rating_inputs=quote.rating_inputs,
        breakdown=quote.breakdown,
        installment_options=quote.installment_options,
        valid_until=quote.valid_until.isoformat(),
        underwriting_case_id=quote.underwriting_case_id,
        created_at=quote.created_at.isoformat(),
    )


@router.get("/quotes", response_model=list[QuoteSummaryResponse])
def list_quotes(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("sales:read")),
) -> list[QuoteSummaryResponse]:
    """Lists quotes with optional status filtering."""
    stmt = select(Quote)
    if status_filter:
        stmt = stmt.where(Quote.status == status_filter)
    stmt = stmt.order_by(Quote.created_at.desc()).limit(limit)

    quotes = db.scalars(stmt).all()
    return [
        QuoteSummaryResponse(
            id=q.id,
            quote_number=q.quote_number,
            product_code=q.product_code,
            status=q.status,
            sum_insured=float(q.sum_insured),
            total_premium=float(q.total_premium),
            valid_until=q.valid_until.isoformat(),
            underwriting_case_id=q.underwriting_case_id,
            created_at=q.created_at.isoformat(),
        )
        for q in quotes
    ]


@router.get("/quotes/{quote_number}", response_model=QuoteDetailResponse)
def get_quote_detail(
    quote_number: str,
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("sales:read")),
) -> QuoteDetailResponse:
    """Retrieves full details of a quote."""
    stmt = select(Quote).where((Quote.quote_number == quote_number) | (Quote.id == quote_number))
    quote = db.scalars(stmt).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quote '{quote_number}' not found",
        )

    return QuoteDetailResponse(
        id=quote.id,
        quote_number=quote.quote_number,
        product_code=quote.product_code,
        status=quote.status,
        sum_insured=float(quote.sum_insured),
        deductible=float(quote.deductible),
        total_premium=float(quote.total_premium),
        rating_inputs=quote.rating_inputs,
        breakdown=quote.breakdown,
        installment_options=quote.installment_options,
        valid_until=quote.valid_until.isoformat(),
        underwriting_case_id=quote.underwriting_case_id,
        created_at=quote.created_at.isoformat(),
    )


@router.post("/quotes/{quote_number}/accept", response_model=QuoteDetailResponse)
def accept_quote(
    quote_number: str,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_permission("sales:read")),
) -> QuoteDetailResponse:
    """Accepts an offered quote."""
    try:
        quote = sales_service.accept_quote(
            db=db, quote_id=quote_number, actor_id=user.get("sub", "user")
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    return get_quote_detail(quote.quote_number, db=db, _user=user)


@router.post("/chat", response_model=ChatQuoteResponse)
def chat_with_quote_assistant(
    req: ChatQuoteRequest,
    _user: dict[str, Any] = Depends(require_permission("sales:read")),
) -> ChatQuoteResponse:
    """Interacts with Agent A1 (Quote Assistant) to gather info and explain quotes."""
    res = quote_assistant_agent.interact(user_message=req.message)
    return ChatQuoteResponse(
        status=res["status"],
        message=res["message"],
        missing_fields=res.get("missing_fields", []),
        extracted=res.get("extracted"),
        quote_result=res.get("quote_result"),
        risk_flag=res.get("risk_flag"),
    )
