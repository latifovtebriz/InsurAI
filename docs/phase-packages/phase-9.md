# Phase 9 Package: Sales & Underwriting (A1 Quote Assistant & A2 Underwriting Copilot)

**Status:** Completed  
**Tag:** `phase-9-done`  
**Date:** 2026-10-12  
**Target Milestone:** Release R2 Pre-requisite  

---

## 1. Executive Summary & Deliverables

Phase 9 implements the Sales module (P02), the Underwriting module (P03), Agent A1 (Quote Assistant), Agent A2 (Underwriting Copilot), deterministic underwriting rules, authority limit matrices, and complete REST API and web console interfaces.

### Key Deliverables:
1. **Sales Module (`backend/app/modules/sales/`):**
   - Schema `"sales"`.
   - Domain models: `Lead` and `Quote` with 30-day validity and itemized rating breakdowns.
   - Quotation Service: Integrates pure deterministic rating engines (`MOTOR_OD`, `MOTOR_TPL`, `HOME`), computes 1-pay and 4-installment schedules down to the exact cent, publishes `QuoteCreatedEvent` and `QuoteAcceptedEvent` to the transactional outbox, and enforces KYC-lite screening hooks.
2. **A1 Quote Assistant Agent (`agent.py`):**
   - Natural language intake of quote requests.
   - Automatic missing-field detection and clarification prompts (e.g., prompting when driver age or vehicle value is absent).
   - **Guardrail G2 (Mathematical Equality):** 100.0% adherence to pure rating engine numbers; zero hallucinated premiums.
   - **Guardrail G7 (Prompt Injection Defense):** Intercepts jailbreaks and adversarial overrides.
3. **Underwriting Module & Deterministic Rule Engine (`backend/app/modules/underwriting/`):**
   - Schema `"underwriting"`.
   - Domain model: `UnderwritingCase` with rule hits, risk scoring, authority tiers, and copilot assessments.
   - Rule Engine (`engine.py`):
     - `UW-01`: Vehicle value > 100,000 AZN -> High exposure referral (Senior Underwriter).
     - `UW-02`: Driver age < 21 -> Young driver referral (surcharge or higher deductible).
     - `UW-03`: Prior claims >= 2 -> Adverse loss history referral (Senior Underwriter).
     - `UW-04`: Combustible property construction -> Property fire survey referral.
     - `UW-05`: Driver age < 18 or value > 300,000 AZN -> Hard capacity knockout / Decline.
   - Delegated Authority Limits Matrix:
     - Junior Underwriter: up to 50,000 AZN sum insured.
     - Senior Underwriter: up to 150,000 AZN sum insured.
     - Chief Underwriter: unlimited.
   - Enforces mandatory written justification for any decline (Guardrail G3).
4. **A2 Underwriting Copilot Agent (`agent.py`):**
   - Summarizes referred risk profile.
   - Retrieves grounded underwriting guidelines (Guardrail G1).
   - Recommends structured conditions and status under L2 Human-in-the-Loop governance.
5. **REST API & Web Console v2 Screens:**
   - Endpoints: `/api/v1/sales/quotes`, `/api/v1/sales/chat`, `/api/v1/underwriting/cases`, `/api/v1/underwriting/cases/{id}/assess`, `/api/v1/underwriting/cases/{id}/decision`.
   - Web Console: `QuotesScreen.tsx` (Instant Calculator, A1 Interactive Chat, Quote Ledger) and `UnderwritingScreen.tsx` (Referral Queue, Rule Hits Dossier, A2 Copilot Panel, Adjudication Action Panel).
6. **Evaluation Benchmark Suite (`evals/run_sales_and_uw_eval.py`):**
   - Evaluated across 60 specialized test scenarios.
   - **A1:** 100% G2 numerical fidelity, 100% clarification rate, 100% prompt injection defense.
   - **A2:** 100% rule recall, 100% rule precision, 100% guideline grounding, 100% human sign-off enforcement.

---

## 2. How to Run and Verify

```bash
# 1. Run all unit, architecture, and integration tests (83 passing tests)
.venv\Scripts\pytest backend/tests/ -v

# 2. Run Sales & Underwriting specific unit and API tests
.venv\Scripts\pytest backend/tests/unit/test_sales_and_underwriting.py backend/tests/unit/test_sales_and_uw_api.py -v

# 3. Run Sales (A1) and Underwriting (A2) Evaluation Suite
.venv\Scripts\python evals/run_sales_and_uw_eval.py

# 4. Verify static typing and code hygiene
.venv\Scripts\ruff check backend/ evals/
.venv\Scripts\mypy backend/app

# 5. Verify frontend production build
npm --prefix frontend run build

# 6. Run secret scanner
.venv\Scripts\python scripts/secret_scanner.py
```

---

## 3. Acceptance Checklist

