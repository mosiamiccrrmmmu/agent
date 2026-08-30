"""Windows-appropriate application data directories.

Never store mutable user data inside the installation directory.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _default_root() -> Path:
    if _is_windows():
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / "PersonalAI"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "personal-ai"
    return Path.home() / ".local" / "share" / "personal-ai"


@dataclass(frozen=True)
class AppPaths:
    root: Path
    config: Path
    database: Path
    logs: Path
    cache: Path
    downloads: Path
    user_files: Path

    def ensure(self) -> None:
        for p in (
            self.root,
            self.config,
            self.database,
            self.logs,
            self.cache,
            self.downloads,
            self.user_files,
        ):
            p.mkdir(parents=True, exist_ok=True)


def get_app_paths(root: Path | None = None) -> AppPaths:
    base = root or _default_root()
    paths = AppPaths(
        root=base,
        config=base / "config",
        database=base / "database",
        logs=base / "logs",
        cache=base / "cache",
        downloads=base / "downloads",
        user_files=base / "files",
    )
    paths.ensure()
    return paths
