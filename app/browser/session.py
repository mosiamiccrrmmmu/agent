"""Browser session abstraction (Playwright-backed when available)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.tools.base import RiskLevel

logger = get_logger(__name__)


class BrowserPolicy(BaseModel):
    max_pages: int = 5
    navigation_timeout_ms: int = 30000
    allow_downloads: bool = False
    allow_uploads: bool = False
    blocked_url_patterns: list[str] = Field(
        default_factory=lambda: ["file://", "chrome://"]
    )

    def risk_for_action(self, action: str) -> RiskLevel:
        high = {"upload", "download", "submit"}
        medium = {"click", "type", "select"}
        if action in high:
            return RiskLevel.HIGH
        if action in medium:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def is_url_allowed(self, url: str) -> bool:
        lower = url.lower()
        return not any(p in lower for p in self.blocked_url_patterns)


class BrowserSession:
    """Isolated browser context. Uses Playwright if installed, else stub."""

    def __init__(self, policy: BrowserPolicy | None = None) -> None:
        self.id = str(uuid4())
        self.policy = policy or BrowserPolicy()
        self._page_count = 0
        self._history: list[str] = []
        self._playwright = None
        self._browser = None
        self._page = None

    async def start(self) -> None:
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            context = await self._browser.new_context()
            self._page = await context.new_page()
            logger.info("browser_session_started", session_id=self.id, backend="playwright")
        except Exception as exc:
            logger.warning("browser_playwright_unavailable", error=str(exc))
            self._page = None

    async def close(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._page = None

    async def navigate(self, url: str) -> dict[str, Any]:
        if not self.policy.is_url_allowed(url):
            return {"success": False, "error": "URL blocked by BrowserPolicy"}
        if self._page_count >= self.policy.max_pages:
            return {"success": False, "error": "max_pages exceeded"}
        self._page_count += 1
        self._history.append(url)
        if self._page:
            await self._page.goto(url, timeout=self.policy.navigation_timeout_ms)
            title = await self._page.title()
            return {"success": True, "url": url, "title": title, "backend": "playwright"}
        return {
            "success": True,
            "url": url,
            "title": "(stub)",
            "backend": "stub",
            "note": "Install playwright for real browser automation",
        }

    async def extract_text(self) -> dict[str, Any]:
        if self._page:
            text = await self._page.inner_text("body")
            return {"success": True, "text": text[:5000], "backend": "playwright"}
        return {
            "success": True,
            "text": "",
            "backend": "stub",
            "note": "No live page — playwright not active",
        }

    async def screenshot(self) -> dict[str, Any]:
        if self._page:
            data = await self._page.screenshot(type="png")
            import base64

            return {
                "success": True,
                "screenshot_b64": base64.b64encode(data).decode("ascii")[:100] + "...",
                "backend": "playwright",
            }
        return {"success": True, "screenshot_b64": None, "backend": "stub"}
