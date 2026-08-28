from __future__ import annotations

"""Personal AI Agent — FastAPI application entry point."""

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(log_level=settings.log_level, json_logs=settings.is_production)
    logger = get_logger("app")

    tool_registry.register(WebSearchTool())
    tool_registry.register(RememberTool())
    tool_registry.register(RecallTool())

    logger.info(
        "app_started",
        env=settings.app_env,
        tools=len(tool_registry.list_tools()),
    )
    yield

    await llm_factory.close_all()
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Production-ready Personal AI Agent",
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
