# Phase 11 Package: Fraud & SIU (A5), Compliance & Sanctions (A8), Customer Service (A6), and Policy Servicing (A3) -> Release R2

**Mərhələ:** Phase 11 (Release R2 Complete)  
**Status:** Tamamlandı (Verified & Evaluated)  
**Tarix:** 2026-10-12  
**Əhatə:** 
- `fraud` modulu: Şəffaf siqnallar (FS-01..06), SIU marşrutlaşdırması ($\ge 70$), Guardrail G8 neytral dil yoxlaması, Guardrail G9 ədalətlilik (fairness).
- `compliance` modulu: OFAC/UN/PEP siyahıları üzrə qeyri-səlis (fuzzy Jaccard) axtarış, Agent A8 (Compliance Explainer), AI avtomatik təmizləmə qadağası (never-clears invariant), insan zabiti qərarı.
- `service` modulu: Agent A6 Müştəri Xidməti (Identity Verification Gate), Agent A3 Siyasət Servisi (Mid-term Endorsement P06, pro-rata hesablama, L2 nəzarəti), şikayətlərin 5/15 günlük qanuni SLA izlənməsi.
- Veb Konsol v2: `SIUScreen.tsx`, `ComplianceScreen.tsx`, `CustomerServiceScreen.tsx`.

---

## 1. Summary of Changes

### A. Fraud Detection & Special Investigation Unit (Agent A5)
1. **Şəffaf Qaydalar Mühərriki (`backend/app/modules/fraud/engine.py`):**
   - 6 izaholunan risk siqnalı:
     - `FS-01`: Müqavilə bağlandıqdan dərhal sonra (14 gün ərzində) baş verən hadisə (+25 bal).
     - `FS-02`: Qeyri-mütənasib zərər şiddəti (iddia məbləği sığorta təminatının 80%-ni aşır, +20 bal).
     - `FS-03`: Tezlik anomaliyası (son 180 gündə 2 və ya daha çox təkrar iddia, +30 bal).
     - `FS-04`: Rəsmi DYP/polis protokolunun olmaması (+15 bal).
     - `FS-05`: Gecikdirilmiş bildiriş (3 iş günündən sonra, +15 bal).
     - `FS-06`: Gecə tək avtomobil hadisəsi (şahid yoxdur, +10 bal).
   - Ümumi risk balı $\ge 70$ olduqda sistem avtomatik olaraq iddia faylını SIU işləri siyahısına yönləndirir (`status="referred_to_siu"`).
2. **Guardrail G9 Ədalətlilik Qorunması (Fairness Protection):**
   - Qorunan demoqrafik göstəricilər (`gender`, `race`, `ethnicity`, `nationality`, `religion`, `postal_code`) risk qiymətləndirməsinə daxil edildikdə mühərrik dərhal `FairnessViolationError` istisnası atır.
3. **Agent A5 SIU Köməkçisi (`backend/app/modules/fraud/agent.py`):**
   - **Guardrail G8 Neytral Dil İcra Mühərriki (`validate_neutral_language`, `sanitize_neutral_language`):** Agentin tərtib etdiyi dosye və qeydlərdə ittihamedici sözlər (`fraud`, `fraudster`, `criminal`, `staged`, `lies`, `fake`, `scam`) qəti şəkildə qadağandır. Bu terminlər obyektiv sığorta terminləri ilə əvəzlənir (`potential inconsistency`, `unwitnessed pattern`, `discrepancy`).

### B. Compliance & Sanctions Screening (Agent A8)
1. **Qeyri-səlis Axtarış Mühərriki (`backend/app/modules/compliance/matcher.py`):**
   - Token Jaccard, Token Containment və Bi-gram hərfi oxşarlıq metriklərindən istifadə edərək ad və vergi nömrəsi (VÖEN/FIN) üzrə OFAC SDN, BMT Təhlükəsizlik Şurası və PEP kataloqları üzrə yoxlama aparır.
2. **Agent A8 Tənzimləyici Qadağası (`backend/app/modules/compliance/agent.py`):**
   - **Never-Clears Invariant:** Agent A8 heç bir halda sanksiya siqnalını avtomatik təmizləyə (`auto_cleared=False`) bilməz. `attempt_auto_clear()` çağırışı birbaşa `PermissionError` atır.
   - A8 zabitə uyğunluq səbəblərini izah edir və Şübhəli Əməliyyat Hesabatı (SAR - Suspicious Activity Report) layihəsini tərtib edir.
