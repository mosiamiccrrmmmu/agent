from __future__ import annotations

"""Personal AI - FastAPI application entry point (Desktop + Agent Core)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.desktop_routes import router as desktop_router
from app.api.routes import router
from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.desktop.lifecycle import lifecycle
from app.desktop.paths import get_app_paths
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
        from app.tools.apps_tools import LaunchAppTool, ListAppsTool

        tool_registry.register(ListAppsTool())
        tool_registry.register(LaunchAppTool())
    except Exception as exc:  # noqa: BLE001
        logger.warning("app_tools_skip", error=str(exc))

    try:
        from app.tools.files.tools import DeleteFileTool, ListFilesTool, ReadFileTool, WriteFileTool

        tool_registry.register(ListFilesTool())
        tool_registry.register(ReadFileTool())
        tool_registry.register(WriteFileTool())
        tool_registry.register(DeleteFileTool())
    except Exception as exc:  # noqa: BLE001
        logger.warning("file_tools_skip", error=str(exc))

    try:
        from app.tools.computer.tools import ComputerActTool, ComputerEmergencyStopTool

        tool_registry.register(ComputerActTool())
        tool_registry.register(ComputerEmergencyStopTool())
    except Exception as exc:  # noqa: BLE001
        logger.warning("computer_tools_skip", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    paths = get_app_paths()
    setup_logging(log_level=settings.log_level, json_logs=settings.is_production)
    logger = get_logger("app")

    lifecycle.mark_starting()
    _register_all_tools()
    try:
        from app.agent.execution_hooks import install_execution_hooks

        install_execution_hooks()
    except Exception as exc:  # noqa: BLE001
        logger.warning("execution_hooks_skip", error=str(exc))
    lifecycle.mark_ready(database_ok=True)

    logger.info(
        "app_started",
        env=settings.app_env,
        tools=len(tool_registry.list_tools()),
        phase=2,
        version=settings.app_version,
        desktop=settings.is_desktop,
        data_root=str(paths.root),
    )
    yield

    lifecycle.mark_stopping()
    await llm_factory.close_all()
    lifecycle.mark_stopped()
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Personal AI - Desktop + Agent Core",
        lifespan=lifespan,
    )
    if settings.debug:
        origins = ["*"]
    else:
        origins = [
            "http://localhost",
            "http://127.0.0.1",
            "tauri://localhost",
            "https://tauri.localhost",
        ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    api_prefix = "/api/v1"
    app.include_router(router, prefix=api_prefix)
    app.include_router(desktop_router, prefix=api_prefix)

    ui_dir = Path(__file__).resolve().parents[1] / "desktop" / "src"
    if not ui_dir.exists():
        import sys

        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            ui_dir = Path(sys._MEIPASS) / "desktop" / "src"
    if ui_dir.exists():
        index = ui_dir / "index.html"

        @app.get("/")
        async def ui_index() -> FileResponse:
            return FileResponse(index)

        app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")

    return app


app = create_app()
