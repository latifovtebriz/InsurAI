# Phase 10 Package: Finance, Renewal, Reinsurance, and Agent A7 Renewal Advisor

## 1. Summary
Phase 10 delivers the financial core, balanced double-entry accounting engine, treaty reinsurance automation, and annual policy renewal review suite for InsurAI:
1. **Finance & Balanced General Ledger (`app/modules/finance/`):**
   - Chart of Accounts (`finance.accounts`), General Ledger Transactions (`gl_transactions`), and Entries (`gl_entries`).
   - Strict double-entry invariant: Debits strictly equal Credits down to the exact cent across 100% of journal entries. Verified by property-based testing (`hypothesis`).
   - Installment invoicing, payment intake simulation, payment allocation updating policy paid amounts and activating bound policies.
   - Automated dunning engine with T+7 (Level 1), T+14 (Level 2), and T+30 (Level 3 default/cancellation) escalation alerts.
   - Claims payout disbursement with four-eyes authorization and commission accrual.
2. **Reinsurance Treaties & Bordereaux (`app/modules/reinsurance/`):**
   - Market treaty models (`reinsurance.treaties`) supporting 20% Quota Share (Swiss Re) and 50k xs 500k Excess of Loss (Munich Re).
   - Automated premium cessions with balanced contra-accounts (`4020` Ceded Premium vs `2040` Reinsurance Payable).
   - Automated claims loss recoveries (`1300` Reinsurance Recoverable vs `5030` Loss Recoveries).
   - Structured bordereau reporting statement generation for treaty reinsurers.
3. **Policy Renewal (P07) & Agent A7 (Renewal Advisor):**
   - Automated T-60 expiring policy scanning job.
   - Bonus-malus claim re-rating: 0 claims (5% no-claims discount), 1 claim (15% surcharge), 2+ claims (non-renewal recommendation).
   - Statutory 30-day notice deadline enforcement: policies expiring in $\le 30$ days without issued notice trigger critical statutory breach alerts (`statutory_deadline_breached = True`).
   - Agent A7 (Renewal Advisor) with ReAct tool registry (`get_expiring_policies`, `calculate_renewal_rate`, `draft_renewal_notice`), Guardrails G1/G2/G7, L1 standard renewals, and mandatory L2 underwriter sign-off for surcharges and non-renewals.
4. **REST APIs & Web Console v2 Screens:**
   - REST endpoints `/api/v1/finance/*`, `/api/v1/renewals/*`, `/api/v1/reinsurance/*`.
   - `FinanceScreen.tsx`: Real-time balanced ledger indicator (`Δ = 0.00 AZN`), invoice payment simulator, GL journal viewer, reinsurance treaties.
   - `RenewalScreen.tsx`: T-60 expiring policies queue, statutory breach warning banner, interactive Agent A7 inspection panel.

---

## 2. How to Run and Verify

### Backend Invariant Tests & Unit Suite
```bash
# Run finance, reinsurance, renewal, and API test suites
.venv\Scripts\pytest backend/tests/unit/test_finance_and_ledger.py backend/tests/unit/test_reinsurance.py backend/tests/unit/test_renewal_and_a7.py backend/tests/unit/test_finance_api.py -v

# Run full test suite (101 tests passing)
.venv\Scripts\pytest backend/tests/ -q

# Run architecture boundary isolation check
.venv\Scripts\pytest backend/tests/architecture/
```

### Static Analysis & Lints
```bash
.venv\Scripts\ruff check backend/
.venv\Scripts\mypy backend/app/
```

### Evaluation Benchmark
```bash
.venv\Scripts\python evals/run_finance_and_renewal_eval.py
```

### Frontend Production Build
```bash
cd frontend
npm run build
```

---

## 3. Acceptance Checklist

