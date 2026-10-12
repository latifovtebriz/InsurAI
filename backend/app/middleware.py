"""Correlation ID and observability middleware."""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

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


class MaxPayloadSizeMiddleware(BaseHTTPMiddleware):
    """Rejects incoming HTTP requests whose Content-Length exceeds max allowed bytes (default 10MB)."""

    def __init__(self, app: Any, max_size_bytes: int = 10 * 1024 * 1024) -> None:
        super().__init__(app)
        self.max_size_bytes = max_size_bytes

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_size_bytes:
                    return Response(
                        content='{"detail":"Payload too large: request body exceeds 10MB limit"}',
                        status_code=413,
                        media_type="application/json",
                    )
            except ValueError:
                pass

        return await call_next(request)
