"""Personal AI desktop launcher.

Single process:
  1. Start FastAPI (uvicorn) on 127.0.0.1
  2. Open native window (pywebview) or system browser fallback
  3. On window close -> graceful shutdown

This is the ENTRY POINT for the packaged EXE.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path


def _prepare_env() -> None:
    os.environ.setdefault("APP_ENV", "desktop")
    os.environ.setdefault("DESKTOP_MODE", "true")
    os.environ.setdefault("HOST", "127.0.0.1")
    os.environ.setdefault("PORT", "8765")
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("DEFAULT_LLM_PROVIDER", os.environ.get("DEFAULT_LLM_PROVIDER", "mock"))

    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "PersonalAI"
    else:
        base = Path.home() / ".local" / "share" / "personal-ai"
    base.mkdir(parents=True, exist_ok=True)
    (base / "database").mkdir(exist_ok=True)
    (base / "logs").mkdir(exist_ok=True)
    (base / "config").mkdir(exist_ok=True)

    db = base / "database" / "personal_ai.db"
    os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{db.as_posix()}")
    os.environ.setdefault("DATABASE_URL_SYNC", f"sqlite:///{db.as_posix()}")

    if not os.environ.get("SECRET_KEY"):
        import hashlib

        seed = str(base / "config") + "|PersonalAI|v1"
        os.environ["SECRET_KEY"] = hashlib.sha256(seed.encode()).hexdigest()[:48]


def _port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def _find_port(host: str, preferred: int) -> int:
    if _port_free(host, preferred):
        return preferred
    for p in range(preferred + 1, preferred + 50):
        if _port_free(host, p):
            return p
    raise RuntimeError("No free port for Personal AI backend")


def _wait_health(url: str, timeout: float = 30.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def run() -> None:
    _prepare_env()
    host = os.environ.get("HOST", "127.0.0.1")
    port = _find_port(host, int(os.environ.get("PORT", "8765")))
    os.environ["PORT"] = str(port)

    import uvicorn

    from app.main import create_app

    app = create_app()
    config = uvicorn.Config(app, host=host, port=port, log_level="info", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="personal-ai-backend", daemon=True)
    thread.start()

    health = f"http://{host}:{port}/api/v1/health"
    if not _wait_health(health):
        print("ERROR: backend failed to start", file=sys.stderr)
        sys.exit(1)

    ui = f"http://{host}:{port}/"
    print(f"Personal AI ready at {ui}")

    try:
        import webview

        webview.create_window("Personal AI", ui, width=1100, height=720, min_size=(800, 560))
        webview.start()
    except Exception as exc:
        print(f"webview unavailable ({exc}); opening system browser", file=sys.stderr)
        import webbrowser

        webbrowser.open(ui)
        try:
            while thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

    server.should_exit = True
    thread.join(timeout=5)


def main() -> None:
    run()


if __name__ == "__main__":
    main()
