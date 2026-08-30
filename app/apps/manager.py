"""Allowlisted application launcher — no arbitrary executables."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from typing import Any

from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppEntry(BaseModel):
    id: str
    name: str
    windows_candidates: list[str] = Field(default_factory=list)
    linux_candidates: list[str] = Field(default_factory=list)


DEFAULT_ALLOWLIST: list[AppEntry] = [
    AppEntry(
        id="notepad",
        name="Notepad",
        windows_candidates=["notepad.exe"],
        linux_candidates=["gedit", "nano", "cat"],
    ),
    AppEntry(
        id="calculator",
        name="Calculator",
        windows_candidates=["calc.exe"],
        linux_candidates=["gnome-calculator", "bc"],
    ),
    AppEntry(
        id="explorer",
        name="File Explorer",
        windows_candidates=["explorer.exe"],
        linux_candidates=["xdg-open"],
    ),
    AppEntry(
        id="chrome",
        name="Google Chrome",
        windows_candidates=[
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "chrome.exe",
        ],
        linux_candidates=["google-chrome", "chromium", "chromium-browser"],
    ),
    AppEntry(
        id="edge",
        name="Microsoft Edge",
        windows_candidates=[
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "msedge.exe",
        ],
        linux_candidates=["microsoft-edge", "msedge"],
    ),
]


class ApplicationManager:
    def __init__(self, allowlist: list[AppEntry] | None = None) -> None:
        self.allowlist = {a.id: a for a in (allowlist or DEFAULT_ALLOWLIST)}
        self._launched: list[dict[str, Any]] = []

    def list_apps(self) -> list[dict[str, str]]:
        return [{"id": a.id, "name": a.name} for a in self.allowlist.values()]

    def resolve_path(self, app_id: str) -> str | None:
        entry = self.allowlist.get(app_id)
        if not entry:
            return None
        candidates = (
            entry.windows_candidates
            if sys.platform.startswith("win")
            else entry.linux_candidates
        )
        for c in candidates:
            if os.path.isfile(c):
                return c
            found = shutil.which(c)
            if found:
                return found
        return None

    def launch(self, app_id: str, args: list[str] | None = None) -> dict[str, Any]:
        if app_id not in self.allowlist:
            return {
                "success": False,
                "error": "APP_NOT_ALLOWLISTED",
                "status": "PERMISSION_DENIED",
            }
        path = self.resolve_path(app_id)
        if not path:
            return {
                "success": False,
                "error": "APP_NOT_FOUND",
                "status": "BACKEND_UNAVAILABLE",
                "platform": platform.system(),
            }
        cmd = [path, *(args or [])]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
            rec = {"app_id": app_id, "path": path, "pid": proc.pid}
            self._launched.append(rec)
            logger.info("app_launched", app_id=app_id, path=path, pid=proc.pid)
            return {"success": True, "data": rec}
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "status": "EXECUTION_FAILED",
            }


application_manager = ApplicationManager()
