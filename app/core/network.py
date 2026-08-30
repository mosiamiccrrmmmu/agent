"""Online / offline detection for Hybrid routing."""

from __future__ import annotations

import socket
from enum import StrEnum


class NetworkMode(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


def probe_internet(timeout: float = 1.5) -> NetworkMode:
    """Best-effort TCP probe (not a guarantee of full internet)."""
    try:
        with socket.create_connection(("1.1.1.1", 443), timeout=timeout):
            return NetworkMode.ONLINE
    except OSError:
        pass
    try:
        with socket.create_connection(("8.8.8.8", 53), timeout=timeout):
            return NetworkMode.ONLINE
    except OSError:
        return NetworkMode.OFFLINE


def is_online() -> bool:
    return probe_internet() == NetworkMode.ONLINE