3. **İnsan Zabitinin Qərarı (`adjudicate_alert`):**
   - Qərar yalnız səlahiyyətli AML zabiti tərəfindən yazılı əsaslandırma ilə qəbul edilə bilər (`confirmed_hit` və ya `false_positive_cleared_by_officer`).

### C. Customer Service (A6) & Policy Servicing (A3)
1. **Agent A6 Kimlik Təsdiqləmə Şlüzü (Verification Gate):**
   - Autentifikasiyadan keçməmiş qonaq istifadəçilər yalnız ictimai sığorta qaydaları və FAQ məlumatlarını ala bilər.
   - Sığorta müqaviləsi nömrəsi, təminat məbləği və ya iddia statusu soruşulduqda, şlüz sıfır sızma ilə dərhal təsdiqləmə tələb edir (`action_taken="PROMPT_AUTHENTICATION"`).
2. **Agent A3 Sığorta Xidməti (Endorsements P06):**
   - Müddətdaxili dəyişikliklər (məsələn, sığorta təminatının artırılması) zamanı qalan günlərə mütənasib olaraq dəqiq pro-rata əlavə haqq hesablayır:
     $$\Delta P = (V_{yeni} - V_{kohne}) \times \text{Tarif} \times \left(\frac{T_{qalan}}{T_{umumi}}\right)$$
   - L2 Qayda Nəzarəti: Dəyişikliyin qüvvəyə minməsi üçün anderrayterin təsdiqi mütləqdir.
3. **Müştəri Şikayətləri və Qanuni SLA-lar:**
   - 5 təqvim günü ərzində ilkin cavab və 15 təqvim günü ərzində yekun qərar qanuni müddətləri (`initial_response_deadline`, `final_resolution_deadline`).
   - Gecikmə halında avtomatik Ombudsman eskalasiyası (`sla_breached=True`).

### D. REST API və Veb Konsol v2
- `/api/v1/siu/*`: İşlərin siyahısı, Agent A5 qiymətləndirməsi, işlərin yenilənməsi.
- `/api/v1/compliance/*`: Sanksiya skrininqi, Agent A8 analizi, zabit qərarı.
- `/api/v1/service/*`: A6 müştəri söhbəti, A3 zəmanət layihəsi, şikayətlər.
- Frontend ekranları: `SIUScreen.tsx`, `ComplianceScreen.tsx`, `CustomerServiceScreen.tsx`.

---

## 2. How to Run and Verify

```bash
# 1. Bütün testləri işə salın
.\.venv\Scripts\pytest backend/tests/unit/test_fraud_and_a5.py
.\.venv\Scripts\pytest backend/tests/unit/test_compliance_and_a8.py
.\.venv\Scripts\pytest backend/tests/unit/test_service_and_agents.py
.\.venv\Scripts\pytest backend/tests/unit/test_r2_apis.py
.\.venv\Scripts\pytest backend/tests/unit/
.\.venv\Scripts\pytest backend/tests/architecture/

# 2. Kod keyfiyyəti və tip təhlükəsizliyi
.\.venv\Scripts\ruff check backend/
.\.venv\Scripts\mypy backend/app

# 3. Agent qiymətləndirmə skripti (A5, A8, A6, A3)
.\.venv\Scripts\python evals/run_r2_agents_eval.py

# 4. Frontend yoxlanışı
cd frontend
npm run build
```

---

## 3. Acceptance Checklist

| Tələb / Standart | Gözlənilən Nəticə | Real Status | Qeyd |
| :--- | :--- | :--- | :--- |
| **Agent A5 G8 Neytral Dil** | 100.0% sıfır ittihamedici söz | **100.0% PASS** | 50 ssenaridə yoxlanıldı (`fraud_a5_report.md`) |
| **Agent A5 G9 Ədalətlilik** | Qorunan demoqrafikada dərhal xəta | **100.0% PASS** | `FairnessViolationError` atıldı |
| **Agent A8 AI Non-Clearance** | AI heç vaxt sanksiyanı təmizləyə bilməz | **100.0% PASS** | `PermissionError` məcburi qorunur (`compliance_a8_report.md`) |
| **Agent A6 Kimlik Şlüzü** | Qonaq istifadəçilərə sıfır məlumat sızması | **100.0% PASS** | `PROMPT_AUTHENTICATION` tələb edildi (`service_a6_report.md`) |
| **Agent A3 Pro-Rata Dəqiqliyi** | Riyazi fərq $\Delta = 0.00$ AZN | **100.0% PASS** | 50 ssenaridə tam dəqiqlik (`servicing_a3_report.md`) |
| **Şikayət Qanuni SLA-ları** | 5 gün ilkin, 15 gün yekun müddət | **100.0% PASS** | Gecikmədə Ombudsman eskalasiyası |
| **Unit Testlər** | $\ge 110$ vahid testi yaşıl | **114/114 PASS** | 0 reqressiya |
| **Arxitektura Testləri** | Modullararası izolyasiya | **2/2 PASS** | AST səviyyəsində yoxlandı |
| **Ruff Linter** | 0 xəta | **0 ISSUES** | Bütün fayllar təmizdir |
| **Mypy Static Typing** | 0 xəta | **0 ISSUES** | 109 mənbə faylı yoxlandı |
| **Frontend Production Build** | TypeScript & Vite təmiz yığılma | **PASS** | `dist/` uğurla yaradıldı |

