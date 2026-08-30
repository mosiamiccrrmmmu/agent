from __future__ import annotations

"""Tool base classes and metadata with strict runtime validation."""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, Field, ValidationError


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DENIED = "DENIED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNAVAILABLE = "UNAVAILABLE"
    RETRYING = "RETRYING"
    BLOCKED = "BLOCKED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"


class ToolResult(BaseModel):
    """Standard result returned by every tool."""

    success: bool
    data: Any = None
    error: str | None = None
    status: ToolStatus | None = None
    error_code: str | None = None
    message: str | None = None
    retryable: bool = False
    requires_approval: bool = False
    approval_id: str | None = None
    audit_id: str | None = None
    duration_ms: float | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.status is None:
            if self.requires_approval:
                object.__setattr__(self, "status", ToolStatus.REQUIRES_APPROVAL)
            elif self.success:
                object.__setattr__(self, "status", ToolStatus.SUCCESS)
            else:
                object.__setattr__(self, "status", ToolStatus.FAILED)
        if self.message is None and self.error:
            object.__setattr__(self, "message", self.error)


class ToolMetadata(BaseModel):
    """Metadata that the Agent uses to discover and decide about tools."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    required_permissions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class BaseTool(ABC):
    """Abstract base for all tools.

    Subclasses SHOULD set ``args_model`` to a Pydantic model for strict
    runtime validation of tool arguments before ``execute`` runs.
    """

    metadata: ToolMetadata
    args_model: ClassVar[type[BaseModel] | None] = None

    def validate_arguments(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        if self.args_model is not None:
            try:
                validated = self.args_model.model_validate(kwargs)
            except ValidationError as exc:
                errors = []
                for err in exc.errors():
                    loc = ".".join(str(x) for x in err.get("loc", ()))
                    msg = err.get("msg", "invalid")
                    errors.append(f"{loc}: {msg}" if loc else msg)
                raise ValueError("; ".join(errors)) from None
            return validated.model_dump()

        schema = self.metadata.input_schema
        required = schema.get("required", [])
        missing = [r for r in required if r not in kwargs]
        if missing:
            raise ValueError(f"Missing required arguments: {missing}")
        props = schema.get("properties", {})
        if props:
            return {k: v for k, v in kwargs.items() if k in props}
        return kwargs

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        ...

    def to_llm_definition(self) -> dict[str, Any]:
        return {
            "name": self.metadata.name,
            "description": self.metadata.description,
            "parameters": self.metadata.input_schema,
        }