| Requirement | Expected | Actual Result | Status |
|---|---|---|---|
| Double-entry GL Invariant | Debits == Credits ($\Delta = 0.00$ AZN) | 175/175 transactions balanced ($\Delta = 0.00$) | **PASS** |
| Property-Based Ledger Invariant | Random debits & credits balance | 100% passed via `hypothesis` | **PASS** |
| Policy Invoicing & Payment Allocation | Activates policy, records Cash vs AR | Tested & verified in `test_policy_invoicing_and_payment_flow` | **PASS** |
| Dunning Job Escalation | T+7, T+14, T+30 notices generated | Verified in `test_dunning_job_escalation` | **PASS** |
| Reinsurance Treaty Cessions | 20% Quota Share ceded to Swiss Re | Verified in `test_premium_cession_and_gl_journal` | **PASS** |
| Excess of Loss Recoveries | Claims $> 50\text{k}$ attach recovery | Verified in `test_claim_loss_recoveries_qs_and_xol` | **PASS** |
| Reinsurance Bordereau Statement | Summary & line-item exports | Verified in `test_bordereau_report_generation` | **PASS** |
| T-60 Renewal Scanner | Identifies expiring policies | Verified in `test_renewal_t60_scanning_and_segmentation` | **PASS** |
| Statutory 30-Day Notice Rule | Breaches flagged if $T \le 30$ | 100% recall (5/5 flagged in eval) | **PASS** |
| Agent A7 Rating Fidelity (G2) | Proposed premium matches tariff | 100% rate fidelity across 30 scenarios | **PASS** |
| A7 L2 Human Sign-off | Non-renewals require underwriter | 100% enforced in eval runner | **PASS** |
| Frontend Production Build | Zero TypeScript / bundle errors | 279 kB bundle built cleanly via Vite | **PASS** |
| Architecture Boundaries | Zero cross-module leaks | 2/2 boundary tests passed | **PASS** |

---

## 4. Explanations in Azerbaijani with C# Analogies

### İkiqat Mühasibat Qeydiyyatı (Double-Entry General Ledger) və İnvaryant
- **Sığorta Konsepti:** Sığorta şirkətində heç bir pul hərəkəti "havadan" yarana bilməz. Hər bir qəpiyin haradan gəldiyi və hara getdiyi ikiqat qeydiyyatla (Debet və Kredit) balanslaşmalıdır. Məsələn, müştəriyə 1,200 AZN-lik sığorta şəhadətnaməsi satılanda:
  - Debet: `1200` Alacaqlar (Accounts Receivable) +1,200 AZN (Aktiv artır).
  - Kredit: `4010` Hesablanmış Ümumi Sığorta Haqqı (GWP) +1,200 AZN (Gəlir artır).
  Müştəri bank vasitəsilə 1,200 AZN ödəyəndə:
  - Debet: `1010` Bank Hesabı (Bank Cash) +1,200 AZN (Aktiv artır).
  - Kredit: `1200` Alacaqlar (Accounts Receivable) -1,200 AZN (Alacaq bağlanır).
- **C# Analogiyası:** C# və Entity Framework Core dünyasında bu, `LedgerTransaction` və `LedgerEntry` cədvəllərində `DbContext.SaveChanges()` çağırılmazdan əvvəl `entries.Sum(e => e.Debit) == entries.Sum(e => e.Credit)` yoxlanışını icra edən bir Interceptor və ya Domain Event kimidir. Əgər bircə qəpik belə fərq varsa, `LedgerImbalanceException` atılaraq tranzaksiya dərhal Rollback edilir.

### Təkrar Sığorta (Reinsurance - Quota Share və Excess of Loss) və Bordero
- **Sığorta Konsepti:** Şirkət böyük riskləri təkbaşına daşımır; beynəlxalq təkrar sığortaçılara (Swiss Re, Munich Re) ötürür.
  - **Quota Share (Kvota Payı):** Hər yazılan sığorta haqqının məsələn 20%-i və baş verən hər zərərin 20%-i təkrar sığortaçıya verilir.
  - **Excess of Loss (Zərərin Artığı):** Şirkət 50,000 AZN-ə qədər olan zərərləri özü ödəyir; 50,000 AZN-dən yuxarı hissəni isə təkrar sığortaçı qarşılayır (məsələn, 80,000 AZN zərərdə 30,000 AZN bərpa olunur).
  - **Bordero (Bordereaux):** Ayın sonunda təkrar sığortaçıya təqdim olunan rəsmi cədvəl hesabatıdır.
- **C# Analogiyası:** C#-da bu, `IReinsurancePolicyEngine` interfeysi kimidir: `CalculateCession(policy)` və `CalculateRecovery(claim)` metodları zərərin növünə görə `QuotaShareStrategy` və ya `ExcessOfLossStrategy` (Strategy Pattern) tətbiq edir.

