# Personal AI Agent

**My Personal AI Operating System** — Phase 2

A production-oriented Personal AI Agent with real-world integrations, permissions, and human-in-the-loop approvals.

## Phase Status

| Phase | Status |
|-------|--------|
| Phase 1 — Core Agent, LLM, Tools, Permissions, Memory | Complete |
| Phase 2 — Integrations (Telegram, Gmail, Calendar, Browser, Computer, WhatsApp, Scheduler) | Scaffolding + tools + API |

## Quick Start

```bash
cp .env.example .env
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/integrations
curl http://localhost:8000/api/v1/tools
```

## Phase 2 Capabilities

- Telegram interface (commands + NL, webhook)
- Gmail / Calendar tools (OAuth for live data; send = HIGH risk)
- Browser (Playwright) navigate + extract
- Computer Use with ComputerPolicy (HIGH needs approval)
- WhatsApp provider abstraction (Business vs Web documented)
- Scheduler (one_time / daily / interval)
- Run history + cost limits
- Integration health at `/integrations`

WhatsApp Web automation is **not** an official API and is not the default.

## Tests

```bash
pytest -v
```

## License

MIT
