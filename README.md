# Personal AI Agent

**My Personal AI Operating System** — Phase 2

A production-oriented Personal AI Agent with real-world integrations, permissions, and human-in-the-loop approvals.

---

## Phase Status

| Phase | Status |
|-------|--------|
| Phase 1 — Core Agent, LLM, Tools, Permissions, Memory | ✅ Complete |
| Phase 2 — Integrations (Telegram, Gmail, Calendar, Browser, Computer, WhatsApp, Scheduler) | ✅ Scaffolding + tools + API (OAuth live flows require user credentials) |

---

## Architecture (Phase 2)

```
USER → Telegram / API
         ↓
   Agent Orchestrator
         ↓
   LLM | Memory | Tools
         ↓
   Permission + Approval
         ↓
   Gmail / Calendar / WhatsApp / Browser / Computer / Scheduler
```

---

## Quick Start

```bash
cp .env.example .env
# SECRET_KEY + optional TELEGRAM_BOT_TOKEN / Google OAuth / etc.
# DEFAULT_LLM_PROVIDER=mock  # for local tests without LLM keys

pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/integrations
curl http://localhost:8000/api/v1/tools
```

Docker:

```bash
docker compose up --build
```

---

## Phase 2 Capabilities

| Integration | Status | Notes |
|-------------|--------|-------|
| Telegram interface | ✅ | Commands + NL → agent; webhook endpoint |
| Gmail tools | ✅ interface | OAuth required for live mail; `send_email` = HIGH risk |
| Google Calendar | ✅ interface | OAuth required; create event supports approval path |
| Browser (Playwright) | ✅ | Isolated session; navigate + extract |
| Computer Use | ✅ | Policy-gated actions; HIGH needs approval |
| WhatsApp | ✅ abstraction | Business API vs Web documented; send = HIGH risk |
| Scheduler | ✅ | one_time / daily / interval |
| Notifications | ✅ base | Telegram provider ready |
| Voice | ✅ foundation | STT/TTS pipeline stub |
| Workflows | ✅ foundation | Morning briefing template |
| Run history + cost limits | ✅ | `/runs`, `/runs/cost` |
| Integration health | ✅ | `/integrations` |

### WhatsApp honesty

- **WhatsApp Business API** — official path when token configured.
- **WhatsApp Web automation** — not an official API; high ban/ToS risk; implemented only as explicit provider class with documentation, not as a silent default.

---

## Tests

```bash
export SECRET_KEY=test-secret-key-at-least-16-chars
export DATABASE_URL=postgresql+asyncpg://agent:agent@localhost:5432/test
export DATABASE_URL_SYNC=postgresql://agent:agent@localhost:5432/test
export DEFAULT_LLM_PROVIDER=mock
pytest -v
# 34 tests including Phase 2 policy, telegram, health, scheduler
```

---

## Security

- Secrets via env only
- OAuth tokens in encrypted credential store (never to LLM)
- HIGH/CRITICAL tools require approval
- Computer policy blocks dangerous hotkeys
- Cost daily/monthly limits

---

## License

MIT
