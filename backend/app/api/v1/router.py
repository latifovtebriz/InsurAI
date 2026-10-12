"""Master API v1 router combining all domain endpoints."""

from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.claims import router as claims_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.policies import router as policies_router
from app.api.v1.sales import router as sales_router
from app.api.v1.traces import router as traces_router
from app.api.v1.underwriting import router as underwriting_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(policies_router)
api_v1_router.include_router(sales_router)
api_v1_router.include_router(underwriting_router)
api_v1_router.include_router(claims_router)
api_v1_router.include_router(traces_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(metrics_router)
