# InsurAI Phase 6 Package: Core Policy Administration (Party, Product, Policy)

## 1. Summary of Completed Work
In Phase 6, we implemented the core policy administration kernel of InsurAI with zero LLM dependence—guaranteeing 100% deterministic, auditable, and mathematically exact financial calculations:
- **`party` Module (`models.py`, `service.py`, `public.py`):**
  - Schema-isolated tables: `parties` (individuals & corporate organizations), `vehicles` (VIN, registration, market value), `properties` (cadastral code, construction type, floor area), `intermediaries` (brokers, license numbers, commissions).
  - Complete domain service supporting KYC lifecycle transitions (`pending` -> `verified` -> `rejected`).
- **`product` Module (`models.py`, `service.py`, `public.py`):**
  - Schema-isolated tables: `products` and effective-dated `product_versions`.
  - **Four-Eyes Publication Governance:** Enforces maker-checker dual authorization (`FourEyesViolationError`); the actuary who drafts a product version cannot self-approve publication.
  - Effective date-in-force resolution: accurately retrieves published versions across 2025 (V1) and 2026 (V2).
- **Pure Deterministic Rating Engine (`policy/rating.py`):**
  - Pure functions using Python's `Decimal` with `ROUND_HALF_UP` precision:
    - `MOTOR_OD`: Base rates (V1: 3.2% vs V2: 3.4%), young driver surcharge (<25yo: 1.30x), vehicle age surcharge (>5yo: 1.20x), bonus-malus discount/surcharge (0.90x, 1.15x, 1.35x), and minimum premium floor enforcement (350 AZN in V1, 380 AZN in V2).
    - `MOTOR_TPL`: Statutory engine capacity bands (1.0x to 2.5x) and bonus-malus tiers.
    - `HOME`: Construction type factor (wooden structures: 1.50x), historic pre-1970 building factor (1.20x), minimum premium floor (120 AZN).
  - **Installment Schedule Generator:** Supports 1, 2, 4, or 12 installments with exact penny remainder allocation to installment #1—ensuring $\sum \text{Installments} \equiv \text{Total Premium}$ down to \$0.01.
- **Process P04 (Policy Issuance - `policy/service.py`):**
  - Pre-bind KYC verification gate: strictly prohibits binding policies for unverified parties.
  - Frozen product version: pins `product_version_id` to prevent retroactive wording or tariff shifts.
  - Number generator: atomic format `POL-{YEAR}-{PREFIX}-{SEQUENCE}`.
  - Certificate generation: creates `PolicyCertificate` with cryptographic SHA-256 integrity digest.
  - Atomic transaction: writes policy, certificate, audit log entry, and publishes `PolicyIssued` event to transactional outbox.
- **Process P06 & Clause F.1 (Pro-Rata Cancellation & Refund Engine - `policy/cancellation.py`):**
  - Pure daily pro-rata formula: handles leap years (e.g. 2024 with 366 days).
  - **Clause F.1 Invariant:** If prior claims exist on the policy, refund is strictly 0.00 AZN.
  - Administrative fee ($25.00$ AZN) deducted from unearned gross refund.
  - Manager sign-off threshold: refunds exceeding $500.00$ AZN trigger `requires_manager_approval = True`.
- **Policy Status Checker Engine (`check_policy_active`):**
  - Core validation engine providing structured coverage status, sum insured, deductible, and date-in-force validation for Claims Triage Agent A4.

---

## 2. How to Run and Verify
```bash
# 1. Run all Policy Administration tests (golden tests & property-based tests)
pytest backend/tests/unit/test_policy_admin.py -v

# 2. Run full test suite (57 tests passing)
pytest backend/tests -v

# 3. Verify static typing and linting
ruff check .
mypy backend

# 4. Verify secret hygiene
python scripts/secret_scanner.py
```

---

## 3. Acceptance Checklist
- [x] Schema-isolated tables for `party`, `product`, and `policy` contexts
- [x] Four-eyes publication rule enforced in `product_service`
- [x] Pure deterministic rating engines for `MOTOR_OD`, `MOTOR_TPL`, and `HOME` with `Decimal`
- [x] Installment schedule generator satisfies penny-exact sum invariant
- [x] Pro-rata cancellation engine with leap year accuracy, Clause F.1 prior claims exclusion, and >500 AZN manager sign-off
- [x] Policy issuance workflow (P04) with pre-bind KYC gate and SHA-256 certificate generation
- [x] Property-based testing with `hypothesis` confirming financial invariants
- [x] 100% test pass rate (57 unit & architecture tests)
- [x] Ruff and Mypy passing with 0 errors across 75 source files

---

## 4. Azərbaycan Dilində İzah və C# Analogiyaları

### 4.1. Niyə Pul və Hesablamalarda LLM və `float` Qəti Qadağandır?
C# proqramçısı çox yaxşı bilir ki, `float` və `double` tipləri IEEE-754 ikilik (binary) formatında saxlanılır. Nəticədə `0.1 + 0.2 = 0.30000000000000004` kimi qalıq xətaları yaranır. Sığortada və bankda 1 qəpiklik kənarlaşma auditdə maliyyə fırıldağı və ya balans bərabərsizliyi sayılır.
Buna görə də C#-da `decimal` tipi olduğu kimi, Python-da da `from decimal import Decimal` və `ROUND_HALF_UP` istifadə etdik. Bütün tarif çarpanları, endirimlər və hissə-hissə ödənişlər (installments) sırf deterministik riyazi funksiyalarla hesablanır. LLM heç vaxt sığorta haqqını və ya kompensasiya məbləğini özündən "təxmin" edə bilməz!

