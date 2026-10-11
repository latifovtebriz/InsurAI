# InsurAI Phase 5 Package: Agent Runtime, Guardrails Pipeline, Tracing & Evaluation Core

## 1. Summary of Completed Work
In Phase 5, we engineered the autonomous agent foundation of InsurAI without relying on heavy third-party agent frameworks (like LangChain or CrewAI):
- **Hand-written ReAct Runtime Loop (`AgentLoop`):** Implemented an explicit, deterministic reasoning-and-acting loop with configurable step budgets (`agent_max_steps`), loop detection (aborting on 3 consecutive identical tool calls), and automatic fail-safe fallback to human review (`needs_human_review`).
- **Tool Registry & Declarations (`ToolRegistry`, `ToolDefinition`):** Typed tool definitions validated with Pydantic v2 schemas and classified into functional categories (`read`, `propose`, `terminal`).
- **Pluggable Guardrail Pipeline (`GuardrailPipeline`):** Enforces deterministic safety rules G1 through G10:
  - **G1 (Grounded Citations):** Prohibits recommendations from citing policy clauses not retrieved during the active session.
  - **G2 (Mathematical Invariant):** Enforces that the agent's proposed payable amount matches the deterministic calculation engine within \$0.01 tolerance.
  - **G3 (Terminal Rejection Guard):** Mandates that any claim denial requires human adjuster sign-off.
  - **G4 (Confidence & Risk Floor):** Intercepts low-confidence decisions (< 0.70) or cases with risk flags / missing data and downgrades them to human review.
  - **G5 (Mandatory Tool Execution):** Verifies that mandatory policy validation and wording search tools were executed.
  - **G7 (Prompt Injection Scanner):** Intercepts adversarial jailbreaks or overrides in raw narrative inputs.
  - **G10 (Non-negative Payout):** Prevents negative monetary payouts.
- **Persistent Database Tracing (`AgentRun`, `AgentStep`):** Schema-isolated tables in `platform` capturing end-to-end execution metadata, tokens, cost estimates, latencies, tool inputs/outputs, and guardrail decisions.
- **Evaluation Framework (`evals/run_eval.py`, `evals/compare_runs.py`):** Unified harness running extraction and retrieval benchmark suites, generating delta reports between runs.
- **Demo Agent (`ClauseLookupAgent`):** Verifies end-to-end integration between Knowledge Service, Tool Registry, and Agent Loop.

---

## 2. How to Run and Verify
```bash
# 1. Run all unit and architecture tests
pytest backend/tests/unit/test_agent_runtime.py -v
pytest backend/tests -v

# 2. Run Ruff and Mypy
ruff check .
mypy backend

# 3. Run the unified evaluation CLI on dev split
python evals/run_eval.py --split dev

# 4. Compare baseline with a test run
python evals/compare_runs.py evals/reports/unified_eval_dev.json evals/reports/unified_eval_dev.json
```

---

## 3. Acceptance Checklist
- [x] Hand-written ReAct loop with step budget (`max_steps`) and loop detector (3 identical calls)
- [x] Strongly typed `ToolDefinition` with Pydantic schema validation and `ToolCategory` (`read`, `propose`, `terminal`)
- [x] Pluggable `GuardrailPipeline` with G1–G10 rules intercepting recommendations
- [x] Tracing entities `AgentRun` and `AgentStep` persisted to database
- [x] Unified evaluation runner (`evals/run_eval.py`) and comparison script (`evals/compare_runs.py`)
- [x] 100% test pass rate (12 runtime unit tests, 41 total unit/arch tests)
- [x] Architecture tests verify zero illegal inter-module imports
- [x] Secret scanner confirms 0 secrets committed

---

## 4. Azərbaycan Dilində İzah və C# Analogiyaları

### 4.1. Niyə LangChain və ya CrewAI Yox, Əllə Yazılmış ReAct Dövrü?
C# və .NET dünyasında böyük enterprayz layihələrdə tez-tez belə bir qayda var: *“Sisteminizin əsas biznes nüvəsini üçüncü tərəf "black-box" framework-lərə bağlamayın”*. Əgər siz MediatR və ya MassTransit əvəzinə daxili strukturu naməlum, hər həftə breaking-change buraxan bir kitabxanadan istifadə etsəniz, tənzimləyici (Mərkəzi Bank və ya sığorta auditoru) audit edəndə sistemin niyə belə qərar verdiyini sübut edə bilməyəcəksiniz.
`AgentLoop` məhz C#-dakı **Workflow State Machine / Coroutine Engine** kimidir. Hər addımda modeldən nə gəldi, hansı Tool çağırıldı, neçə millaniyə çəkdi, hansı parametr göndərildi – hamısı `AgentStep` cədvəlində qeyd olunur.

### 4.2. ToolRegistry və C# MEF / Dependency Injection
`ToolRegistry` C#-da `IServiceCollection` və ya `MEF` (Managed Extensibility Framework) kimidir:
- Hər bir tool (`ToolDefinition`) bir interfeys/kontrakt kimidir.
- Pydantic modeli C#-dakı `Record` və ya `DataContract` kimidir (`SimpleAddArgs`). İstifadəçi və ya LLM səhv arqument göndərsə, tool icra olunmur, avtomatik model validasiya xətası (`ValidationError` -> `BadRequestException`) qaytarılır.
- Tool kateqoriyaları (`read`, `propose`, `terminal`) sistemin təhlükəsizliyini təmin edir: oxuma tool-ları yan təsirsizdir, terminal tool isə dövrü bitirir və qərarı mühafizə filtrlərinə ötürür.

