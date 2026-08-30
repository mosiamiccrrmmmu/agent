"""Path sandbox for file tools — prevent traversal outside allowed roots."""

from __future__ import annotations

from pathlib import Path


class PathSandboxError(ValueError):
    pass


class PathSandbox:
    def __init__(self, roots: list[Path] | None = None) -> None:
        if roots is None:
            from app.desktop.paths import get_app_paths

            paths = get_app_paths()
            roots = [paths.root, Path.cwd() / "workspace"]
        self.roots = [r.resolve() for r in roots]
        for r in self.roots:
            r.mkdir(parents=True, exist_ok=True)

    def resolve(self, user_path: str) -> Path:
        raw = Path(user_path).expanduser()
        candidate = (
            (self.roots[0] / raw).resolve() if not raw.is_absolute() else raw.resolve()
        )
        for root in self.roots:
            try:
                candidate.relative_to(root)
                return candidate
            except ValueError:
                continue
        raise PathSandboxError(f"Path outside allowed roots: {user_path}")
