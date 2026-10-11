# Gotchas, Workarounds, and Environment Quirks

## 1. Environment Discovery (2026-10-12)

- **Operating System:** Windows (PowerShell shell).
- **Git:** `git version 2.45.1.windows.1`.
- **Python:** `Python 3.13.7` (64-bit).
- **Package Manager (`uv`):** `uv 0.13.0` installed via `python -m pip install --user uv`. Can be invoked via `python -m uv`.
- **Node & NPM:** `node v20.17.0`, `npm 10.8.2`.
- **Docker:** `Docker version 29.1.3`, `Docker Compose v2.40.3-desktop.1`.
  - **Status:** Docker Desktop daemon is currently **not running** (`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`).
  - **Fallback:** Container files (`Dockerfile`, `docker-compose.yml`) are written. Unit tests and mocked tests run without external database. Integration tests requiring PostgreSQL/pgvector use `@pytest.mark.integration` and skip cleanly when no DB is available.

## 2. LLM Gateway & Offline Mode

- **LLM Status:** `LLM_API_KEY` is not provided (offline mode).
- **Implementation:** `LLMClient` protocol implemented with `FakeLLMClient` and `RecordReplayLLMClient`.
- **Gemini Client:** Google GenAI / Gemini client implementation written behind the interface. Marked: `UNVERIFIED AGAINST LIVE API` until live key is supplied.
- **Evaluation:** Offline eval reports marked `plumbing only, fake LLM, not a quality measurement`.

## 3. Windows Shell & Line Endings

- Git `.gitattributes` configured with `* text=auto` and `*.sh text eol=lf` to prevent CRLF line ending corruptions in bash and docker scripts.
- PowerShell command timeouts and non-interactive parameters (`--yes`, `-y`) enforced.
