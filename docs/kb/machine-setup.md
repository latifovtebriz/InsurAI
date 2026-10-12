# InsurAI New Machine Onboarding & Environment Setup Guide

This guide ensures you can clone and run **InsurAI** on any computer (Windows, macOS, Linux) without dependencies or credential blockers.

---

## 1. Quick Requirements

| Component | Minimum Version | Recommended Tool | Purpose |
|---|---|---|---|
| **Python** | 3.12+ (or 3.13) | Standard Python or `uv` | Backend runtime & test suite |
| **Node.js** | 20+ (LTS) | `node` + `npm` | Web Console v2 frontend |
| **Git** | 2.40+ | Official Git CLI | Version control |
| **Docker** | Optional | Docker Desktop | Optional (PostgreSQL + pgvector) |

> [!NOTE]
> **Docker is NOT required to run or test InsurAI.** The entire platform features a zero-dependency local mode using SQLite and a deterministic fake LLM, enabling 100% functionality out-of-the-box.

---

## 2. Cloning & Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/latifovtebriz/InsurAI.git
cd InsurAI

# 2. Verify git status and branches
git status
git branch -a
```

---

## 3. Backend Virtual Environment Setup

### Option A: Using `uv` (Fastest, Recommended)
```bash
# Install uv if not present
pip install --user uv

# Create virtual environment
uv venv
# On Windows PowerShell:
.venv\Scripts\activate
# On macOS / Linux:
# source .venv/bin/activate

# Install backend dependencies in editable mode with dev tools
uv pip install -e ".[dev]"
```

### Option B: Using Standard Python `venv` + `pip`
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

---

## 4. Frontend Console Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Test production build
npm run build

# Return to repository root
cd ..
```

---

## 5. Single-Command Turnkey Demo Seeding

InsurAI includes an automated demo database seeder that auto-detects if PostgreSQL is running. If PostgreSQL is offline, it instantly provisions a standalone demo SQLite database (`insurai_demo.db`):

```bash
# Run the demo data seeder
python scripts/seed_demo_data.py
```

**Expected output:**
```
[1/10] Connecting to database engine...
  -> Connected: SQLite database at sqlite:///insurai_demo.db
[2/10] Initializing chart of accounts (13 accounts)...
[3/10] Provisioning reinsurance treaties...
[4/10] Generating synthetic parties, vehicles, and properties...
[5/10] Quoting and underwriting policies...
[6/10] Binding policies, invoicing, collecting premiums, and ceding reinsurance...
[7/10] Processing mid-term endorsement (Process P06)...
[8/10] Adjudicating claims, establishing reserves, and collecting reinsurance recovery...
[9/10] Generating SIU fraud case, AML sanctions alert, and customer complaint...
[10/10] Scanning expiring policies at T-60 (Agent A7, Process P07)...
--- System Integrity Verification ---
  Total General Ledger Debits :      43142.50 AZN
  Total General Ledger Credits:      43142.50 AZN
  General Ledger Difference   :          0.00 AZN
  General Ledger Balanced     : [PASSED] YES
[SUCCESS] Seed-to-Demo pipeline successfully initialized complete InsurAI instance!
```

---

## 6. Running the Platform Locally

Open two terminal windows:

### Terminal 1: Backend API
```powershell
.venv\Scripts\activate
uvicorn app.main:app --port 8000 --reload
```
- Swagger Interactive Documentation: `http://localhost:8000/docs`
- Prometheus Metrics: `http://localhost:8000/metrics`
- System Health: `http://localhost:8000/health`
- Readiness & Outbox Depth: `http://localhost:8000/ready`
- Executive KPIs: `http://localhost:8000/api/v1/metrics/executive-kpis`

### Terminal 2: Frontend Web Console v2
```powershell
cd frontend
npm run dev
```
- Open Web Console: **`http://localhost:5173`**
- Instant 1-click persona logins available: Adjuster, Senior Underwriter, Finance Officer, Compliance Officer, SIU Investigator.

---

## 7. Running the Verification Suite on Any Machine

To verify that your new machine passes all quality gates:

```powershell
# 1. Run all unit, architecture, robustness, and golden journey tests (129 tests)
pytest

# 2. Run static type checking across 109 backend files
mypy backend/app

# 3. Run linter and formatting checks
ruff check .
ruff format --check .

# 4. Verify secret hygiene scanner
python scripts/secret_scanner.py

# 5. Verify frontend build
cd frontend ; npm run build ; cd ..
```

All 5 checks should report **100% green / 0 errors**.

---

## 8. Switching to PostgreSQL + pgvector (Production / Docker Mode)

If Docker Desktop is installed and running on your new machine:

```bash
# 1. Start PostgreSQL with pgvector container
docker compose up -d

# 2. Set environment variable in your .env file
# Copy from example
cp .env.example .env
# Set DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/insurai

# 3. Run migrations or seed script
python scripts/seed_demo_data.py
```

---

## 9. Common Gotchas on New Machines

1. **`python` vs `python3`**: On Linux/macOS, use `python3 -m venv .venv`. On Windows, ensure Python is registered in your PATH.
2. **Execution Policy on Windows PowerShell**:
   If PowerShell blocks script activation (`Activate.ps1 cannot be loaded`), run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
3. **Port 8000 or 5173 Already in Use**:
   - Backend: specify another port: `uvicorn app.main:app --port 8001`
   - Frontend: Vite will automatically offer port 5174 if 5173 is occupied.
4. **Git CRLF Line Ending Warnings on Windows**:
   `.gitattributes` is already configured in the repository root (`* text=auto`, `*.sh text eol=lf`) to guarantee clean LF endings for Docker scripts.
