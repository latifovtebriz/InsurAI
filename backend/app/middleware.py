"""Correlation ID and observability middleware."""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging import correlation_id_ctx


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that injects or propagates X-Correlation-ID headers."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        corr_id = request.headers.get("X-Correlation-ID")
        if not corr_id:
            corr_id = str(uuid.uuid4())

        token = correlation_id_ctx.set(corr_id)
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = corr_id
            return response
        finally:
            correlation_id_ctx.reset(token)
