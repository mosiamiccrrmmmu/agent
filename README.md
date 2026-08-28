# Personal AI Agent

**My Personal AI Operating System**

A production-oriented Personal AI Agent with Tools, Memory, Permissions, Human-in-the-Loop Approvals, and multi-provider LLM abstraction.

> This is **not** a simple chatbot. It is an Agent Runtime.

---

## Phase 1 Status — COMPLETE

| Component | Status |
|-----------|--------|
| Repository structure | ✅ |
| FastAPI application | ✅ |
| PostgreSQL + pgvector (Docker) | ✅ |
| Agent Orchestrator | ✅ |
| LLM abstraction (Claude / OpenAI / Mock) | ✅ |
| Tool Registry + Pydantic validation | ✅ |
| Permission + Approval system | ✅ |
| Memory (Short / Long / Profile) | ✅ |
| API endpoints | ✅ |
| Tests (unit + E2E with Mock) | ✅ 25 passed |
| Docker + Healthchecks | ✅ |
| Security baseline | ✅ |
| Documentation | ✅ |

---

## Quick Start

```bash
git clone https://github.com/mosiamiccrrmmmu/agent.git
cd agent
cp .env.example .env
# Set SECRET_KEY; for tests without API keys use DEFAULT_LLM_PROVIDER=mock

docker compose up --build
# API: http://localhost:8000
```

```bash
curl http://localhost:8000/api/v1/health
curl -X POST http://localhost:8000/api/v1/chat -H 'Content-Type: application/json' -d '{"message":"hello"}'
```

## Tests

```bash
pip install -e ".[dev]"
pytest -v   # 25 passed (Mock LLM)
ruff check app tests
```

## Security

- Secrets only in env / .env (never committed)
- HIGH/CRITICAL tools require approval
- Agent max_steps + timeout
- Session-isolated short-term memory
- Strict Pydantic validation on all tool arguments

## License

MIT
