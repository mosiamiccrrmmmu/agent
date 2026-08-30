"""Gmail integration via OAuth2 (Google API).

Tokens come from CredentialStore — never passed to the LLM.
Send actions must go through PermissionManager (HIGH risk).

Status honesty:
- Without a valid OAuth token: NOT CONFIGURED (never success=True).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.credentials.store import credential_store

logger = get_logger(__name__)


class EmailMessage(BaseModel):
    id: str
    thread_id: str = ""
    subject: str = ""
    from_addr: str = ""
    to: list[str] = Field(default_factory=list)
    snippet: str = ""
    body: str = ""
    labels: list[str] = Field(default_factory=list)


class GmailClient:
    """Thin client. Real HTTP calls require valid OAuth access token."""

    def __init__(self, user_id: str = "default") -> None:
        self.user_id = user_id

    def _token(self) -> str | None:
        return credential_store.get_token(self.user_id, "gmail", "oauth_access")

    def is_connected(self) -> bool:
        return self._token() is not None

    def status(self) -> str:
        return "connected" if self.is_connected() else "not_configured"

    async def list_messages(self, query: str = "", max_results: int = 10) -> list[EmailMessage]:
        if not self._token():
            return []
        # Real Gmail API not wired — fail closed with empty + log
        logger.warning("gmail_list_messages_not_implemented", query=query)
        return []

    async def read_message(self, message_id: str) -> EmailMessage | None:
        if not self._token():
            return None
        logger.warning("gmail_read_message_not_implemented", message_id=message_id)
        return None

    async def draft_reply(self, message_id: str, body: str) -> dict[str, Any]:
        if not self._token():
            return {"success": False, "status": "not_configured", "error": "Gmail not connected"}
        return {
            "success": False,
            "status": "not_implemented",
            "error": "Gmail draft API not implemented",
        }

    async def send_message(self, to: str, subject: str, body: str) -> dict[str, Any]:
        """HIGH risk — caller must enforce approval. Never fake success."""
        if not self._token():
            return {"success": False, "status": "not_configured", "error": "Gmail not connected"}
        logger.warning("gmail_send_not_implemented", to=to)
        return {
            "success": False,
            "status": "not_implemented",
            "error": "Gmail send API not implemented — configure Google OAuth and implement Gmail API client",
        }
