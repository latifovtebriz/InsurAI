# Phase 2 Package: Platform Core

## 1. Status
- **Phase:** Phase 2 (Platform Core)
- **Status:** COMPLETED
- **Completed Tasks:**
  - Task 2.1: Database architecture: SQLAlchemy 2.0 models for `platform` (`User`, `RolePermission`, `AuditLog`, `OutboxEvent`, `ProcessedEvent`, `Job`, `BusinessRuleModel`), common timestamp mixins, money conventions.
  - Task 2.2: Identity & RBAC: Salted PBKDF2-HMAC password hashing, JWT bearer tokens, role permission matrix per Architecture Section 3.12, `require_permission` FastAPI dependencies.
  - Task 2.3: Atomic audit logging (`record_audit_event`), committed within the caller's transaction.
  - Task 2.4: Declarative workflow engine (`workflow.py`) with state transitions, triggers, and guards for quotes, policies, claims, and invoices.
  - Task 2.5: Business rules engine integration with effective dating.
  - Task 2.6: Transactional outbox (`outbox.py`) with idempotent consumer dispatcher (`OutboxDispatcher`) and deduplication table (`processed_events`).
  - Task 2.7: Database-backed background job queue (`job_runner.py`) with atomic claim and timeout-based crash recovery.
  - Task 2.8: RFC 7807 Problem Details error response generator and correlation ID middleware propagation.
  - Task 2.9: Architecture tests and unit test suite verifying rollback atomicity, idempotent dispatch, crash recovery, and illegal transition rejection.
  - Task 2.10: Formally documented ADR-002, ADR-003, and ADR-008 in `DECISIONS.md`.

---

## 2. What Was Built & Key Files
- `backend/app/modules/platform/models.py`: Platform database entities with schema isolation.
- `backend/app/modules/platform/rbac.py`: PBKDF2 hashing, JWT tokens, and 8-role RBAC matrix.
- `backend/app/modules/platform/audit.py`: Append-only transactional audit trail.
- `backend/app/modules/platform/workflow.py`: Declarative state machine engine and lifecycle definitions.
- `backend/app/modules/platform/outbox.py`: Outbox event publisher and idempotent consumer dispatcher.
- `backend/app/modules/platform/job_runner.py`: Crash-resilient job runner.
- `backend/app/modules/platform/errors.py`: RFC 7807 Problem Details formatter.
- `backend/app/modules/platform/public.py`: Fully encapsulated public interface for the platform module.
- `backend/tests/unit/test_platform_core.py`: 9 comprehensive unit tests verifying all acceptance criteria.

---

## 3. How to Run and Verify
```powershell
# 1. Run complete platform core test suite
pytest backend/tests/unit/test_platform_core.py

# 2. Run full project test suite
pytest

# 3. Verify quality gates
ruff check .
mypy backend/app
python scripts/secret_scanner.py
```

---

## 4. Quality Report
- **Unit Tests:** 19 passed (9 platform core tests, 5 synthetic data tests, 3 health/readiness tests, 2 architecture boundary tests).
- **Atomicity Acceptance Criteria:** Passed (forced failure test confirms that business state and outbox events roll back atomically with 0 orphaned events).
- **Idempotency Acceptance Criteria:** Passed (simulated duplicated redelivery confirms consumers process each event exactly once).
- **Crash Recovery Criteria:** Passed (simulated crashed worker job is reclaimed after lock timeout and executed to completion exactly once).
- **Workflow State Machine:** Passed (illegal transitions raise `InvalidStateTransitionError` and execute zero mutations).
- **Linters & Types:** 0 ruff errors, 0 mypy issues across 41 source files.

---

## 5. Pre-Push Security Checklist (Appendix C)
- [x] No plaintext passwords: All credentials use salted PBKDF2-HMAC-SHA256 with 100,000 iterations.
- [x] JWT tokens signed with HMAC-SHA256 using configurable `JWT_SECRET`.
- [x] Secret scanner passed (`python scripts/secret_scanner.py`).

---

## 6. İzahlar (Azərbaycan dilində və C# Analoqları ilə)

