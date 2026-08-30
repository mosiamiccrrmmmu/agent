# Personal AI

**Windows Desktop Application** + Agent Core

A Personal AI assistant: local FastAPI backend, pywebview desktop shell, secure credential storage, and provider-agnostic Agent architecture with **Grok (xAI) as the primary LLM**.

---

## Status matrix (honest)

| Area | Status |
|------|--------|
| Agent Core (orchestrator, tools, permissions) | **VERIFIED** (unit/e2e with Mock) |
| Grok provider class + factory wiring | **VERIFIED** (unit, no live key) |
| Grok **real API** | **NOT VERIFIED** in CI (requires `XAI_API_KEY`) |
| OpenAI / Anthropic providers | **IMPLEMENTED** — live **NOT VERIFIED** |
| Tool validation | **VERIFIED** |
| Permission + approval binding / replay protection | **VERIFIED** (unit) |
| Approval **persistence across restart** | **PARTIAL** (in-process; SQLite persistence planned) |
| Memory (short/long) | **PARTIAL** (in-process; restart loses data) |
| LocalAuth on API | **VERIFIED** (code path; tests disable auth) |
| Desktop UI (minimal) | **PARTIAL** (static first-run + chat shell) |
| Tauri 2 | **NOT IMPLEMENTED** (pywebview is the desktop shell) |
| Gmail / Calendar | **NOT IMPLEMENTED** (fail closed) |
| WhatsApp | **NOT IMPLEMENTED** (fail closed) |
| Telegram | **PARTIAL** |
| Browser | **PARTIAL** |
| Computer Use | **SIMULATOR only** — not real OS control |
| Windows EXE / Installer / Clean VM | **NOT VERIFIED** |
| Code signing | **NOT IMPLEMENTED** |
| Auto-update | **NOT IMPLEMENTED** |

---

## Architecture

```
Desktop UI (pywebview → desktop/src)
        → Local FastAPI (127.0.0.1)
        → Agent Orchestrator → LLM (Grok / OpenAI / Anthropic / Mock)
                            → Tools / Permissions / Memory
```

---

## Quick start (development)

```bash
cp .env.example .env
# Set XAI_API_KEY for Grok, or DEFAULT_LLM_PROVIDER=mock
pip install -e ".[dev]" pywebview
export REQUIRE_LOCAL_AUTH=false   # optional for local curl tests
python run_personal_ai.py
```

```bash
curl http://127.0.0.1:8765/api/v1/health
curl http://127.0.0.1:8765/api/v1/desktop/setup/status
```

---

## Grok setup

1. Create an API key at xAI.
2. Prefer env `XAI_API_KEY` (alias `GROK_API_KEY` accepted).
3. Or use the Setup screen in the desktop UI — key is stored via keyring when available.
4. `DEFAULT_LLM_PROVIDER=grok`

Supported factory providers: `grok`, `openai`, `anthropic`, `mock`.

---

## Tests

```bash
export SECRET_KEY=test-secret-key-at-least-16-chars
export DATABASE_URL=sqlite+aiosqlite:///./test.db
export DATABASE_URL_SYNC=sqlite:///./test.db
export DEFAULT_LLM_PROVIDER=mock
export REQUIRE_LOCAL_AUTH=false
pytest -q
ruff check app tests
```

---

## Windows EXE (developer)

On Windows with Python 3.11+:

```powershell
.\scripts\build_exe.ps1
```

Output: `dist\PersonalAI.exe`. **Clean-machine and installer verification are still required before calling a release READY.**

---

## License

MIT
