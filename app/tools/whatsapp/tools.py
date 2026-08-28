"""WhatsApp tools — send always HIGH risk."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from app.integrations.whatsapp.provider import WhatsAppBusinessProvider
from app.tools.base import BaseTool, RiskLevel, ToolMetadata, ToolResult


class SendWhatsAppArgs(BaseModel):
    chat_id: str = Field(..., min_length=1, max_length=128)
    body: str = Field(..., min_length=1, max_length=4096)


class SendWhatsAppTool(BaseTool):
    args_model: ClassVar[type[BaseModel]] = SendWhatsAppArgs
    metadata = ToolMetadata(
        name="send_whatsapp",
        description="Send a WhatsApp message. Always requires human approval.",
        input_schema={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["chat_id", "body"],
        },
        risk_level=RiskLevel.HIGH,
        tags=["whatsapp"],
    )

    async def execute(self, chat_id: str, body: str, **_: Any) -> ToolResult:
        provider = WhatsAppBusinessProvider()
        result = await provider.send_message(chat_id, body)
        return ToolResult(success=result.get("success", False), data=result, error=result.get("error"))
