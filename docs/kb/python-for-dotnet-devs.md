# Python for .NET / C# Developers (Enterprise Core Cheat Sheet)

This cheat sheet provides direct C# / .NET / ASP.NET Core architectural analogies for every concept implemented in InsurAI.

---

## 1. Core Framework & Language Mapping

| Concept | Python / InsurAI Stack | .NET / C# / ASP.NET Core | Comparison & Architectural Nuances |
|---|---|---|---|
| **Web Framework** | FastAPI | ASP.NET Core Minimal APIs / Controllers | FastAPI uses Python type hints for automatic Swagger/OpenAPI docs and runtime request validation. |
| **DTOs & Validation** | Pydantic (`BaseModel`, `Field`) | C# `record` + `FluentValidation` | Pydantic performs automatic parsing, validation, and JSON schema generation at runtime. |
| **ORM & Persistence** | SQLAlchemy 2.0 (`Mapped[...]`) | Entity Framework Core (EF Core) | SQLAlchemy uses explicit sessions and Unit of Work (`session.flush()`, `session.commit()`). |
| **Database Migrations** | Alembic | EF Core Migrations | Alembic compares SQLAlchemy `Base.metadata` against database tables to produce migration scripts. |
| **Dependency Injection** | FastAPI `Depends(get_db)` | `IServiceCollection` / Constructor DI | In FastAPI, DI is evaluated at the route handler signature rather than class constructors. |
| **Testing Framework** | `pytest` + fixtures | `xUnit` + `WebApplicationFactory` | `pytest` uses plain Python `assert` statements and dependency fixtures rather than test classes. |
| **Architecture Tests** | AST Architecture Tests (`ast.parse`) | `NetArchTest` / `ArchUnitNET` | Analyzes Abstract Syntax Trees to enforce that modules only communicate via `public.py`. |
| **Package Management** | `uv` + `pyproject.toml` | NuGet + `.csproj` / `Directory.Packages.props` | `uv` resolves and installs Python virtual environments in milliseconds (written in Rust). |
| **Linter & Code Analyzer** | `ruff` | Roslyn Analyzers / StyleCop | `ruff` enforces formatting and linting instantly (replaces Black, Flake8, isort). |
| **Static Type Checking** | `mypy --strict` | C# Roslyn Compiler | Python is dynamically typed at runtime, but `mypy` enforces strict compile-time type verification. |
| **Configuration** | `pydantic-settings` | `appsettings.json` + `IOptions<T>` | Binds environment variables into strongly-typed settings objects with default fallbacks. |

---

## 2. Enterprise Design Patterns in InsurAI vs .NET

### 2.1 Transactional Outbox Pattern
- **InsurAI**: Writes domain events to `platform.outbox_events` in the same database transaction as the business entity. A background worker polls with `SELECT ... FOR UPDATE SKIP LOCKED` and publishes to subscribers. Deduplication handled by `platform.processed_events`.
- **C# / .NET Analogy**: The **MassTransit Outbox** or **Wolverine Outbox** pattern, writing to an Outbox EF Core DbSet within `DbContext.SaveChangesAsync()` and relaying messages asynchronously to RabbitMQ/Kafka.

### 2.2 Double-Entry General Ledger Balance Invariant
- **InsurAI**: Centralized `LedgerEngine` enforces $|\sum Debits - \sum Credits| == Decimal("0.00")` across all 13 accounts before committing. Throws `LedgerImbalanceError`.
- **C# / .NET Analogy**: An EF Core `SaveChangesInterceptor` or Domain Service validating that the sum of debit line items equals credit line items inside a `TransactionScope`.

### 2.3 Prometheus Observability & Metrics
- **InsurAI**: Standard text exposition at `GET /metrics` formatted per Prometheus text specification 0.0.4.
- **C# / .NET Analogy**: The `prometheus-net.AspNetCore` middleware (`app.UseMetricServer("/metrics")`) or OpenTelemetry .NET metrics (`services.AddOpenTelemetry().WithMetrics(...)`).

### 2.4 DoS Payload Size Limiting
- **InsurAI**: `MaxPayloadSizeMiddleware` inspects `Content-Length` and rejects bodies > 10MB with HTTP 413.
- **C# / .NET Analogy**: Setting `KestrelServerOptions.Limits.MaxRequestBodySize = 10 * 1024 * 1024` or using the `[RequestSizeLimit(10_485_760)]` action attribute in ASP.NET Core.

### 2.5 Structured JSON Logging & PII Masking
- **InsurAI**: `JSONFormatter` in `app.logging` applies `sanitize_pii()` to scrub 16-digit PANs (`[REDACTED_PAN]`) and Bearer tokens (`[REDACTED_SECRET]`).
- **C# / .NET Analogy**: Configuring **Serilog** with custom `ILogEventFilter` or `DestructuringPolicy` (e.g. `Destructurama.Attributed`) to mask sensitive card numbers before sending logs to Elasticsearch/Datadog.

### 2.6 Agent ReAct Loop & Fail-Safe Fallbacks
- **InsurAI**: Hand-written ReAct loop with step budgets, loop detection, and fail-safe catch blocks routing errors to `needs_human_review`.
- **C# / .NET Analogy**: Using **Polly** with a `FallbackPolicy` and `CircuitBreakerPolicy` wrapping AI client calls to safeguard financial core transactions.
