"""WhatsApp provider abstraction.

IMPORTANT:
- WhatsApp Business API is the official channel (requires Meta Business setup).
- WhatsApp Web automation (browser) is unofficial, fragile, and may violate ToS.
  Do not present Web automation as an official API.

Never return success=True for unimplemented sends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class WhatsAppMessage(BaseModel):
    id: str
    chat_id: str
    sender: str
    body: str
    timestamp: str | None = None


class WhatsAppChat(BaseModel):
    id: str
    name: str
    last_message: str = ""


class WhatsAppProvider(ABC):
    name: str

    @abstractmethod
    async def list_chats(self, limit: int = 20) -> list[WhatsAppChat]:
        ...

    @abstractmethod
    async def read_messages(self, chat_id: str, limit: int = 20) -> list[WhatsAppMessage]:
        ...

    @abstractmethod
    async def send_message(self, chat_id: str, body: str) -> dict[str, Any]:
        """HIGH risk — must require approval at tool layer."""
        ...

    def status(self) -> str:
        return "not_configured"


class WhatsAppBusinessProvider(WhatsAppProvider):
    """Official WhatsApp Cloud / Business API adapter."""

    name = "whatsapp_business"

    def __init__(self, access_token: str | None = None, phone_number_id: str | None = None) -> None:
        self.access_token = access_token
        self.phone_number_id = phone_number_id

    def status(self) -> str:
        if self.access_token and self.phone_number_id:
            return "configured_not_implemented"
        return "not_configured"

    async def list_chats(self, limit: int = 20) -> list[WhatsAppChat]:
        if not self.access_token:
            return []
        logger.warning("whatsapp_business_list_chats_not_implemented")
        return []

    async def read_messages(self, chat_id: str, limit: int = 20) -> list[WhatsAppMessage]:
        return []

    async def send_message(self, chat_id: str, body: str) -> dict[str, Any]:
        if not self.access_token or not self.phone_number_id:
            return {
                "success": False,
                "status": "not_configured",
                "error": "WhatsApp Business not configured (token + phone_number_id required)",
            }
        return {
            "success": False,
            "status": "not_implemented",
            "error": "WhatsApp Business Cloud API client not implemented",
        }


class WhatsAppWebProvider(WhatsAppProvider):
    """Browser-based WhatsApp Web automation (unofficial).

    Documented risks: session ban, ToS issues, fragility. Prefer Business API.
    """

    name = "whatsapp_web"

    def __init__(self) -> None:
        self._connected = False

    def status(self) -> str:
        return "not_implemented"

    async def list_chats(self, limit: int = 20) -> list[WhatsAppChat]:
        logger.warning("whatsapp_web_unofficial", action="list_chats")
        return []

    async def read_messages(self, chat_id: str, limit: int = 20) -> list[WhatsAppMessage]:
        logger.warning("whatsapp_web_unofficial", action="read_messages")
        return []

    async def send_message(self, chat_id: str, body: str) -> dict[str, Any]:
        logger.warning("whatsapp_web_unofficial", action="send_message")
        return {
            "success": False,
            "status": "not_implemented",
            "error": (
                "WhatsApp Web automation is unofficial and not implemented. "
                "Use WhatsApp Business Cloud API when available."
            ),
        }
