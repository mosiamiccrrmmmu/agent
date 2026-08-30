"""Global execution gate — stop-all blocks new work until reset."""

from __future__ import annotations

import threading

_lock = threading.Lock()
_blocked = False


def block_all() -> None:
    global _blocked
    with _lock:
        _blocked = True


def reset_gate() -> None:
    global _blocked
    with _lock:
        _blocked = False


def is_blocked() -> bool:
    with _lock:
        return _blocked
