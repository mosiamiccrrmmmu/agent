"""Gmail integration via OAuth2 (Google API).

Tokens come from CredentialStore — never passed to the LLM.
Send actions must go through PermissionManager (HIGH risk).
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

    async def list_messages(self, query: str = "", max_results: int = 10) -> list[EmailMessage]:
        token = self._token()
        if not token:
            return []
        logger.info("gmail_list_messages", query=query, max_results=max_results)
        return []

    async def read_message(self, message_id: str) -> EmailMessage | None:
        if not self._token():
            return None
        logger.info("gmail_read_message", message_id=message_id)
        return None

    async def draft_reply(self, message_id: str, body: str) -> dict[str, Any]:
        if not self._token():
            return {"success": False, "error": "Gmail not connected"}
        return {"success": True, "draft_id": "draft-stub", "body": body}

    async def send_message(self, to: str, subject: str, body: str) -> dict[str, Any]:
        """HIGH risk — caller must enforce approval."""
        if not self._token():
            return {"success": False, "error": "Gmail not connected"}
        logger.info("gmail_send", to=to, subject=subject)
        return {"success": True, "message_id": "sent-stub", "note": "Configure real Gmail API"}
