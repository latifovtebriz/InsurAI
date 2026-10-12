# Gotchas, Workarounds, and Environment Quirks

## 1. Environment Discovery (2026-10-12)

- **Operating System:** Windows (PowerShell shell).
- **Git:** `git version 2.45.1.windows.1`.
- **Python:** `Python 3.13.7` (64-bit).
- **Package Manager (`uv`):** `uv 0.13.0` installed via `python -m pip install --user uv`. Can be invoked via `python -m uv` or `.venv\Scripts\python`.
- **Node & NPM:** `node v20.17.0`, `npm 10.8.2`.
- **Docker:** `Docker version 29.1.3`, `Docker Compose v2.40.3-desktop.1`.
  - **Status:** Docker Desktop daemon is currently **not running** (`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`).
  - **Fallback:** Container files (`Dockerfile`, `docker-compose.yml`) are written. Unit tests and mocked tests run without external database. Integration tests requiring PostgreSQL/pgvector use `@pytest.mark.integration` and skip cleanly when no DB is available.

---

## 2. LLM Gateway & Offline Mode

- **LLM Status:** `LLM_API_KEY` is not provided (offline mode).
- **Implementation:** `LLMClient` protocol implemented with `FakeLLMClient` and `RecordReplayLLMClient`.
- **Gemini Client:** Google GenAI / Gemini client implementation written behind the interface. Marked: `UNVERIFIED AGAINST LIVE API` until live key is supplied.
- **Evaluation:** Offline eval reports marked `plumbing only, fake LLM, not a quality measurement`.

---

## 3. Windows Shell & Line Endings

- Git `.gitattributes` configured with `* text=auto` and `*.sh text eol=lf` to prevent CRLF line ending corruptions in bash and docker scripts.
- PowerShell command timeouts and non-interactive parameters (`--yes`, `-y`) enforced.

---

## 4. Dual Database Architecture & SQLite Schema Translation (`schema_translate_map`)

- **The Issue**: In PostgreSQL, InsurAI uses 12 schema namespaces (`platform`, `party`, `product`, `policy`, `sales`, `underwriting`, `claims`, `finance`, `fraud`, `compliance`, `service`, `reinsurance`). However, SQLite does not support PostgreSQL schemas and will crash with `sqlite3.OperationalError: unknown database platform`.
- **The Solution**: In test fixtures (`conftest.py`) and offline demo seeding (`scripts/seed_demo_data.py`), SQLAlchemy engine creation uses `execution_options={"schema_translate_map": SCHEMA_TRANSLATE_MAP}`, mapping each schema name to `None`. This collapses table names into the default flat SQLite namespace seamlessly without changing model code.

---

## 5. Non-Blocking Socket Probing vs. TCP Connection Timeouts

- **The Issue**: When PostgreSQL is configured as the default URL but the service is offline, calling `create_engine(DATABASE_URL).connect()` blocks for 30–60 seconds while the OS waits for TCP socket timeout before failing.
- **The Solution**: In `scripts/seed_demo_data.py`, implement an instant 0.5-second socket probe (`is_postgres_running(host, port)`) before initializing SQLAlchemy. If the probe fails, the system immediately switches to SQLite in 1 millisecond, preventing annoying developer hangs.

---

## 6. Financial Ledger Double-Entry Invariant & Exact Math

- **The Issue**: Float math (`0.1 + 0.2 = 0.30000000000000004`) causes insidious one-cent rounding errors that violate double-entry balancing ($\sum Debits \neq \sum Credits$).
- **The Solution**:
  1. All financial figures are strictly typed as Python `Decimal`.
  2. Use `quantize_money(amount)` with `Decimal("0.01")` and `ROUND_HALF_UP`.
  3. `LedgerEngine` checks $|\sum Debits - \sum Credits| == Decimal("0.00")` before commit.
  4. Never allow an LLM to calculate prices or disbursements; only deterministic engines compute figures.

---

## 7. AST Module Boundary Enforcement

- **The Issue**: Developers or agents may accidentally import internal models from foreign modules (e.g. `from app.modules.finance.models import Account` instead of `from app.modules.finance.public import Account`).
- **The Solution**: Architecture test `backend/tests/architecture/test_module_boundaries.py` walks the Python Abstract Syntax Tree (AST) of every module. Importing anything other than `public.py` from another module fails the build immediately.

---

## 8. Pytest Fixture Shadowing

- **The Issue**: If a test file defines its own `@pytest.fixture def client() -> TestClient:` without overriding `get_db`, it shadows the global `client` fixture in `conftest.py`. As a result, endpoints calling `Depends(get_db)` will try to connect to the real `DATABASE_URL` instead of the in-memory SQLite fixture.
- **The Solution**: Never redefine local `client` fixtures in individual test files unless explicitly overriding dependencies; rely on the shared `client` fixture from `conftest.py`.

---

## 9. Transactional Outbox State Semantics

- **The Issue**: Querying `OutboxEvent` for pending events must use `OutboxEvent.status == "pending"`, not boolean flags. `OutboxEvent` uses a tri-state string: `"pending"`, `"published"`, `"failed"`.
