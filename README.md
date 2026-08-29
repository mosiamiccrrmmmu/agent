# Personal AI

**Windows Desktop Application** + Agent Core (Phase 1 & 2)

A professional Personal AI assistant: installable on Windows, with a modern desktop UI, system tray, secure credential storage, and the full Agent architecture underneath.

---

## Phase Status

| Phase | Status |
|-------|--------|
| Phase 1 — Agent Core, LLM, Tools, Permissions, Memory | Complete |
| Phase 2 — Integrations | Complete (OAuth live needs credentials) |
| Final — Windows Desktop Productization | Architecture + UI + lifecycle + build scripts shipped; Windows EXE requires a Windows build agent |

---

## Product experience

```
Download PersonalAI.exe
        → Launch Personal AI
        → First-run: Claude / OpenAI / Mock + API key
        → Chat · Tasks · Memory · Approvals · Integrations · Activity · Settings
```

---

## Architecture

```
Desktop UI (pywebview / Tauri)
        → Local FastAPI backend (127.0.0.1)
        → Agent Orchestrator → LLM / Memory / Tools / Permissions
```

Details: [docs/desktop-architecture.md](docs/desktop-architecture.md)

---

## Quick start (development)

```bash
cp .env.example .env
pip install -e ".[dev]" pywebview
python run_personal_ai.py
# or: ./scripts/run_backend_desktop.sh
```

```bash
curl http://127.0.0.1:8765/api/v1/health
curl http://127.0.0.1:8765/api/v1/desktop/setup/status
```

---

## Windows EXE build

On a Windows PC with Python 3.11+:

```powershell
.\scripts\build_exe.ps1
```

Output: `dist\PersonalAI.exe` — double-click to open. No Python required for end users.

See [docs/windows-build.md](docs/windows-build.md).

---

## Tests

```bash
export SECRET_KEY=test-secret-key-at-least-16-chars
export DATABASE_URL=sqlite+aiosqlite:///./test.db
export DATABASE_URL_SYNC=sqlite:///./test.db
export DEFAULT_LLM_PROVIDER=mock
pytest -q
```

---

## License

MIT
