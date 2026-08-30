"""SSRF protection for browser navigation."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

_BLOCKED_SCHEMES = frozenset(
    {"file", "ftp", "chrome", "chrome-extension", "about", "data"}
)
_PRIVATE_HOST_RE = re.compile(
    r"^(localhost|127\.|0\.0\.0\.0|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|"
    r"\[?::1\]?|metadata\.google|169\.254\.169\.254)",
    re.I,
)


def is_ssrf_blocked(url: str, *, allow_localhost: bool = False) -> tuple[bool, str]:
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return True, "invalid_url"
    scheme = (parsed.scheme or "").lower()
    if scheme in _BLOCKED_SCHEMES:
        return True, f"blocked_scheme:{scheme or 'none'}"
    if scheme not in ("http", "https"):
        return True, f"unsupported_scheme:{scheme or 'none'}"
    host = (parsed.hostname or "").lower()
    if not host:
        return True, "missing_host"
    if not allow_localhost and _PRIVATE_HOST_RE.match(host):
        return True, "private_or_local_host"
    try:
        ip = ipaddress.ip_address(host)
        if not allow_localhost and (
            ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        ):
            return True, "private_ip"
    except ValueError:
        pass
    return False, "ok"
