# Phase 0 Package: Foundation, Tooling, and Architecture Skeleton

## 1. Status
- **Phase:** Phase 0 (Foundation, Tooling, Git)
- **Status:** COMPLETED
- **Completed Tasks:**
  - Task 0.0: Git initialization, `.gitignore` configuration, proof of `.env` exclusion, initial commit.
  - Task 0.1: Repository layout per Section 3.17 with 12 isolated bounded contexts and `public.py` boundaries.
  - Task 0.2: Python 3.12+ / 3.13 backend skeleton with FastAPI, Pydantic settings, `/health`, `/ready`, JSON logging, correlation ID middleware.
  - Task 0.3: `docker-compose.yml` with PostgreSQL 16 + pgvector, backend service, and placeholder Vite React frontend.
  - Task 0.4: Quality gates configured (`ruff`, `mypy`, `pytest`, `scripts/secret_scanner.py`, `.pre-commit-config.yaml`).
  - Task 0.5: GitHub Actions CI workflow (`.github/workflows/ci.yml`).
  - Task 0.6: Knowledge base initialized in `docs/kb/`, ADR-001, ADR-010, `PROGRESS.md`.
  - Task 0.7: Initial README.md with quick-start guides and architectural overview.

---

## 2. What Was Built & Key Files
- `backend/app/main.py`: Core FastAPI application with middleware and health probes.
- `backend/app/config.py`: Environment-driven settings with Pydantic Settings.
- `backend/app/logging.py` & `middleware.py`: Structured JSON logger with async `X-Correlation-ID` tracking.
- `backend/app/db.py`: SQLAlchemy database engine and connectivity checker.
- `backend/app/modules/*/public.py`: 12 encapsulated module boundaries.
- `backend/tests/architecture/test_module_boundaries.py`: AST-based architecture test enforcing that modules only import through `public.py`.
- `backend/tests/unit/test_health.py`: Unit tests for `/health` and `/ready`.
- `scripts/secret_scanner.py`: Pre-push hygiene and high-entropy secret scanner.
- `docker-compose.yml`: Multi-container setup (Postgres + pgvector, backend, frontend).

---

## 3. How to Run and Verify
```powershell
# 1. Activate environment
.venv\Scripts\activate

# 2. Run secret scanner
python scripts/secret_scanner.py

# 3. Run linters & type checker
ruff check .
mypy backend/app

# 4. Run test suite
pytest
```

---

## 4. Quality Report
- **Unit Tests:** 3 passed (`test_health.py`).
- **Architecture Tests:** 2 passed (`test_module_boundaries.py` including deliberate violation test).
- **Ruff Linter:** 0 errors across all source files.
- **Mypy Type Checker:** 0 issues found in 32 source files.
- **Secret Scan:** PASSED (no tracked secrets, `.env` properly ignored).

---

## 5. Pre-Push Security Checklist (Appendix C)
- [x] `git status` shows no `.env`, key, certificate, dump, log, or trace files staged.
- [x] No tokens, passwords, API keys, or connection strings with real passwords.
- [x] Secret scan passes (`python scripts/secret_scanner.py`).
- [x] `.env.example` contains only empty or obviously fake values.
- [x] Test fixtures contain synthetic data only.
- [x] `docker-compose.yml` uses environment variable defaults with change_me credentials.
- [x] `git check-ignore -v .env` reports `.gitignore:2:.env .env`.

---

## 6. İzahlar (Azərbaycan dilində və C# Analoqları ilə)

### Nə etdik və Niyə belə etdik?
Phase 0-da layihənin təməlini qurduq. Sığorta kimi ciddi requlyasiya olunan və maliyyə məsuliyyəti daşıyan sistemlərdə arxitektura sərhədləri (bounded contexts) və təhlükəsizlik əvvəlcədən təmin olunmalıdır.
1. **Modular Monolith:** 12 müstəqil domen modulu (`claims`, `policy`, `party`, `product`, `finance` və s.) yaratdıq. Hər modulun öz `public.py` faylı var.
2. **Architecture Tests:** Bir modulun digər modulun daxili fayllarına birbaşa müraciət etməsini qadağan edən avtomatlaşdırılmış test yazdıq.

### C# / .NET Analoqları:
- **FastAPI vs ASP.NET Core:** FastAPI Python dünyasında ASP.NET Core Minimal API-yə bənzəyir. Tip annotasiyaları əsasında həm avtomatik Swagger/OpenAPI sənədləşməsi yaradır, həm də request-ləri validate edir.
- **Pydantic vs DTO + FluentValidation:** `pydantic-settings` və Pydantic modelləri C#-dakı `record` və `IOptions<T>` konfiqurasiya modelinin qarışığıdır.
- **import-linter vs NetArchTest:** C#-da NetArchTest kitabxanası ilə `Types().That().ResideInNamespace("Claims").ShouldNot().HaveDependencyOn("Finance.Internal")` qaydaları yazırıq. Biz bu qaydanı Python-da AST üzərində işləyən avtomatik arxitektura testi ilə reallaşdırdıq.
- **uv vs NuGet/dotnet CLI:** `uv` aləti Rust dilində yazılmış ultra-sürətli paket meneceridir. `dotnet restore` kimi saniyələr ərzində asılılıqları quraşdırır.

---

## 7. Interview Sentences (English)
1. "In Phase 0, I established a Modular Monolith architecture enforcing strict domain boundaries across 12 insurance bounded contexts using AST-based architecture tests."
2. "I implemented health and readiness probes in FastAPI with structured JSON logging and asynchronous correlation ID tracking across request lifecycles."
3. "To guarantee supply chain and repository safety from day one, I developed a pre-push secret scanner and automated CI pipeline verifying strict type safety and zero secret leakage."

---

## 8. Five Self-Check Questions

1. **Concept:** Why do we forbid direct imports of internal models between modules and enforce communication only via `public.py`?
2. **Code Reading:** How does `CorrelationIdMiddleware` ensure correlation IDs are propagated in asynchronous request contexts?
3. **Design Trade-off:** Why did we choose a Modular Monolith with schema-per-module isolation instead of a distributed microservice architecture?
4. **Failure Scenario:** What happens to the `/ready` probe if PostgreSQL becomes unreachable, and why does this matter for Kubernetes/Docker orchestration?
5. **What would you change:** In a production Kubernetes deployment, how would the health and readiness probes differ from the local Docker Compose setup?

---

### Hidden Answers:
<!--
Answers:
1. Enforcing public.py prevents tight coupling and "spaghetti dependencies". It allows modules to refactor their internal database tables or services without breaking other domains, preserving clean DDD bounded contexts.
2. It uses Python's `contextvars.ContextVar`, which maintains isolated, task-local storage across asynchronous coroutines without thread contention.
3. Microservices introduce network overhead, distributed transactions (two-phase commit issues), and operational overhead. A Modular Monolith gives the clean boundary benefits of microservices with the transactional reliability and atomic deployments of a single codebase.
4. It returns HTTP 503 Service Unavailable, signaling container orchestrators to stop routing traffic to this instance until dependencies recover.
5. In production, /ready would also inspect read-replica lag, connection pool saturation, and cache readiness, with distinct timeouts to prevent cascading failure storms.
-->

---

## 8b. Known Limitations & Next-Phase Preview
- **Limitations:** Database container is not running locally due to Docker Desktop daemon inactivity; integration tests for PostgreSQL are marked and will run when Docker is started.
- **Next Phase (Phase 1):** Domain model, synthetic data generation, and deterministic ground-truth labels for 150+ insurance scenarios (Motor OD, Motor TPL, and Home).
