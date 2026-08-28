"""Gmail tools registered with the agent tool registry."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from app.integrations.gmail.client import GmailClient
from app.tools.base import BaseTool, RiskLevel, ToolMetadata, ToolResult


class ListEmailArgs(BaseModel):
    query: str = Field(default="", max_length=500)
    max_results: int = Field(default=10, ge=1, le=50)


class SendEmailArgs(BaseModel):
    to: str = Field(..., min_length=3, max_length=320)
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=10000)


class ListEmailsTool(BaseTool):
    args_model: ClassVar[type[BaseModel]] = ListEmailArgs
    metadata = ToolMetadata(
        name="list_emails",
        description="List or search Gmail messages for the user.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 10},
            },
        },
        risk_level=RiskLevel.LOW,
        tags=["gmail", "email"],
    )

    async def execute(self, query: str = "", max_results: int = 10, **_: Any) -> ToolResult:
        client = GmailClient()
        if not client.is_connected():
            return ToolResult(success=False, error="Gmail not connected. Complete OAuth first.")
        msgs = await client.list_messages(query=query, max_results=max_results)
        return ToolResult(success=True, data=[m.model_dump() for m in msgs])


class SendEmailTool(BaseTool):
    args_model: ClassVar[type[BaseModel]] = SendEmailArgs
    metadata = ToolMetadata(
        name="send_email",
        description="Send an email via Gmail. Requires human approval.",
        input_schema={
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
        risk_level=RiskLevel.HIGH,
        tags=["gmail", "email"],
    )

    async def execute(self, to: str, subject: str, body: str, **_: Any) -> ToolResult:
        client = GmailClient()
        result = await client.send_message(to=to, subject=subject, body=body)
        return ToolResult(success=result.get("success", False), data=result, error=result.get("error"))