| Requirement | Description | Status | Evidence |
|---|---|---|---|
| **REQ-SLS-01** | `sales` module with Leads, Quotes, and 30-day validity | **PASS** | `Lead` and `Quote` models in schema `"sales"`. |
| **REQ-SLS-02** | Deterministic rating engine with installment options | **PASS** | Integrated Motor OD, TPL, Home rating with penny-exact installments. |
| **REQ-SLS-03** | KYC-lite screening hook stub | **PASS** | `check_kyc_lite_status` implemented and verified on accept. |
| **REQ-AGT-A1** | A1 Quote Assistant with missing-field clarification | **PASS** | Clarifies missing value/age; 100% clarification detection rate. |
| **REQ-GRD-G2** | G2 Mathematical Equality (zero hallucinated premiums) | **PASS** | 100.0% match between A1 explanations and deterministic rating engine. |
| **REQ-UW-01** | `underwriting` module with rule engine (UW-01 to UW-05) | **PASS** | 100.0% recall and precision across all rule triggers. |
| **REQ-UW-02** | Authority Limits Matrix (junior <= 50k, senior <= 150k, chief) | **PASS** | Verified in `test_underwriting_authority_matrix`. |
| **REQ-AGT-A2** | A2 Underwriting Copilot with guideline RAG | **PASS** | Grounded in underwriting guidelines; 100% grounding rate. |
| **REQ-GRD-G3** | Terminal outcomes (decline) always require human | **PASS** | System rejects declines without written underwriter rationale. |
| **REQ-UI-SLS** | Web Console screens for Quotes and Underwriting | **PASS** | `QuotesScreen.tsx` and `UnderwritingScreen.tsx` built and verified. |

---

## 4. Azərbaycan Dilində İzahat və C# Analogiyaları

### 4.1. Satış və Anderraytinq Prosesi Nədir?
1. **Satış (Quotation - P02):** Müştəri sığorta almaq istədikdə avtomobilin və ya əmlakın parametrlərini daxil edir. Süni intellekt (Agent A1) müştərinin sualını təhlil edir, əgər vacib məlumat çatışmırsa (məsələn, sürücünün yaşı və ya avtomobilin dəyəri), nəzakətlə aydınlaşdırıcı suallar verir. Bütün məlumatlar tam olduqda, **heç vaxt özündən rəqəm uydurmur (Guardrail G2)**; arxadakı deterministik tarif mühərrikini çağıraraq rəsmi və dəqiq təklif (Quote) formalaşdırır.
2. **Anderraytinq və Yönləndirmə (Referral - P03):** Hər bir risk dərhal təsdiqlənə bilməz. Əgər avtomobilin dəyəri 100,000 AZN-dən çoxdursa, sürücünün yaşı 21-dən azdırsa və ya keçmişdə 2-dən çox qəzası olubsa, sistem bunu avtomatik olaraq anderrayterə yönləndirir (Underwriting Referral).
3. **Anderrayter Köməkçisi (Agent A2):** Təcrübəli anderrayter müraciəti açdıqda, Agent A2 risk profilini xülasə edir, şirkətin daxili anderraytinq təlimatlarına (UW Guidelines) istinad edir və xüsusi şərtlərlə (məsələn, GPS izləyici quraşdırmaq və ya azadolma məbləğini artırmaq) təsdiq təklif edir. Lakin **son qərarı (xüsusən də imtina qərarını) yalnız insan anderrayter qəbul edə bilər (Guardrail G3)**.

### 4.2. C# / .NET Analogiyaları

1. **A1 Rating Explanation vs FluentValidation & MediatR:**
   - C#-da biz adətən `CalculateQuoteQuery` göndəririk və `RatingCalculationService` riyazi dəqiqliklə `QuoteResponse` qaytarır.
   - Python-dakı `QuoteAssistantAgent` bu sorğunu istifadəçi mətni ilə bağlayır və çıxışı C#-dakı `String.Format("{0:N2} AZN", quote.TotalPremium)` kimi riyazi dəqiqliklə təqdim edir.

2. **Underwriting Rules vs Rule Engines (RulesEngine / MediatR Pipeline):**
   - .NET ekosistemində Microsoft-un `RulesEngine` kitabxanası və ya `WorkflowEngine` necə deklarativ qaydaları (`rule_hits`) icra edirsə, InsurAI-nin `evaluate_underwriting_rules()` funksiyası eyni şəkildə işləyir.
   - Hər bir qaydanın sərtlik dərəcəsi (`info`, `referral`, `knockout`) və tələb etdiyi səlahiyyət pilləsi (`junior`, `senior`, `chief`) var.

3. **Authority Limit Matrix vs Claims-Based Authorization in ASP.NET Core:**
   - C#-da `[Authorize(Policy = "SeniorUnderwriterPolicy")]` atributu vasitəsilə istifadəçinin limitini (`user.Claims.FirstOrDefault(c => c.Type == "AuthorityLimit")`) necə yoxlayırıqsa, InsurAI-də `verify_underwriter_authority()` funksiyası anderrayterin səlahiyyətindən artıq olan riskləri təsdiq etməsinə imkan vermir.

