"""Local API authentication between desktop UI and backend.

The backend binds to localhost only. Requests from the desktop shell
must present a local API token stored in the secure secret store.
"""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.desktop.secrets import SecureSecretStore


class LocalAuth:
    TOKEN_NAME = "local_api_token"

    def __init__(self, store: SecureSecretStore | None = None) -> None:
        self.store = store or SecureSecretStore()

    def ensure_token(self) -> str:
        existing = self.store.get(self.TOKEN_NAME)
        if existing:
            return existing
        token = secrets.token_urlsafe(32)
        self.store.set(self.TOKEN_NAME, token)
        return token

    def validate(self, provided: str | None) -> bool:
        if not provided:
            return False
        expected = self.store.get(self.TOKEN_NAME)
        if not expected:
            return False
        return secrets.compare_digest(provided, expected)

    def require(
        self,
        x_personal_ai_token: Annotated[str | None, Header()] = None,
    ) -> None:
        if not self.validate(x_personal_ai_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing local API token",
            )


local_auth = LocalAuth()
