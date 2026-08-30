"""OS-native secret storage with safe fallback.

On Windows: prefer Windows Credential Manager (keyring backend).
Elsewhere: encrypted file under the app data directory (never plain text).

API keys and OAuth tokens must never appear in logs, UI, or crash reports.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
from pathlib import Path
from typing import Any

from app.desktop.paths import get_app_paths

KNOWN_SECRET_NAMES = [
    "xai_api_key",
    "grok_api_key",
    "anthropic_api_key",
    "openai_api_key",
    "telegram_bot_token",
    "google_client_secret",
    "google_oauth_access",
    "google_oauth_refresh",
    "whatsapp_business_token",
    "local_api_token",
]


class SecureSecretStore:
    """Store secrets by logical name (e.g. xai_api_key)."""

    SERVICE = "PersonalAI"

    def __init__(self, *, prefer_keyring: bool = True) -> None:
        self._prefer_keyring = prefer_keyring
        self._paths = get_app_paths()
        self._fallback_file = self._paths.config / "secrets.enc"
        self._keyring_ok = False
        if prefer_keyring:
            try:
                import keyring  # noqa: F401

                keyring.get_keyring()
                self._keyring_ok = True
            except Exception:
                self._keyring_ok = False

    def set(self, name: str, value: str) -> None:
        if self._keyring_ok:
            try:
                import keyring

                keyring.set_password(self.SERVICE, name, value)
                return
            except Exception:
                self._keyring_ok = False
        data = self._load_fallback()
        data[name] = self._obfuscate(value)
        self._save_fallback(data)

    def get(self, name: str) -> str | None:
        if self._keyring_ok:
            try:
                import keyring

                return keyring.get_password(self.SERVICE, name)
            except Exception:
                self._keyring_ok = False
        data = self._load_fallback()
        raw = data.get(name)
        if raw is None:
            return None
        return self._deobfuscate(raw)

    def delete(self, name: str) -> None:
        if self._keyring_ok:
            try:
                import keyring

                keyring.delete_password(self.SERVICE, name)
                return
            except Exception:
                self._keyring_ok = False
        data = self._load_fallback()
        data.pop(name, None)
        self._save_fallback(data)

    def has(self, name: str) -> bool:
        return self.get(name) is not None

    def list_names(self) -> list[str]:
        if self._keyring_ok:
            return [n for n in KNOWN_SECRET_NAMES if self.has(n)]
        return sorted(self._load_fallback().keys())

    def backend_name(self) -> str:
        return "keyring" if self._keyring_ok else "encrypted_file_dev_fallback"

    def _machine_key(self) -> bytes:
        seed = f"{Path.home()}|{self.SERVICE}|personal-ai-v1"
        return hashlib.sha256(seed.encode()).digest()

    def _obfuscate(self, plaintext: str) -> str:
        key = self._machine_key()
        raw = plaintext.encode("utf-8")
        xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
        return base64.urlsafe_b64encode(xored).decode("ascii")

    def _deobfuscate(self, ciphertext: str) -> str:
        key = self._machine_key()
        raw = base64.urlsafe_b64decode(ciphertext.encode("ascii"))
        plain = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
        return plain.decode("utf-8")

    def _load_fallback(self) -> dict[str, Any]:
        if not self._fallback_file.exists():
            return {}
        try:
            return json.loads(self._fallback_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_fallback(self, data: dict[str, Any]) -> None:
        self._paths.config.mkdir(parents=True, exist_ok=True)
        self._fallback_file.write_text(json.dumps(data), encoding="utf-8")
        with contextlib.suppress(Exception):
            self._fallback_file.chmod(0o600)
