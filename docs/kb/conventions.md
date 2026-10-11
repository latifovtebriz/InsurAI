# Engineering Conventions

1. **Monetary Precision:** Always use `Decimal` for financial quantities. Never use `float`. Amounts are rounded to 2 decimal places using `ROUND_HALF_UP`.
2. **Date and Time:** All database timestamps stored as UTC ISO 8601 strings or timezone-aware `datetime.datetime` in UTC (`datetime.now(datetime.timezone.utc)`).
3. **Module Interfaces:** Synchronous cross-module calls pass exclusively through `backend.app.modules.<module>.public`. Cross-schema DB queries or direct table imports are strictly forbidden.
4. **Error Responses:** APIs return RFC 7807 Problem Details (`{type, title, status, detail, instance, invalid_params}`).
5. **Correlation ID:** Every incoming HTTP request and agent execution propagates `X-Correlation-ID`.
6. **Logging:** Structured JSON logging via standard library `logging` or `structlog`.
