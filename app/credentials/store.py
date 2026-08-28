"""Secure credential storage abstraction.

Tokens are never exposed to the LLM. Tools receive capabilities only.
In production, encrypt at rest (e.g. Fernet + SECRET_KEY or a KMS).
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.config import get_settings


class CredentialRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    provider: str  # gmail | calendar | telegram | whatsapp | ...
    kind: str  # oauth_access | oauth_refresh | api_token
    # Encrypted payload (base64); never log or send to LLM
    ciphertext: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None


def _derive_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode()).digest()


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    # Lightweight obfuscation for MVP — replace with Fernet/KMS in production
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


class CredentialStore:
    """In-memory encrypted credential store (MVP). Persist via DB in production."""

    def __init__(self) -> None:
        self._records: dict[str, CredentialRecord] = {}

    def _encrypt(self, plaintext: str) -> str:
        settings = get_settings()
        key = _derive_key(settings.secret_key)
        raw = _xor_bytes(plaintext.encode("utf-8"), key)
        return base64.urlsafe_b64encode(raw).decode("ascii")

    def _decrypt(self, ciphertext: str) -> str:
        settings = get_settings()
        key = _derive_key(settings.secret_key)
        raw = base64.urlsafe_b64decode(ciphertext.encode("ascii"))
        return _xor_bytes(raw, key).decode("utf-8")

    def put(
        self,
        user_id: str,
        provider: str,
        kind: str,
        token: str,
        *,
        metadata: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> CredentialRecord:
        for rid, rec in list(self._records.items()):
            if rec.user_id == user_id and rec.provider == provider and rec.kind == kind:
                del self._records[rid]
        record = CredentialRecord(
            user_id=user_id,
            provider=provider,
            kind=kind,
            ciphertext=self._encrypt(token),
            metadata=metadata or {},
            expires_at=expires_at,
        )
        self._records[record.id] = record
        return record

    def get_token(self, user_id: str, provider: str, kind: str) -> str | None:
        for rec in self._records.values():
            if rec.user_id == user_id and rec.provider == provider and rec.kind == kind:
                return self._decrypt(rec.ciphertext)
        return None

    def has(self, user_id: str, provider: str) -> bool:
        return any(
            r.user_id == user_id and r.provider == provider for r in self._records.values()
        )

    def list_providers(self, user_id: str) -> list[str]:
        return sorted({r.provider for r in self._records.values() if r.user_id == user_id})

    def delete(self, user_id: str, provider: str) -> int:
        to_del = [
            rid
            for rid, r in self._records.items()
            if r.user_id == user_id and r.provider == provider
        ]
        for rid in to_del:
            del self._records[rid]
        return len(to_del)


credential_store = CredentialStore()
