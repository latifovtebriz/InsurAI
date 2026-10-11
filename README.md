# InsurAI

**InsurAI** is an enterprise-grade agentic insurance core platform for Property & Casualty (P&C) insurance, demonstrating deterministic financial engines, schema-per-module isolation, human-in-the-loop autonomous workflows (L0–L3), and defensive guardrail pipelines (G1–G10).

## 🚀 Key Architectural Highlights

- **Deterministic Financial & Legal Core:** Payouts, deductibles, premiums, taxes, and pro-rata cancellations are strictly executed by pure deterministic Python code using `Decimal`.
- **Bounded Context Monolith:** Schema-per-module database isolation across 12 business domains (`platform`, `party`, `product`, `policy`, `claims`, `sales`, `underwriting`, `finance`, `fraud`, `compliance`, `service`, `reinsurance`).
- **Transactional Outbox:** Guaranteed, atomic inter-module event publishing.
- **Autonomous Agent Runtime:** Hand-written ReAct loop with step budgets, loop detection, and pluggable guardrails.
- **Adjuster & Underwriter Copilot Console:** Modern React / Vite / TypeScript web dashboard.

---

## 🛠️ Quick Start

### 1. Prerequisites
- Python 3.12+ (or 3.13)
- `uv` (recommended) or `pip`
- Docker & Docker Compose (optional for local PostgreSQL + pgvector)

### 2. Setup Environment
```bash
# Create and activate virtual environment
python -m uv venv
.venv\Scripts\activate

# Install dependencies
python -m uv pip install -e ".[dev]"
```

### 3. Run Development Server
```bash
uvicorn backend.app.main:app --reload --port 8000
```
- API Documentation (Swagger): `http://localhost:8000/docs`
- Health Probe: `http://localhost:8000/health`
- Readiness Probe: `http://localhost:8000/ready`

### 4. Run Verification Suite
```bash
pytest
ruff check .
mypy backend/app
```
