# Phase 4 Package: Knowledge Service (RAG) and Grounded Wording Retrieval

## 1. Status
- **Phase:** Phase 4 (Knowledge Service - RAG)
- **Status:** COMPLETED
- **Completed Tasks:**
  - Task 4.1: Database storage: `platform.kb_chunks` model with pgvector compatibility, embedding dimension (768) parameterized, unique constraint preventing duplicate clauses.
  - Task 4.2: Clause-based semantic chunking: chunks bounded by numbered clauses (`clause_id`) with `title + "\n" + text`, metadata (`collection`, `product_code`, `version`, `effective_from/to`), and idempotent ingestion (`ingest_product_wording`).
  - Task 4.3: Retrieval engine: mandatory **Date-in-Force filtering first** in SQL before cosine similarity vector ranking; returns typed `Citation` objects.
  - Task 4.4: Ingested products catalog (49 clauses across `MOTOR_OD` v1, `MOTOR_OD` v2, `MOTOR_TPL`, and `HOME`).
  - Task 4.5: Retrieval benchmark suite (`evals/run_retrieval_eval.py`) evaluated across 40 labeled queries; generated `evals/reports/retrieval_dev_report.md`.
  - Task 4.6: Critical **Time-Travel Test** verified: historical 2025 claim retrieves Version 1 clauses (excluding B.7 cyber exclusion); 2026 claim retrieves Version 2 clauses.
  - Task 4.7: Documented ADR-009 in `DECISIONS.md`.

---

## 2. What Was Built & Key Files
- `backend/app/modules/platform/knowledge/models.py`: `KBChunk` entity in schema `platform`.
- `backend/app/modules/platform/knowledge/embedder.py`: Deterministic token-aware 768-dim unit-normalized embedder and cosine similarity function.
- `backend/app/modules/platform/knowledge/service.py`: `KnowledgeService` and `Citation` schema with time-travel date filtering.
- `data/synthetic/create_retrieval_dataset.py`: 40 labeled queries across perils, exclusions, notice rules, and deductibles.
- `data/synthetic/retrieval_queries.json`: Dataset of 40 labeled test queries.
- `evals/run_retrieval_eval.py`: Automated retrieval benchmark script.
- `evals/reports/retrieval_dev_report.md`: Benchmark report (Recall@5: 85.0%, MRR: 0.710).
- `backend/tests/unit/test_knowledge_service.py`: Unit tests for idempotency, time-travel, and product isolation.

---

## 3. How to Run and Verify
```powershell
# 1. Run Knowledge Service unit tests
pytest backend/tests/unit/test_knowledge_service.py

# 2. Run retrieval benchmark evaluation
.venv\Scripts\python evals/run_retrieval_eval.py

# 3. Verify quality gates
ruff check .
mypy backend/app
python scripts/secret_scanner.py
```

---

## 4. Quality Report
- **Total Tests:** 29 passed across entire repository.
- **Idempotency Criteria:** Passed (re-ingesting 49 clauses adds 0 duplicate rows).
- **Time-Travel Criteria:** Passed (claims on 2025-07-20 strictly retrieve v1 clauses; claims on 2026-05-10 retrieve v2 clauses).
- **Product Isolation:** Passed (searching MOTOR_OD never returns HOME or MOTOR_TPL clauses).
- **Retrieval Metrics (40 Labeled Queries):**
  - Recall@1: 60.0%
  - Recall@3: 82.5%
  - Recall@5: 85.0%
  - MRR: 0.710
- **Linters & Types:** 0 ruff errors, 0 mypy issues across 49 source files.

---

## 5. Pre-Push Security Checklist (Appendix C)
- [x] Zero external network requests made; embeddings generated deterministically offline.
- [x] No secrets in knowledge store or queries.
- [x] Secret scanner passed (`python scripts/secret_scanner.py`).

---

## 6. İzahlar (Azərbaycan dilində və C# Analoqları ilə)