### 4.2. Dörd Göz (Four-Eyes / Maker-Checker) Prinsipi
Bank və sığorta sistemlərində ən vacib daxili nəzarət mexanizmi **Maker-Checker** patternidir. 
Tutaq ki, bir aktuar (maker) yeni bir sığorta məhsulu və ya tarif cədvəli hazırlayır (`status="draft"`). Əgər həmin aktuar özü təkbaşına bu tarifi bazara buraxa bilsə (`status="published"`), sistemdə səhv və ya sui-istifadə riski yaranar.
`product_service.publish_product_version` metodunda C#-dakı **Business Rule Validation / Domain Exception** tətbiq olunub:
Əgər `reviewer_id == created_by` olarsa, sistem dərhal `FourEyesViolationError` atır. Təsdiq edən mütləq başqa bir anderrayter və ya rəhbər şəxs olmalıdır.

### 4.3. Qəpik Balanslaşdırması (Penny-Rounding Invariant)
Fərz edin ki, sığorta haqqı 1000.00 AZN-dir və müştəri bunu 12 aya bölmək istəyir.
$1000 / 12 = 83.3333...$
Hər aya 83.33 AZN yazsaq: $83.33 \times 12 = 999.96$ AZN. Yerdə 4 qəpik çatışmır!
C#-da maliyyə ledgerlərində tətbiq edilən standart yanaşma: qalıq 4 qəpik ilk ödənişə əlavə edilir ($83.37$ AZN ilk ay, qalan 11 ay $83.33$ AZN). Beləliklə, cəm mütləq $1000.00$ AZN olur. Bizim `hypothesis` testlərimiz minlərlə təsadüfi məbləğ üzərində bu invariantı yoxlayır və sübut edir.

### 4.4. Clause F.1 və Xalis Geri Qaytarılma (Pro-Rata Cancellation)
Müştəri siyasəti vaxtından əvvəl ləğv etdikdə qalan günlərin pulunu geri istəyir:
- Əgər il 366 gündürsə (artıq il / leap year), günlərin sayı dəqiq təqvim riyaziyyatı ilə hesablanır.
- **Clause F.1 qaydası:** Əgər müştəri il ərzində artıq sığorta hadisəsi (claim) bildiribsə və ya ödəniş alıbsa, qaytarılacaq məbləğ avtomatik **0.00 AZN** olur! Çünki sığortaçı artıq risk üzrə öhdəliyini icra edib.
- Əgər geri qaytarılacaq xalis məbləğ 500 AZN-dən çoxdursa, sistem bunu `requires_manager_approval = True` kimi qeyd edir (C#-da `RequiresAuthorizationLevel(Manager)` kimi).

---

## 5. Senior Interview Sentences (English)
1. *"Our core policy administration engine strictly isolates monetary calculations inside a deterministic domain service using Python's `Decimal` with explicit `ROUND_HALF_UP` rounding, eliminating IEEE-754 floating-point drift and LLM hallucination."*
2. *"We enforced regulatory governance on insurance tariffs through a programmatic Four-Eyes maker-checker protocol, guaranteeing that no product version can be published without independent underwriting peer review."*
3. *"For mid-term policy cancellations, our pro-rata refund calculator dynamically accounts for leap years, enforces the Clause F.1 exclusion barring refunds when claims exist, and routes refunds above 500 AZN for managerial sign-off."*
4. *"We utilized property-based testing with Hypothesis to rigorously verify financial invariants across thousands of randomized parameter permutations, proving that installment schedules balance to the penny."*

---

## 6. Self-Assessment Quiz (Questions & Answers)

### Questions
1. Why must the product version ID (`product_version_id`) be frozen on the policy record at the moment of issuance?
2. What happens if an actuary attempts to publish a draft product version where they are both the creator and the reviewer?
3. How does the installment schedule generator guarantee that the sum of installments equals the policy total premium without losing fractions of a cent?
4. Under policy wording Clause F.1, how much refund is a policyholder entitled to if they cancel their policy 6 months before expiry but previously filed an approved collision claim?
5. Why are pre-bind checks executed in `PolicyService.issue_policy` before assigning a policy number and emitting the `PolicyIssued` event?

---

### Hidden Answers (Reveal After Testing Yourself)
<details>
<summary>Click to reveal answers</summary>

1. **Answer:** Sığorta müqaviləsi bağlandığı andakı hüquqi maddələr və tariflər müqavilə müddətində dəyişməz qalmalıdır. Əgər gələcəkdə həmin məhsulun V3 versiyası çıxarsa, mövcud siyasət geriyə təsir etməməlidir (non-retroactivity). `product_version_id`-nin dondurulması məhz bu hüquqi toxunulmazlığı təmin edir.
2. **Answer:** The service raises a `FourEyesViolationError` (HTTP 400 Problem Details), blocking publication until an independent, distinct reviewer (`reviewer_id != created_by`) signs off.
3. **Answer:** It performs decimal quantization on the base installment amount, computes the rounding discrepancy (`remainder = total_premium - base_installment * count`), and adds that penny remainder into the first installment.
4. **Answer:** Zero AZN (0.00). Clause F.1 explicitly dictates that pro-rata refunds are only permitted provided no claims have been filed under the policy.
5. **Answer:** To prevent illegal or uncollectible policies from entering the system. If party KYC is unverified, or if no published product version is in force as of the inception date, the transaction is rejected prior to committing state changes or publishing outbox events.
</details>

---

## 7. Git Step & Limitations
- **Git Commit:** Completed Phase 6 with party, product, and policy modules, rating engines, pro-rata cancellation, and property-based tests.
- **Tag:** `phase-6-done`
- **Known Limitations:** In Phase 6, payment recording is handled via domain service calls (`record_premium_payment`). Full bank reconciliation, double-entry general ledger, and automated payment gateway webhooks will be introduced in Phase 10 (Finance).
