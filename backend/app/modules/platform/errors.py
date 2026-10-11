"""RFC 7807 Problem Details format and idempotency handling."""

from typing import Any

from app.logging import correlation_id_ctx
from fastapi import status
from fastapi.responses import JSONResponse


class InsurAIException(Exception):
    """Base domain exception with RFC 7807 metadata."""

    def __init__(
        self,
        detail: str,
        title: str = "Domain Error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_type: str = "urn:insurai:error",
        invalid_params: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.title = title
        self.status_code = status_code
        self.error_type = error_type
        self.invalid_params = invalid_params or []


def create_problem_response(
    status_code: int,
    title: str,
    detail: str,
    instance: str,
    error_type: str = "about:blank",
    invalid_params: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """Formats an RFC 7807 compliant Problem Details JSON response."""
    payload: dict[str, Any] = {
        "type": error_type,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
        "correlation_id": correlation_id_ctx.get(),
    }
    if invalid_params:
        payload["invalid_params"] = invalid_params

    return JSONResponse(
        status_code=status_code,
        content=payload,
        headers={"Content-Type": "application/problem+json"},
    )