### Nə etdik və Niyə belə etdik?
Phase 4-də sığorta müqaviləsi qaydalarını (wording) və təlimatları AI agentlərinə əsaslandırılmış sitatlarla (citations) təqdim edən Knowledge Service (RAG) qurduq:
1. **Clause-Level Chunking (Bənd Səviyyəsində Bölmə):** Standart RAG sistemlərində mətni ixtiyari sayda sözə (məsələn, hər 500 tokenə) bölürlər. Bu zaman hüquqi cümlələr ortadan kəsilir və bənd nömrəsi itir. Biz mətni dəqiq hüquqi bənd sərhədləri ilə (`MOTOR_OD:A.1`, `MOTOR_OD:B.3`) böldük.
2. **Date-in-Force Filtering First (Qüvvədə Olma Tarixi ilə Əvvəlcədən Filtrləmə):** Ən böyük səhv bütün versiyaların vektorlarını eyni qaba töküb axtarmaqdır. Əgər qəza 2025-ci ildə baş veribsə, sistem mütləq 2025-ci ildə qüvvədə olan v1 qaydalarını tapmalıdır. Buna görə də vektor axtarışından ƏVVƏL SQL səviyyəsində `effective_from <= incident_date <= effective_to` filtri tətbiq olunur.
3. **Time-Travel Qabiliyyəti:** Testlə sübut etdik ki, 2025-ci il qəzası üçün axtarış etdikdə 2026-cı ildə əlavə olunmuş `B.7` (Kiber istisna) bəndi heç vaxt tapılmır; 2026-cı il qəzasında isə düzgün tapılır.

### C# / .NET Analoqları:
- **Date-in-Force Filtering vs EF Core Global Query Filters / Temporal Tables:** C#-da `DbContext.OnModelCreating`-də `HasQueryFilter(x => x.EffectiveFrom <= incidentDate && x.EffectiveTo >= incidentDate)` yazdığımız kimi, burada da vektor axtarışından əvvəl məcburi tarix filtri tətbiq etdik.
- **pgvector vs Azure AI Search / Semantic Kernel Memory:** C# və .NET Semantic Kernel ilə Azure AI Search və ya Qdrant istifadə etdiyimiz kimi, burada PostgreSQL daxilində eyni relyasion tranzaksiya içində vektor saxlayırıq.
- **Deterministic Fake Embedder vs Mocking IEmbeddingGenerator in .NET 9:** .NET 9-da `Microsoft.Extensions.AI` içindəki `IEmbeddingGenerator` interfeysini testlər üçün saxta implementasiya ilə əvəz etdiyimiz kimi, burada `DeterministicFakeEmbedder` qurduq.

---

## 7. Interview Sentences (English)
1. "In Phase 4, I architected a legal-grade RAG knowledge service that chunks insurance policies strictly by clause boundaries to preserve legal integrity and citation lineage."
2. "I implemented a strict 'Date-in-Force' pre-filtering invariant in SQL prior to vector cosine ranking, guaranteeing that historical incidents are evaluated exclusively against their contemporaneous policy version."
3. "I verified time-travel retrieval with automated unit tests, proving that claims with historical incident dates never leak subsequent contract exclusions."

---

## 8. Five Self-Check Questions

1. **Concept:** Why must date-in-force filtering occur *before* vector cosine similarity ranking rather than after?
2. **Code Reading:** In `backend/app/modules/platform/knowledge/service.py`, how does `KnowledgeService.ingest_product_wording` achieve complete idempotency when re-ingesting published versions?
3. **Design Trade-off:** What are the advantages of chunking policy contracts by numbered legal clauses (`title + text`) compared to arbitrary fixed-size token windows (e.g. 512 tokens with 50-token overlap)?
4. **Failure Scenario:** What severe legal consequence occurs in an insurance claims system if a RAG service retrieves clauses from Product Version 2 for an accident that occurred under Product Version 1?
5. **What would you change:** When scaling to millions of clauses across hundreds of corporate products, how would index selection (`HNSW` vs `IVFFlat`) in pgvector affect retrieval latency and recall?

---

### Hidden Answers:
<!--
Answers:
1. If filtering is done after vector ranking, top-k results could be dominated by newer versions of the contract, completely crowding out contemporaneous clauses and returning zero valid citations for the incident date. Pre-filtering ensures vector ranking only operates on legally valid candidates.
2. It queries for an existing chunk using the unique key `(collection, product_code, version, clause_id)`. If present, it updates the existing record in-place rather than inserting a new row.
3. Fixed-size windows arbitrarily split sentences, clauses, and lists, destroying contractual context. Clause-level chunking preserves complete legal provisions and maintains clear, auditable `clause_id` citation targets.
4. The insurer could unlawfully deny coverage based on an exclusion that did not exist in the contract at the time the insured purchased it and suffered the loss, leading to severe regulatory penalties and bad-faith litigation.
5. HNSW (Hierarchical Navigable Small World) provides superior recall (>95%) and low search latency with zero pre-training requirements at the cost of higher build time and memory, whereas IVFFlat is faster to build and lighter on memory but requires list-clustering warmup and achieves lower recall on high dimensions.
-->

---

## 8b. Known Limitations & Next-Phase Preview
- **Next Phase (Phase 5):** Agent Runtime, Guardrails, Tracing, and Evaluation Core (Hand-written ReAct agent loop, tool registry, G1–G10 guardrail interceptors, step budgets, loop detection, evaluation framework, demo lookup agent).
