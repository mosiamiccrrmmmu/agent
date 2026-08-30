"""CLI helpers for development and smoke tests.

Usage:
  python -m app.cli smoke-grok

Requires XAI_API_KEY (or GROK_API_KEY) in the environment.
Never prints the API key.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys


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
        print("GROK LIVE TEST = BLOCKED BY ENVIRONMENT")
        print("Set XAI_API_KEY (preferred) or GROK_API_KEY and re-run:")
        print("  python -m app.cli smoke-grok")
        return 2

    from app.llm.base import Message, MessageRole, ToolDefinition
    from app.llm.factory import LLMFactory

    factory = LLMFactory()
    try:
        provider = factory.get_provider("grok")
    except Exception as exc:
        print(f"GROK LIVE TEST = FAIL (provider init): {type(exc).__name__}")
        return 1

    print("1) Connection: provider initialized (key present, not displayed)")
    try:
        resp = await provider.generate(
            [Message(role=MessageRole.USER, content="Reply with exactly: pong")],
            temperature=0,
            max_tokens=32,
        )
    except Exception as exc:
        print(f"GROK LIVE TEST = FAIL (generate): {type(exc).__name__}: {exc}")
        return 1

    content = (resp.content or "").strip()
    print(f"2) Model response received (len={len(content)}, model={resp.model})")
    print(f"3) Token usage: in={resp.usage.input_tokens} out={resp.usage.output_tokens}")

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
        has_tools = bool(tool_resp.tool_calls)
        print(f"4) Tool-call capability: {'yes' if has_tools else 'no (model may omit tools)'}")
    except Exception as exc:
        print(f"4) Tool-call check error: {type(exc).__name__}")

    await factory.close_all()
    print("GROK LIVE TEST = PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("smoke-grok", help="Live Grok API smoke test (requires XAI_API_KEY)")
    args = parser.parse_args(argv)
    if args.cmd == "smoke-grok":
        return asyncio.run(smoke_grok())
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