---

## 4. Explanations in Azerbaijani with C# Analogies

### 1. Guardrail G8 və Neytral Dil Niyə Həyati Əhəmiyyət Kəsb Edir?
Sığorta şirkətlərində SIU (Xüsusi Təhqiqat Şöbəsi) daxili qeydlər apararkən hüquqi məsuliyyət daşıyır. Əgər süni intellekt və ya anderrayter müştərinin iddia faylında "bu adam fırıldaqçıdır (fraudster)" və ya "saxta qəzadır (staged accident)" yazarsa, sabah məhkəmə və ya Ombudsman bu sənədi tələb etdikdə şirkət böhtan (defamation) və qərəz ittihamı ilə cərimələnə bilər.
- **C# Analogiyası:** Təsəvvür edin ki, ASP.NET Core-da `IOutputFilter` və ya `ActionFilterAttribute` yazmısınız. Model `OnActionExecuted` mərhələsindən keçərkən `Regex.Replace` ilə qadağan olunmuş kəskin leksika obyektiv sığorta terminləri ilə əvəzlənir və `ImmutableRecord` yaradılır.

### 2. Sanksiya Yoxlamasında AI Qadağası (Agent A8 Never-Clears)
Maliyyə monitorinqi və çirkli pulların yuyulmasına qarşı mübarizə (AML) qanunvericiliyinə əsasən, beynəlxalq sanksiya siyahısına (OFAC, UN) düşən şəxsin blokdan çıxarılması qərarını heç bir alqoritm təkbaşına verə bilməz. Məsuliyyət yalnız fiziki şəxsin — Komplayens Zabitinin üzərində olmalıdır.
- **C# Analogiyası:** Bu, C#-da `internal` metodun icazəsiz çağırışında dərhal `UnauthorizedAccessException` atmasına bənzəyir:
  ```csharp
  public void AttemptAutoClear(string alertId) =>
      throw new UnauthorizedAccessException("AI is legally prohibited from clearing sanctions hits.");
  ```
  Yalnız `[Authorize(Roles = "ComplianceOfficer")]` atributu olan metod qərar qəbul edə bilər.

### 3. Agent A6 Kimlik Təsdiqləmə Şlüzü (Verification Gate)
İstifadəçi "Mənim sığortam nə vaxt bitir?" soruşduqda, əgər sessiya təsdiqlənməyibsə (`is_authenticated == false`), sistem heç bir şəxsi məlumatı göstərmir.
- **C# Analogiyası:** Bu, ASP.NET Core-da `[Authorize]` filtrinin işinə bənzəyir: ictimai endpoint (`[AllowAnonymous]`) ümumi FAQ qaytarır, lakin şəxsi məlumat tələb olunan kimi `401 Challenge` verilir.

### 4. Agent A3 və Pro-rata Dəqiq Hesablama (Process P06)
Müştəri ilin ortasında avtomobilinin sığorta məbləğini artırdıqda, əlavə sığorta haqqı qalan günlərin sayına mütənasib olaraq dəqiq günlərlə hesablanır. Heç bir təxmini faiz və ya LLM riyaziyyatı yoxdur — hər şey deterministik maliyyə riyaziyyatı ilə hesablanır.
- **C# Analogiyası:** .NET-də `decimal` tipi və `MidpointRounding.AwayFromZero` istifadə edərək `(endDate - effectiveDate).TotalDays` üzərindən hesablanan maliyyə mühərriki.

---

## 5. Interview Sentences (English)