### 4.3. Guardrails Pipeline və ASP.NET Core Middleware / ActionFilter
C#-da API-yə daxil olan və çıxan sorğuları yoxlamaq üçün **ActionFilter** və ya **Middleware Pipeline** yazırsınız (`app.UseAuthentication()`, `app.UseAuthorization()`, `OnActionExecuting`).
`GuardrailPipeline` məhz bu mexanizmdir:
- LLM nə qədər "ağıllı" və inamlı görünürsə görünsün, onun çıxardığı tövsiyə birbaşa bazaya və ya istifadəçiyə getmir.
- **G1 (Grounded Citations):** Əgər LLM sığorta qərarında bir maddəyə istinad edirsə, pipeline yoxlayır: bu maddə bu sessiyada RAG axtarışından həqiqətən qayıtmışdımı? Əgər model özündən maddə uydurubsa (hallusinasiya), qərar dərhal insan baxışına (`needs_human_review`) yönləndirilir.
- **G2 (Mathematical Invariant):** Əgər model ödəniş məbləğini \$1200 təklif edirsə, amma bizim deterministik C# style kalkulyatorumuz \$1000 hesablayıbsa, fərq aşkar olunur və təsdiq bloklanır.
- **G3 (Terminal Rejection):** Sığorta iddiasının rədd edilməsi heç vaxt tam avtomatik (L3) ola bilməz; mütləq insan anderrayterin və ya tənzimləyicinin imzası tələb olunur.

### 4.4. Tracing və OpenTelemetry ActivitySource
`AgentRun` və `AgentStep` modelləri C# dünyasındakı **System.Diagnostics.ActivitySource / OpenTelemetry distributed tracing** standartı ilə eynidir. Hər bir agent icrası tək bir `CorrelationId` ilə bağlanır. Sabah müştəri şikayət etsə: "Mənim iddiamı niyə rədd etdiniz?", audit loqundan saniyəbəsaniyə modelin hansı addımları atdığı sübut edilə bilər.

---

## 5. Senior Interview Sentences (English)
1. *"Rather than relying on opaque agent orchestration frameworks like LangChain, we implemented a deterministic, hand-written ReAct loop with explicit step budgeting and infinite-loop detection."*
2. *"Our safety architecture decouples generative reasoning from domain verification through an interceptor Guardrail Pipeline that enforces grounding invariants, mathematical equivalence, and mandatory human sign-off on terminal rejections."*
3. *"Every tool in our registry is strongly typed and validated against Pydantic schemas prior to invocation, categorizing capabilities into read-only, proposal, and terminal actions."*
4. *"We treat agent auditability as a first-class citizen by persisting fine-grained step telemetry, token consumption, and latency metrics to schema-isolated PostgreSQL tables."*

---

## 6. Self-Assessment Quiz (Questions & Answers)

### Questions
1. Why is an explicit loop detector necessary in an autonomous ReAct agent loop, and how does InsurAI's loop detector decide to terminate?
2. What is the fundamental difference between a `read` tool and a `terminal` tool in the `ToolCategory` enum?
3. How does Guardrail G1 protect the system against LLM hallucination in coverage decisions?
4. What happens under Guardrail G3 if an agent recommends `reject` on an insurance claim with 99% confidence?
5. Why are agent execution traces (`AgentRun` and `AgentStep`) stored in an isolated `platform` schema rather than logged only to console or text files?

---

### Hidden Answers (Reveal After Testing Yourself)
<details>
<summary>Click to reveal answers</summary>

1. **Answer:** LLMs can enter degenerate repetition loops where they issue identical tool calls indefinitely due to unhandled errors or ambiguous prompt states. InsurAI computes a SHA-256 hash of `tool_name + sorted_arguments`; if 3 consecutive identical calls occur, the loop terminates immediately with a fail-safe `needs_human_review` status.
2. **Answer:** A `read` tool is side-effect-free and provides data to the model's scratchpad for ongoing reasoning. A `terminal` tool signals the completion of the agent's objective (e.g. `submit_recommendation`), terminating the loop and handing the payload to the `GuardrailPipeline` for safety validation.
3. **Answer:** G1 extracts all clause IDs cited as evidence in the recommendation and verifies that every cited clause was actually returned by `KnowledgeService` during the active session. If the model invents a clause ID out of thin air, G1 fails and downgrades the decision to human review.
4. **Answer:** Even with 99% confidence, Guardrail G3 flags the decision and mandates human adjuster sign-off (`downgrade_to_review = True`), ensuring that adverse legal actions against policyholders cannot be executed autonomously without human oversight.
5. **Answer:** Console or file logs can be rotated, truncated, or lost. Storing structured execution traces in ACID relational tables ensures cryptographic traceability, cross-referencing with domain entities (`claims`, `policies`), and regulatory audit compliance required by insurance solvency frameworks and the EU AI Act.
</details>

---

## 7. Git Step & Limitations
- **Git Commit:** Completed Phase 5 with agent runtime, tools, ReAct loop, guardrails, evaluation harness, and unit tests.
- **Tag:** `phase-5-done`
- **Known Limitations:** In offline mode without live `LLM_API_KEY`, evaluation runs utilize the heuristic `FakeLLMClient`. Quality metrics represent pipeline plumbing rather than real foundation model accuracy.