### Nə etdik və Niyə belə etdik?
Phase 2 bütün biznes modullarının (`claims`, `policy`, `sales` və s.) üzərində işləyəcəyi texniki platforma nüvəsini qurdu:
1. **Transactional Outbox:** Paylanmış sistemlərdə və ya modullararası rabitədə ən böyük problem "Dual Write" problemidir: Məsələn, sığorta iddiası bazaya yazılır, amma hadisə mesajı (event) göndərilərkən şəbəkə xətası baş verir və ya əksinə. Biz Transactional Outbox ilə hadisəni iddia ilə eyni verilənlər bazası tranzaksiyasında `outbox_events` cədvəlinə yazırıq. Beləliklə, tranzaksiya rollback olsa, hadisə də ləğv edilir.
2. **Idempotent Consumers:** Hadisə təkrar göndərildikdə sistemin iki dəfə pul ödəməməsi və ya iki dəfə e-poçt atmaması üçün `processed_events` cədvəli ilə deduplikasiya tətbiq etdik.
3. **Declarative State Machines:** Sığorta iddiası birbaşa `fnol_received` vəziyyətindən `approved` vəziyyətinə keçə bilməz. Qanunsuz keçid cəhdləri avtomatik olaraq `InvalidStateTransitionError` xətası verir.
4. **Restart-Safe Job Runner:** Əgər arxa planda iş icra edən server çökərsə, `locked_at` vaxtı bitdikdən sonra digər işçi (worker) işi avtomatik bərpa edir və tamamlayır.

### C# / .NET Analoqları:
- **Transactional Outbox vs MassTransit / Wolverine Outbox:** .NET dünyasında MassTransit və ya Wolverine kitabxanalarında `UseEntityFrameworkOutbox<AppDbContext>()` necə işləyirsə, biz eyni mexanizmi SQLAlchemy tranzaksiyası daxilində qurduq.
- **Declarative State Machine vs Stateless / Automatonymous:** C#-da `Stateless` kitabxanası ilə `machine.Configure(ClaimStatus.Fnol).Permit(Trigger.Register, ClaimStatus.Registered)` yazdığımız kimi, burada da təmiz Python ilə bəyannaməli state machine yaratdıq.
- **Job Runner with SKIP LOCKED vs Hangfire / Quartz.NET:** SQL Server və ya PostgreSQL-də `SELECT ... WITH (ROWLOCK, READPAST)` (Postgres: `SKIP LOCKED`) ilə Hangfire-in arxa plan işlərini paylaması kimi, bizim JobRunner da kilidlənmiş işləri təhlükəsiz şəkildə worker-lərə paylayır.
- **RBAC Matrix vs ASP.NET Core Policy-Based Authorization:** `require_permission("claims:approve")` C#-dakı `[Authorize(Policy = "CanApproveClaims")]` atributunun FastAPI ekvivalentidir.

---

## 7. Interview Sentences (English)
1. "In Phase 2, I engineered the platform technical kernel, implementing the Transactional Outbox pattern to guarantee zero dual-write inconsistencies between domain state changes and asynchronous event dispatching."
2. "I developed an idempotent event dispatcher backed by database deduplication, ensuring that at-least-once message delivery never results in duplicate side-effects."
3. "To enforce strict domain lifecycles, I built a declarative state machine engine with transition guards that programmatically prevents unauthorized or illegal entity state changes."

---

## 8. Five Self-Check Questions

1. **Concept:** What is the dual-write problem, and how does the Transactional Outbox pattern solve it?
2. **Code Reading:** In `backend/app/modules/platform/outbox.py`, how does `OutboxDispatcher` guarantee that a duplicated event is not executed twice by the same consumer?
3. **Design Trade-off:** Why did we implement our own lightweight declarative state machine rather than relying on mutable boolean columns (e.g. `is_approved`, `is_rejected`)?
4. **Failure Scenario:** If a background worker node is abruptly killed (SIGKILL) while processing a job, how does `JobRunner.claim_next_job` ensure the job is not permanently lost?
5. **What would you change:** Under high event throughput (e.g., 10,000 events/second), what architectural component would replace direct PostgreSQL table polling for the outbox?

---

### Hidden Answers:
<!--
Answers:
1. The dual-write problem occurs when writing to a database and publishing to an external message broker in a single logical operation without distributed transactions; if either fails after the other succeeds, state becomes inconsistent. The Outbox pattern writes the event into an outbox table in the same local database transaction as the entity mutation, ensuring atomic all-or-nothing guarantees.
2. It queries `platform.processed_events` for the composite key `(event_id, consumer_name)`. If a record already exists, it skips invoking the handler.
3. Boolean flags permit contradictory states (e.g. `is_approved=True` and `is_rejected=True`) and allow bypassing mandatory intermediate lifecycle stages (like triage or underwriter review). A state machine strictly enforces valid sequences.
4. It checks for jobs in `running` status whose `locked_at` timestamp is older than `lock_timeout_seconds` (orphaned jobs), allowing another worker to reclaim and resume the job.
5. Debezium or PostgreSQL Change Data Capture (CDC) streaming logical replication WAL logs directly into Apache Kafka or RabbitMQ, eliminating database polling entirely.
-->

---

## 8b. Known Limitations & Next-Phase Preview
- **Next Phase (Phase 3):** LLM Gateway and Structured Extraction (`LLMClient` protocol, Google GenAI / Gemini implementation, Fake and Record-and-Replay clients, prompt versioning, structured extraction service for FNOL text and quotes with validation and injection defense).