1. *"In Release R2, we deployed Agent A5 for fraud detection, backed by two strict architectural guardrails: G9 for demographic fairness protection and G8 to enforce neutral, objective language in SIU dossiers, eliminating legal defamation risks."*
2. *"Regulatory compliance mandates that automated models can never unilaterally clear a sanctions or PEP hit; therefore, Agent A8 acts strictly as an explainer and SAR drafter, while final clearance requires human Compliance Officer sign-off."*
3. *"Customer Service Agent A6 features an identity verification gate that prevents PII leakage to unauthenticated sessions, falling back cleanly to public insurance FAQ retrieval."*
4. *"For mid-term endorsements (Process P06), Agent A3 pairs deterministic pro-rata monetary calculations with Level 2 human-in-the-loop underwriter sign-off before altering any bound policy."*

---

## 6. Self-Assessment Questions & Answers

### Sual 1:
Niyə Agent A5-in çıxardığı təhqiqat qeydlərində "fırıldaqçı" və ya "cinayətkar" kimi sözlər qadağandır?
*(Cavab sənədin sonunda gizlədilib)*

### Sual 2:
Agent A8 sanksiya xəbərdarlığını (alert) süni intellekt vasitəsilə "təmiz" elan edə bilərmi? Bu qayda memarlıqda necə qorunur?
*(Cavab sənədin sonunda gizlədilib)*

### Sual 3:
Agent A6 qonaq (autentifikasiyadan keçməmiş) istifadəçinin sığorta müqaviləsi sorğusuna necə reaksiya verir?
*(Cavab sənədin sonunda gizlədilib)*

### Sual 4:
Müddətdaxili dəyişiklikdə (endorsement) əlavə sığorta haqqı hansı düsturla hesablanır və nə üçün LLM-ə etibar edilmir?
*(Cavab sənədin sonunda gizlədilib)*

### Sual 5:
Sığortaçının qanuni şikayət (complaint) cavablandırma və həll müddətləri nə qədərdir və bu müddət pozularsa nə baş verir?
*(Cavab sənədin sonunda gizlədilib)*

---

### Gizli Cavablar (Hidden Answers)

<details>
<summary>Cavabları göstər</summary>

1. **Cavab 1:** Çünki məhkəmə və Ombudsman araşdırmalarında daxili qeydlər sübut kimi tələb oluna bilər. Obyektiv faktlar sübuta yetirilmədən ittihamedici dildən istifadə şirkət üçün böhtan və reputasiya riskləri yaradır. Guardrail G8 bu sözləri neytral ifadələrlə əvəzləyir.
2. **Cavab 2:** Xeyr, qətiyyən bilməz. Beynəlxalq maliyyə monitorinqi qaydalarına görə sanksiya uyğunluğunu yalnız səlahiyyətli insan (Komplayens Zabiti) təmizləyə bilər. Memarlıqda `attempt_auto_clear` metodu `PermissionError` atır və AST testləri ilə qorunur.
3. **Cavab 3:** Qonaq istifadəçiyə heç bir fərdi sığorta və ya iddia məlumatı sızdırılmır (`data_accessed=False`). Sistem `action_taken="PROMPT_AUTHENTICATION"` statusu qaytararaq VÖEN/FİN və telefon ilə daxil olmağı tələb edir.
4. **Cavab 4:** Dəyişiklik qalan günlərin ümumi günlərə nisbəti ($\frac{T_{qalan}}{T_{umumi}}$) vurulsun illik tarif fərqi düsturu ilə hesablanır. LLM hallüsinasiya edə və qeyri-dəqiq yuvarlaqlaşdıra biləcəyi üçün yalnız `Decimal` deterministik Python mühərriki istifadə edilir.
5. **Cavab 5:** Qanunvericiliyə əsasən ilkin reaksiya müddəti 5 təqvim günü, yekun araşdırma və qərar müddəti isə 15 təqvim günüdür. 15 gün keçdikdən sonra iş avtomatik olaraq Ombudsman eskalasiyası (`sla_breached=True`) kimi qeyd olunur.

</details>

---

## 7. Git Step & Known Limitations

- **Git Tag:** `phase-11-done` və `release-R2`.
- **Məlum Məhdudiyyətlər:**
  - `LLM_API_KEY` olmadığı üçün Agent A5 və A8 oflayn deterministik qoruyucu və simulyasiya edilmiş ReAct rejimində işləyir (`plumbing only, fake LLM, not a quality measurement`).
  - Sanksiya kataloqu simulyasiya edilmiş 5 əsas təşkilat və şəxslə seed edilir; real istehsalat mühitində gündəlik OFAC XML feed inteqrasiyası tələb olunur.
