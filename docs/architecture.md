# Architecture

```
User → Desktop UI (pywebview + desktop/src)
     → Local FastAPI (127.0.0.1)
     → Agent Orchestrator
     → LLM (Grok primary | OpenAI | Anthropic | Mock)
     → Tool Registry → Permission → Approval → Execution
     → SQLite (memory, approvals, tasks)
     → ComputerController → MockDriver | WindowsDriver
```

Security is enforced in code, not by the LLM.
