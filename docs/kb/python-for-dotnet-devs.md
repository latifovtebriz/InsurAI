# Python for .NET Developers (Cheat Sheet)

| Concept | Python / FastAPI / Ecosystem | .NET / C# / ASP.NET Core | Comparison & Gotchas |
|---|---|---|---|
| Web Framework | FastAPI | ASP.NET Core Web API | FastAPI uses type hints for automatic Swagger/OpenAPI docs and validation. |
| DTO / Validation | Pydantic Models (`BaseModel`) | Records / Classes + FluentValidation | Pydantic parses and coerces types automatically at runtime. |
| ORM | SQLAlchemy 2.0 | Entity Framework Core (EF Core) | SQLAlchemy uses explicit sessions and DeclarativeBase models; sync/async separation is explicit. |
| Migrations | Alembic | EF Core Migrations | Alembic auto-generates migrations from SQLAlchemy metadata. |
| Dependency Injection | FastAPI `Depends()` | Built-in `IServiceProvider` | In FastAPI, DI is resolved per-route parameter rather than constructor-injected. |
| Test Framework | `pytest` | `xUnit` / `NUnit` | `pytest` uses plain `assert` statements and fixtures instead of class inheritance. |
| Architecture Tests | `import-linter` | `NetArchTest` | Enforces that modules only communicate via `public.py`. |
| Package Management | `uv` / `pyproject.toml` | NuGet / `.csproj` | `uv` provides ultra-fast resolution and virtualenv management. |
| Linters & Formatters | `ruff`, `mypy` | Roslyn Analyzers, StyleCop | `ruff` replaces Black, Flake8, and isort in Rust. `mypy` is static type checker. |
| Configuration | `pydantic-settings` | `appsettings.json` + `IOptions<T>` | Validates environment variables into typed configuration objects. |
