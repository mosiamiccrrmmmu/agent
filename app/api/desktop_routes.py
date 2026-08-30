from __future__ import annotations

"""Desktop-specific API routes: setup, secrets status, local diagnostics."""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.logging import get_logger
from app.desktop.auth import local_auth
from app.desktop.paths import get_app_paths
from app.desktop.secrets import SecureSecretStore

logger = get_logger(__name__)
router = APIRouter(prefix="/desktop", tags=["desktop"])

_store = SecureSecretStore()


def _optional_auth(
    x_personal_ai_token: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    if not settings.require_local_auth:
        return
    existing = _store.get(local_auth.TOKEN_NAME)
    if existing is None:
        return
    if not local_auth.validate(x_personal_ai_token):
        raise HTTPException(status_code=401, detail="Invalid or missing local API token")


class ProviderConfigRequest(BaseModel):
    provider: str = Field(..., description="grok | openai | anthropic | mock")
    api_key: str | None = None
    model: str | None = None


class TestConnectionRequest(BaseModel):
    provider: str = "grok"
    api_key: str | None = None


@router.get("/setup/status")
async def setup_status() -> dict[str, Any]:
    settings = get_settings()
    paths = get_app_paths()
    has_grok = bool(_store.get("xai_api_key") or settings.effective_xai_api_key)
    has_openai = bool(_store.get("openai_api_key") or settings.openai_api_key)
    has_anthropic = bool(_store.get("anthropic_api_key") or settings.anthropic_api_key)
    token_ready = _store.has(local_auth.TOKEN_NAME)

    configured = (
        has_grok
        or has_openai
        or has_anthropic
        or settings.default_llm_provider == "mock"
    )
    return {
        "version": settings.app_version,
        "desktop": settings.is_desktop,
        "first_run_complete": configured and token_ready,
        "providers": {
            "grok": "connected" if has_grok else "not_configured",
            "openai": "connected" if has_openai else "not_configured",
            "anthropic": "connected" if has_anthropic else "not_configured",
            "mock": "available",
        },
        "default_provider": settings.default_llm_provider,
        "data_root": str(paths.root),
        "secret_backend": _store.backend_name(),
        "local_auth_ready": token_ready,
    }


@router.post("/setup/provider")
async def setup_provider(req: ProviderConfigRequest) -> dict[str, Any]:
    provider = req.provider.lower().strip()
    if provider not in ("grok", "openai", "anthropic", "mock"):
        raise HTTPException(400, f"Unsupported provider: {provider}")

    if provider == "mock":
        token = local_auth.ensure_token()
        return {
            "status": "ok",
            "provider": "mock",
            "message": "Mock provider selected (no API key required)",
            "local_token_issued": True,
            "local_api_token": token,
        }

    if not req.api_key or not req.api_key.strip():
        raise HTTPException(400, "api_key is required for this provider")

    key_name = {
        "grok": "xai_api_key",
        "openai": "openai_api_key",
        "anthropic": "anthropic_api_key",
    }[provider]
    _store.set(key_name, req.api_key.strip())
    token = local_auth.ensure_token()
    logger.info("provider_configured", provider=provider)
    return {
        "status": "ok",
        "provider": provider,
        "message": f"{provider} API key stored securely",
        "secret_backend": _store.backend_name(),
        "local_token_issued": True,
        "local_api_token": token,
    }


@router.post("/setup/test-connection")
async def test_connection(req: TestConnectionRequest) -> dict[str, Any]:
    provider = req.provider.lower().strip()
    api_key = req.api_key

    if provider == "mock":
        return {
            "status": "ok",
            "provider": "mock",
            "message": "Mock provider always available",
        }

    if not api_key:
        key_name = {
            "grok": "xai_api_key",
            "openai": "openai_api_key",
            "anthropic": "anthropic_api_key",
        }.get(provider)
        if key_name:
            api_key = _store.get(key_name)

    if not api_key:
        return {
            "status": "not_configured",
            "provider": provider,
            "message": "No API key available for this provider",
        }

    if len(api_key.strip()) < 8:
        return {
            "status": "error",
            "provider": provider,
            "message": "API key appears invalid (too short)",
        }

    return {
        "status": "ok",
        "provider": provider,
        "message": "API key accepted (live verification requires network and is optional)",
        "live_verified": False,
    }


@router.get("/diagnostics")
async def diagnostics(_: None = Depends(_optional_auth)) -> dict[str, Any]:
    settings = get_settings()
    paths = get_app_paths()
    return {
        "version": settings.app_version,
        "env": settings.app_env,
        "desktop": settings.is_desktop,
        "host": settings.host,
        "port": settings.port,
        "default_provider": settings.default_llm_provider,
        "data_root": str(paths.root),
        "secret_backend": _store.backend_name(),
    }


@router.post("/stop-all")
async def stop_all(_: None = Depends(_optional_auth)) -> dict[str, str]:
    """Emergency stop: agent cancel + computer use + block new work."""
    from app.agent.cancel import request_agent_cancel
    from app.computer.controller import trigger_emergency_stop
    from app.core.execution_gate import block_all

    request_agent_cancel()
    trigger_emergency_stop()
    block_all()
    return {"status": "stopped"}


@router.post("/reset-stop")
async def reset_stop(_: None = Depends(_optional_auth)) -> dict[str, str]:
    """Clear global stop gate so new executions can start."""
    from app.agent.cancel import clear_agent_cancel
    from app.computer.controller import clear_emergency_stop
    from app.core.execution_gate import reset_gate

    clear_agent_cancel()
    clear_emergency_stop()
    reset_gate()
    return {"status": "ready"}