---

## 5. Senior Interview Sentences (English)

1. *"To eliminate financial hallucination in our sales funnel, Agent A1 operates under strict Guardrail G2 mathematical equality: natural language inquiries are parsed for intent and missing parameters, but numerical quotations are strictly computed by our deterministic tariff engine."*
2. *"Our underwriting architecture enforces a clean separation of concerns: a deterministic rule engine evaluates statutory exposure thresholds and assigns delegated authority tiers, while Copilot A2 grounds recommended conditions against our knowledge base under non-negotiable L2 human oversight."*
3. *"Under statutory compliance rules, terminal outcomes such as underwriting declines cannot be autonomously executed by AI; our system enforces Guardrail G3, mandating human underwriter assignment and a persistent audit justification."*

---

## 6. Technical & Domain Quiz Questions

### Suallar:
1. Agent A1 müştəri ilə danışarkən nə üçün sığorta haqqını özü "təxmin" etməməli və mütləq deterministik aləti (`calculate_quote`) çağırmalıdır?
2. Sığorta qaydalarına əsasən avtomobilin dəyəri 120,000 AZN olduqda nə üçün kiçik anderrayter (Junior Underwriter) onu təsdiq edə bilməz və sistem nə tələb edir?
3. Əgər müştəri müraciətində avtomobilin markasını qeyd edib, lakin dəyərini və öz yaşını qeyd etməyibsə, A1 agenti hansı addımı atmalıdır?
4. Anderraytinq müraciətini rədd (decline) edərkən sistem hansı məcburi qoruyucu qaydanı (Guardrail G3) tətbiq edir?
5. Agent A2-nin təklif etdiyi anderraytinq şərtləri (məsələn, 25% yanğın əlavəsi) haradan əldə edilir və bu Guardrail G1-ə necə uyğundur?

---

<details>
<summary><b>Cavabları Görmək Üçün Klikləyin</b></summary>

### Cavablar:
1. **Deterministik Dəqiqlik (G2 Invariant):** LLM-lər təxmini mətn generasiya etdiyi üçün sığorta tariflərində yuvarlaqlaşdırma və riyazi xətalar edə bilər. Qanunvericilik və audit tələb edir ki, təqdim olunan hər bir qiymət təsdiq olunmuş aktuar tarif cədvəlinə uyğun olsun.
2. **Səlahiyyət Matrisi (Authority Limit Matrix):** 100,000 AZN-dən yuxarı risklər yüksək məbləğli exposure sayılır və Rule UW-01-ə əsasən Senior Underwriter təsdiqi və telematika/GPS quraşdırma zəmanəti tələb olunur.
3. **Çatışmayan Sahələrin Aydınlaşdırılması:** Sistem defolt rəqəm uydurmur; `missing_fields` siyahısını müəyyən edir və müştəriyə nəzakətli sual ünvanlayaraq avtomobilin bazar dəyərini və sürücülük yaşını soruşur.
4. **Məcburi İmtina Əsaslandırması (G3):** Süni intellekt heç bir riski təkbaşına imtina edə bilməz. İmtina qərarı yalnız insan anderrayter tərəfindən verilə bilər və mütləq yazılı əsaslandırma (`override_reason` və ya `notes`) daxil edilməlidir.
5. **Əsaslandırılmış İstinad (G1 Grounding):** Agent A2 daxili anderraytinq təlimatlarını (`search_uw_guidelines`) axtarır və çıxardığı hər bir tələb üçün rəsmi qayda kodunu (məsələn: `UW-GUIDELINE-HOME-01`) istinad kimi qeyd edir.
</details>

---

## 7. Git Steps & Tag

- **Commit:** `feat(sales-uw): implement sales, underwriting, A1 Quote Assistant, and A2 Copilot (Phase 9)`
- **Tag:** `phase-9-done`
- **Pre-push checks:** Secret scanner PASSED, Pytest 83/83 PASSED, Ruff PASSED, Mypy PASSED, Frontend build PASSED.

---

## 8. Known Limitations & Next Steps

1. **KYC Screening:** Phase 9 implements a KYC-lite stub interface; comprehensive sanctions list screening and PEP checks will arrive in Phase 11 (`compliance` module).
2. **Next Phase:** Proceed to **Phase 10: Finance, Renewal, Reinsurance, and A7 Renewal Advisor (Release R2)**:
   - `finance` module (P05, P11): installments, invoices, balanced double-entry ledger, dunning.
   - `renewal` module (P07): T-60 review, statutory notice deadlines.
   - Agent A7 (Renewal Advisor).
   - `reinsurance` module (P13): treaties, cession job, bordereaux report.
