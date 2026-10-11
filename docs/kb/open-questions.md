# Open Questions

## ASSUMED (learner may overrule)

1. **Reconstruction of Missing Plan Parts:**
   - **Observation:** `implementation_plan\parts` originally contained `assemble.sh`, `sec0_header.md`, `sec2_working_rules.md`, `sec5_phases.md`, `sec6_appendices.md`, and `sec7_appendix_G_claims_reference.md`. Missing parts were `partA.md`, `partB.md`, `partC.md`, `sec1.md`, and `sec3_4.md`.
   - **Resolution:** As per Section 2 Bootstrap instructions, these missing parts were reconstructed accurately and fully from the explicit requirements, section mappings (Sections 1, 3.3, 3.7.3, 3.8, 3.10, 3.12, 3.13, 3.17, Section 4 traceability, Processes P01–P13, Agents A1–A8, Guardrails G1–G10), and Appendix G.
   - **Action for Learner:** Review the assembled `docs/ARCHITECTURE_AND_PROCESSES.md` and `docs/MASTER_PLAN.md` if any business wording or parameters should be adjusted.

2. **Offline Mode with Fake & Replay LLM:**
   - **Assumption:** No `LLM_API_KEY` is present. System runs in offline mode using `FakeLLMClient` and `RecordReplayLLMClient`. Gemini live client is implemented and ready behind `LLMClient` interface.
   - **Action for Learner:** To evaluate against Gemini live API, add `LLM_API_KEY` to `.env` and execute the evaluation command provided in `PROGRESS.md`.

3. **Docker Daemon Status:**
   - **Assumption:** Docker Desktop daemon is stopped on the host. Integration tests requiring live PostgreSQL/pgvector will skip cleanly with `@pytest.mark.integration` when connection fails, while all domain logic, engines, guardrails, and unit tests run against in-memory/mocked components.
   - **Action for Learner:** Start Docker Desktop in the morning and run `docker compose up -d` to verify full multi-container stack.
