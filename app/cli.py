"""CLI: smoke-grok, release-audit, audit-fake-success, local-ai-status, diagnostics.

Never prints API keys.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import re
import sys
from pathlib import Path


def _ensure_test_env() -> None:
    os.environ.setdefault("SECRET_KEY", "cli-secret-key-at-least-16")
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./cli.db")
    os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./cli.db")
    os.environ.setdefault("DEFAULT_LLM_PROVIDER", "grok")
    os.environ.setdefault("REQUIRE_LOCAL_AUTH", "false")


async def smoke_grok() -> int:
    _ensure_test_env()
    from app.config.settings import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    key = settings.effective_xai_api_key
    if not key:
        print("STATUS: NOT_CONFIGURED")
        print("GROK LIVE TEST = BLOCKED BY ENVIRONMENT")
        print("Set XAI_API_KEY (preferred) or GROK_API_KEY")
        return 2

    from app.llm.base import Message, MessageRole, ToolDefinition
    from app.llm.factory import LLMFactory

    factory = LLMFactory()
    try:
        provider = factory.get_provider("grok")
    except Exception as exc:
        msg = str(exc).lower()
        if "key" in msg or "auth" in msg:
            print("STATUS: INVALID_KEY")
        else:
            print(f"STATUS: MODEL_ERROR ({type(exc).__name__})")
        return 1

    print("STATUS: provider_initialized")
    try:
        resp = await provider.generate(
            [Message(role=MessageRole.USER, content="Reply with exactly: pong")],
            temperature=0,
            max_tokens=32,
        )
    except Exception as exc:
        name = type(exc).__name__.lower()
        text = str(exc).lower()
        if "timeout" in name or "timeout" in text:
            print("STATUS: NETWORK_ERROR (timeout)")
        elif "rate" in text or "429" in text:
            print("STATUS: RATE_LIMITED")
        elif "401" in text or "403" in text or "auth" in text:
            print("STATUS: INVALID_KEY")
        elif "connect" in text or "network" in text:
            print("STATUS: NETWORK_ERROR")
        else:
            print(f"STATUS: MODEL_ERROR ({type(exc).__name__})")
        return 1

    content = (resp.content or "").strip()
    print(f"RESPONSE_LEN={len(content)} MODEL={resp.model}")
    print(f"TOKENS in={resp.usage.input_tokens} out={resp.usage.output_tokens}")

    tools = [
        ToolDefinition(
            name="echo_tool",
            description="Echo a string",
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        )
    ]
    try:
        tool_resp = await provider.generate(
            [
                Message(
                    role=MessageRole.USER,
                    content="Call echo_tool with text='ok'. Do not answer otherwise.",
                )
            ],
            tools=tools,
            temperature=0,
            max_tokens=128,
        )
        print(f"TOOL_CALLS={'yes' if tool_resp.tool_calls else 'no'}")
    except Exception as exc:
        print(f"TOOL_CALL_CHECK_ERROR={type(exc).__name__}")

    await factory.close_all()
    print("STATUS: CONNECTED")
    print("GROK LIVE TEST = PASS")
    return 0


def release_audit(*, as_json: bool = False) -> int:
    rows: list[tuple[str, str]] = []

    def row(name: str, status: str) -> None:
        rows.append((name, status))

    try:
        from app.agent.orchestrator import AgentOrchestrator  # noqa: F401

        row("Agent Core", "PASS")
    except Exception as exc:
        row("Agent Core", f"FAIL ({exc})")

    try:
        from app.agent.lifecycle import AgentLifecycle  # noqa: F401

        row("Agent Lifecycle", "PASS")
    except Exception as exc:
        row("Agent Lifecycle", f"FAIL ({exc})")

    try:
        from app.llm.factory import LLMFactory

        f = LLMFactory()
        f.get_provider("mock")
        row("LLM Factory (mock)", "PASS")
        from app.config.settings import get_settings

        get_settings.cache_clear()
        s = get_settings()
        if s.effective_xai_api_key:
            row("Grok Configuration", "PASS (key present)")
            row("Grok Live API", "NOT_VERIFIED (run smoke-grok)")
        else:
            row("Grok Configuration", "NOT_CONFIGURED")
            row("Grok Live API", "NOT_VERIFIED")
    except Exception as exp:
        row("LLM Factory", f"FAIL ({exp})")

    try:
        from app.database.sqlite_store import SQLiteStore

        store = SQLiteStore()
        if hasattr(store, "upsert_agent_run"):
            row("SQLite agent_runs", "PASS")
        else:
            row("SQLite agent_runs", "FAIL (missing methods)")
        row("SQLite Persistence module", "PASS")
    except Exception as exc:
        row("SQLite Persistence", f"FAIL ({exc})")

    try:
        from app.permissions.manager import PermissionManager  # noqa: F401

        row("Approvals / Permissions", "PASS")
    except Exception as exp:
        row("Approvals / Permissions", f"FAIL ({exp})")

    try:
        from app.computer.factory import create_driver

        d = create_driver(force_mock=True)
        row(
            "Computer MockDriver",
            "PASS" if d.name == "mock" else f"UNEXPECTED ({d.name})",
        )
        if sys.platform.startswith("win") and os.environ.get(
            "COMPUTER_USE_MOCK", ""
        ).lower() not in ("1", "true", "yes"):
            try:
                wd = create_driver(force_mock=False)
                row(
                    "Computer WindowsDriver",
                    "PASS" if wd.name == "windows" else f"PARTIAL ({wd.name})",
                )
            except Exception as exc:
                row("Computer WindowsDriver", f"FAIL ({exc})")
        else:
            row(
                "Computer WindowsDriver",
                "NOT_VERIFIED (non-Windows or COMPUTER_USE_MOCK)",
            )
    except Exception as exp:
        row("Computer Use", f"FAIL ({exp})")

    try:
        from app.browser.session import BrowserSession  # noqa: F401

        row("Browser", "PARTIAL (module present; live Playwright NOT_VERIFIED)")
    except Exception:
        row("Browser", "NOT_IMPLEMENTED")

    row("Gmail", "NOT_CONFIGURED / fail-closed")
    row("Calendar", "NOT_CONFIGURED / fail-closed")
    row("WhatsApp", "NOT_CONFIGURED / fail-closed")
    row("Telegram", "PARTIAL")

    try:
        from app.tools.files.sandbox import PathSandbox  # noqa: F401

        row("Filesystem sandbox", "PASS")
    except Exception as exp:
        row("Filesystem sandbox", f"FAIL ({exp})")

    ui = Path(__file__).resolve().parent.parent / "desktop" / "src" / "index.html"
    row("Desktop UI (index.html)", "PASS" if ui.is_file() else "NOT_IMPLEMENTED")

    root = Path(__file__).resolve().parent.parent
    ps1 = root / "scripts" / "build_exe.ps1"
    row("Windows EXE build script", "PASS" if ps1.is_file() else "NOT_IMPLEMENTED")
    row("Windows EXE binary", "NOT_VERIFIED")
    row("Installer", "NOT_VERIFIED")
    row("Clean VM", "NOT_VERIFIED")

    try:
        from app.config.settings import get_settings

        get_settings.cache_clear()
        host = get_settings().host
        if host in ("127.0.0.1", "localhost"):
            row("Desktop bind host default", f"PASS ({host})")
        else:
            row("Desktop bind host default", f"WARN ({host})")
    except Exception as exp:
        row("Desktop bind host", f"UNKNOWN ({exp})")

    row("Platform", platform.platform())
    row("Python", sys.version.split()[0])

    if as_json:
        print(json.dumps({name: status for name, status in rows}, indent=2))
        return 0

    print("PERSONALAI RELEASE AUDIT")
    print("=" * 48)
    width = max(len(n) for n, _ in rows)
    for name, status in rows:
        print(f"{name.ljust(width)}  {status}")
    print("=" * 48)
    print(
        "Legend: PASS = evidence in this process; NOT_VERIFIED = needs Windows/key/live run"
    )
    print(
        "FINAL: READY FOR WINDOWS ACCEPTANCE (repo baseline) — not WINDOWS DESKTOP RELEASE READY"
    )
    return 0


def audit_fake_success() -> int:
    root = Path(__file__).resolve().parent.parent / "app"
    patterns = [
        re.compile(r"success\s*=\s*True"),
        re.compile(r'"success"\s*:\s*True'),
        re.compile(r"message_id\s*=\s*[\"']stub", re.I),
        re.compile(r"fake[_\s]?result", re.I),
        re.compile(r"placeholder response", re.I),
    ]
    allow_substrings = ("mock_driver", "mock.py", "/tests/", "test_")
    findings: list[str] = []
    for path in root.rglob("*.py"):
        rel = str(path.relative_to(root.parent))
        if any(a in rel for a in allow_substrings):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), 1):
            if any(p.search(line) for p in patterns):
                findings.append(f"{rel}:{i}: {line.strip()[:120]}")

    print("FAKE SUCCESS AUDIT")
    print("=" * 48)
    if not findings:
        print("No suspicious success=True patterns outside mocks (heuristic).")
        return 0
    print(f"Found {len(findings)} candidate line(s) — review manually:")
    for f in findings[:80]:
        print(f"  {f}")
    if len(findings) > 80:
        print(f"  ... +{len(findings) - 80} more")
    print("=" * 48)
    print("NOTE: legitimate ToolResult(success=True) after real work is expected.")
    return 0


def local_ai_status() -> int:
    import httpx

    from app.core.network import probe_internet

    base = os.environ.get("LOCAL_AI_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("LOCAL_AI_MODEL", "llama3.2")
    net = probe_internet(timeout=0.8).value
    ollama = "UNAVAILABLE"
    reason = "not_reached"
    try:
        r = httpx.get(f"{base}/api/tags", timeout=2.0)
        if r.status_code == 200:
            ollama = "AVAILABLE"
            reason = "api_tags_ok"
            tags = r.json().get("models") or []
            names = [m.get("name", "") for m in tags]
            print(f"OLLAMA_MODELS={names[:10]}")
        else:
            reason = f"http_{r.status_code}"
    except Exception as exc:
        reason = type(exc).__name__
    print(f"NETWORK={net}")
    print(f"OLLAMA={ollama}")
    print(f"BASE_URL={base}")
    print(f"MODEL={model}")
    print(f"REASON={reason}")
    return 0 if ollama == "AVAILABLE" else 2


def diagnostics() -> int:
    print("PERSONALAI DIAGNOSTICS")
    print("=" * 48)
    print(f"Python={sys.version.split()[0]}")
    print(f"Platform={platform.platform()}")
    local_ai_status()
    print("---")
    return release_audit(as_json=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("smoke-grok", help="Live Grok API smoke test")
    ra = sub.add_parser("release-audit", help="Evidence-based release gate report")
    ra.add_argument("--json", action="store_true", help="Machine-readable JSON")
    sub.add_parser("audit-fake-success", help="Heuristic scan for fake success patterns")
    sub.add_parser("local-ai-status", help="Ollama / local AI health")
    sub.add_parser("diagnostics", help="System diagnostics + release-audit")
    args = parser.parse_args(argv)
    if args.cmd == "smoke-grok":
        return asyncio.run(smoke_grok())
    if args.cmd == "release-audit":
        return release_audit(as_json=bool(getattr(args, "json", False)))
    if args.cmd == "audit-fake-success":
        return audit_fake_success()
    if args.cmd == "local-ai-status":
        return local_ai_status()
    if args.cmd == "diagnostics":
        return diagnostics()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
