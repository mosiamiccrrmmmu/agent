from __future__ import annotations

"""Personal AI Agent — FastAPI application entry point (Phase 2)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.llm.factory import llm_factory
from app.tools.memory_tools import RecallTool, RememberTool
from app.tools.registry import tool_registry
from app.tools.web.search import WebSearchTool


def _register_all_tools() -> None:
    logger = get_logger("app")

    tool_registry.register(WebSearchTool())
    tool_registry.register(RememberTool())
    tool_registry.register(RecallTool())

    try:
        from app.tools.gmail.tools import ListEmailsTool, SendEmailTool

        tool_registry.register(ListEmailsTool())
        tool_registry.register(SendEmailTool())
    except Exception as exc:  # noqa: BLE001
        logger.warning("gmail_tools_skip", error=str(exc))

    try:
        from app.tools.calendar.tools import CreateEventTool, FindFreeTimeTool

        tool_registry.register(FindFreeTimeTool())
        tool_registry.register(CreateEventTool())
    except Exception as exc:  # noqa: BLE001
        logger.warning("calendar_tools_skip", error=str(exc))

    try:
        from app.tools.whatsapp.tools import SendWhatsAppTool

        tool_registry.register(SendWhatsAppTool())
    except Exception as exc:  # noqa: BLE001
        logger.warning("whatsapp_tools_skip", error=str(exc))

    try:
        from app.tools.browser.tools import ExtractTextTool, NavigateTool

        tool_registry.register(NavigateTool())
        tool_registry.register(ExtractTextTool())
    except Exception as exc:  # noqa: BLE001
        logger.warning("browser_tools_skip", error=str(exc))

    try:
        from app.tools.computer.tools import ComputerActTool

        tool_registry.register(ComputerActTool())
    except Exception as exc:  # noqa: BLE001
        logger.warning("computer_tools_skip", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(log_level=settings.log_level, json_logs=settings.is_production)
    logger = get_logger("app")

    _register_all_tools()

    logger.info(
        "app_started",
        env=settings.app_env,
        tools=len(tool_registry.list_tools()),
        phase=2,
    )
    yield

    await llm_factory.close_all()
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        description="Personal AI Agent — Phase 2 integrations",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api/v1")
    return app


app = create_app()
