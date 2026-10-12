# InsurAI 5-Minute Golden Demo Walkthrough

This script guides an interviewer, evaluator, or technical leader through 4 core operational journeys showcasing InsurAI's autonomous agents, deterministic engines, and real-time Web Console.

---

## Prerequisites (30 Seconds Setup)

1. **Seed Turnkey Demo Environment**:
   ```powershell
   python scripts/seed_demo_data.py
   ```
   *Expected Output*: `[OK] Demo seed complete! Created 13 accounts, 2 treaties, 10 parties, 8 vehicles, 6 properties, 8 policies, 8 claims, 3 complaints. General Ledger Balance: 0.00 AZN.`

2. **Start Backend & Frontend**:
   - Terminal 1 (Backend): `.venv\Scripts\uvicorn app.main:app --port 8000 --reload`
   - Terminal 2 (Frontend): `cd frontend && npm run dev`
   - Open Web Console at `http://localhost:5173`.

---

## Scenario 1: Instant Motor OD Quote to Policy Issuance (60 Seconds)

**Business Story**: A customer requests comprehensive motor coverage for a 2021 Toyota Corolla in Baku. Agent A1 rates the risk, issues an instant quote, and upon binding, the system posts a balanced double-entry accounting transaction.

### Step-by-Step Walkthrough:
1. Navigate to the **Sales & Quotes** screen in the Web Console.
2. Click **"New Quote"** (or inspect existing active quote `QUO-2026-A101`).
3. Select Product: `MOTOR-OD-001` (Kasko / Comprehensive Motor).
4. Insured Value: `35,000 AZN`, Deductible: `500 AZN`.
5. Observe:
   - Rating Engine calculates base premium + location multiplier (`AZ-BAKU` = 1.05) + deductible discount.
   - Total Premium: `1,102.50 AZN`.
6. Click **"Bind & Issue Policy"**.
7. Navigate to **Finance & Ledger** screen:
   - Verify transaction `TX-INV-001` is posted.
   - **Debit**: Account `1120` (Accounts Receivable - Direct) = `1,102.50 AZN`.
   - **Credit**: Account `4110` (Gross Written Premium) = `1,102.50 AZN`.
   - **Balance Difference**: Exactly `0.00 AZN`.

---

## Scenario 2: Grounded FNOL Intake & Straight-Through Payout (90 Seconds)

**Business Story**: Policyholder files a First Notice of Loss (FNOL) for minor bumper and fender damage resulting from a parking lot collision. Claims Agent A4 triages the claim autonomously at Autonomy Level 1.

### Step-by-Step Walkthrough:
1. Navigate to the **Claims Triage** screen.
2. Select Claim `CLM-2026-0001` (Motor Collision, Claimed Amount: `850.00 AZN`).
3. Click **"Run Autonomous Triage (Agent A4)"**.
4. Observe the Real-time Agent Reasoning Trace:
   - **Step 1 (Tool)**: `check_policy_active` -> Confirms policy was in force on incident date.
   - **Step 2 (Tool)**: `search_policy_wording` -> Retrieves Section 4, Clause 01 (Accidental Collision Coverage).
   - **Step 3 (Engine)**: Deterministic Payout Engine computes:
     $$\text{Payable} = \min(850.00, 35000.00) - 250.00\text{ (deductible)} - 0.00\text{ (depreciation)} = 600.00\text{ AZN}$$
   - **Step 4 (Guardrails)**: G1 (Grounded Citations), G2 (Mathematical Invariant), G5 (Mandatory Tools) all pass with green badges.
5. Decision Status: **Approved (Autonomy L1)**.
6. Click **"Authorize Payout Disbursement"**:
   - Ledger posts claim settlement:
     - Debit `5110` (Claims Incurred) = `600.00 AZN`
     - Credit `1110` (Cash and Bank) = `600.00 AZN`
     - Invariant: $\Delta = 0.00$ AZN.

---

## Scenario 3: Suspicious Claim Triage & Adjuster Override (90 Seconds)

**Business Story**: A claim is filed 2 days after policy inception with inconsistent damage descriptions and high claimed amounts. Fraud Agent A5 detects anomalous risk signals and downgrades to Autonomy Level 2.

### Step-by-Step Walkthrough:
1. On **Claims Triage**, select Claim `CLM-2026-0004` (Claimed Amount: `4,200.00 AZN`, Incident Date: 48 hours post-inception).
2. Click **"Run Autonomous Triage"**.
3. Observe Agent Execution:
   - Fraud Agent A5 flags anomaly: `SIG-INCEPTION-01` (Claim filed within 72 hours of binding).
   - Damage inconsistency detected against photos.
   - Total Fraud Score: `0.74` ($\ge 0.60$ SIU threshold).
   - Guardrail G4 (Ambiguity) and Autonomy Level 2 circuit breaker trigger.
   - Status: **Downgraded to `needs_human_review`**.
4. As the Senior Adjuster, inspect the SIU case summary.
5. Click **"Adjuster Override"**:
   - Enter rationale: *"Physical inspection confirms pre-existing oxidation on damaged panels. Rejecting payout per Exclusion Clause 7.2."*
   - Change Status to **Rejected**.
6. Navigate to **Executive KPIs** (`MetricsScreen.tsx`):
   - Notice the **Adjuster Override Rate** metric increments, recording human governance.

---

## Scenario 4: Statutory Complaint Intake & Reinsurance Recovery (60 Seconds)

**Business Story**: A customer submits a complaint regarding communication delays. Service Agent A3 triages the complaint against the Central Bank of Azerbaijan (CBA) 10-day statutory SLA, while Finance Agent A7 recovers large loss capital from the reinsurance treaty.

### Step-by-Step Walkthrough:
1. Navigate to the **Customer Service & Complaints** screen.
2. Select Complaint `CMP-2026-0001`:
   - Incident Date: Day 3 of 10.
   - Statutory SLA Status: `ACTIVE (7 business days remaining)`.
   - Agent A3 proposes apology resolution letter and expedited adjuster assignment.
3. Switch to **Finance & Reinsurance**:
   - Inspect Treaty `QS-MOTOR-2026` (Quota Share 20% cession).
   - Verify claim recovery `REC-2026-0001` ceded to Munich Re:
     - Recovered Amount: `120.00 AZN` (20% of 600.00 AZN payout).
     - Ledger Debit: `1130` (Reinsurance Receivables) = `120.00 AZN`.
     - Ledger Credit: `5120` (Reinsurance Recoveries Revenue) = `1,20.00 AZN`.
4. Check **System Health Indicator**:
   - Prometheus Endpoint `/metrics`: Green.
   - General Ledger Total Imbalance: `0.00 AZN`.