### Müqavilənin Yenilənməsi (Renewal P07) və Qanuni 30 Günlük Bildiriş Qaydası
- **Sığorta Konsepti:** Müqavilənin bitməsinə 60 gün qalmış (T-60) sistem müştərinin il ərzindəki qəza tarixçəsini analiz edir. Qəzası olmayan müştəriyə 5% endirim (Bonus-Malus NCD), 1 qəzası olana 15% əlavə haqq təklif olunur. Əgər müştərinin 2 və ya daha çox qəzası varsa, şirkət müqaviləni yeniləməkdən imtina edə bilər (Non-Renewal). Lakin sığorta qanunvericiliyinə görə, imtina bildirişi müqavilə bitməzdən **ən azı 30 gün əvvəl** çatdırılmalıdır! Əgər 30 gün qalıbsa və bildiriş verilməyibsə, sistem qanun pozuntusu xəbərdarlığı (`statutory_deadline_breached = True`) qaldırır.
- **C# Analogiyası:** Quartz.NET və ya Hangfire ilə hər gecə çalışan `RenewalScannerJob` kimidir. Expiring müqavilələri filter edir, `daysToExpiry <= 30` və `recommendation == NonRenewal` olduqda sistem avtomatik `StatutoryBreachEvent` yayır.

---

## 5. 3-5 Interview Sentences in English
1. "In Phase 10, I designed and implemented a constraint-enforced double-entry general ledger where the total debits strictly equal total credits across all transactions, verified down to the exact cent via property-based hypothesis testing."
2. "I automated reinsurance treaty cessions and claims recoveries under both Quota Share and Excess of Loss contracts, generating structured periodic bordereau statements for global reinsurers."
3. "Our policy renewal workflow runs automated T-60 batch scanning with claim-based bonus-malus re-rating, and programmatically enforces statutory 30-day non-renewal notification deadlines to prevent regulatory breach."
4. "Agent A7 acts as an autonomous Renewal Advisor operating under L1 for clean discount renewals, but strictly downgrading to L2 human underwriter sign-off whenever risk surcharges or terminal non-renewals are proposed."

---

## 6. Five Verification Questions
1. **Q:** Why must the double-entry accounting ledger enforce $\sum \text{Debit} == \sum \text{Credit}$ in code before committing to PostgreSQL?
2. **Q:** How does a Quota Share (QS) treaty differ from an Excess of Loss (XOL) treaty in its impact on the general ledger?
3. **Q:** What is the statutory consequence if an insurer decides not to renew a policy but fails to deliver the non-renewal notice at least 30 days prior to expiration?
4. **Q:** Under which governance tier does Agent A7 operate when processing a policyholder with zero claims versus a policyholder with two at-fault accidents?
5. **Q:** How is financial integrity protected against rounding drift in installment schedules and pro-rata cessions?

*(Answers are located at the end of this document).*

---

## 7. Git Step
- **Commit:** `feat(finance-reinsurance): implement double-entry ledger, reinsurance treaties, renewal workflow, and A7 advisor (Phase 10)`
- **Tag:** `phase-10-done`
- **Remote Push:** `git push origin main --tags`

---

## 8. Known Limitations & Deferred Items
- **Automated Bank Gateway Webhook:** Real-time webhooks (e.g. Stripe/Adyen/Kapital Bank) are simulated via `POST /api/v1/finance/invoices/{id}/pay` in offline mode.
- **Live LLM Evaluation:** Evaluation ran deterministically with `FakeLLMClient` and heuristic tools. Real-model evaluation run is queued for when `LLM_API_KEY` is provided.

---

### Answers to Verification Questions
1. **A:** In core financial accounting, single-column balance tables or manual recalculations can mask floating-point drift or unhandled transaction legs. Enforcing the double-entry invariant at the service boundary guarantees that every economic event has an explicit source and destination of funds, ensuring the ledger can never be written in an unbalanced state.
2. **A:** Quota Share cedes a fixed percentage (e.g., 20%) of all written premiums and all incurred losses continuously, creating proportionate contra-revenue and contra-expense postings. Excess of Loss does not cede premium proportionately; it only attaches when an individual catastrophic claim exceeds the retention threshold (e.g., 50,000 AZN), recovering only the excess amount.
3. **A:** By statutory insurance law, failing to give timely 30-day notice of non-renewal legally obligates the insurer to renew coverage on existing terms or subjects the carrier to administrative regulatory sanctions.
4. **A:** Clean risks with 0 claims operate under Autonomy Level 1 (system automatically prepares and issues standard renewal offers with no-claims discount). Adverse risks with multiple claims operate strictly under Autonomy Level 2, requiring explicit human underwriter review, written rationale, and formal sign-off before a non-renewal notice can be issued.
5. **A:** All monetary numbers utilize Python's `Decimal` type with fixed 2-place quantization (`0.01`) and standard commercial rounding (`ROUND_HALF_UP`). Zero IEEE-754 floating-point math is allowed in financial pathways.
