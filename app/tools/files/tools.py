"""Sandboxed file tools — list/read/write/delete with path policy."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from app.tools.base import BaseTool, RiskLevel, ToolMetadata, ToolResult
from app.tools.files.sandbox import PathSandbox, PathSandboxError

_sandbox: PathSandbox | None = None


def get_sandbox() -> PathSandbox:
    global _sandbox
    if _sandbox is None:
        _sandbox = PathSandbox()
    return _sandbox


class ListFilesArgs(BaseModel):
    path: str = Field(default=".", max_length=500)


class ReadFileArgs(BaseModel):
    path: str = Field(..., max_length=500)
    max_bytes: int = Field(default=100_000, ge=1, le=1_000_000)


class WriteFileArgs(BaseModel):
    path: str = Field(..., max_length=500)
    content: str = Field(..., max_length=500_000)


class DeleteFileArgs(BaseModel):
    path: str = Field(..., max_length=500)


class ListFilesTool(BaseTool):
    args_model: ClassVar[type[BaseModel]] = ListFilesArgs
    metadata = ToolMetadata(
        name="list_files",
        description="List files in a sandboxed directory under PersonalAI data roots.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
        },
        risk_level=RiskLevel.LOW,
        tags=["files"],
    )

    async def execute(self, path: str = ".", **_: Any) -> ToolResult:
        try:
            target = get_sandbox().resolve(path)
        except PathSandboxError as exc:
            return ToolResult(success=False, error=str(exc))
        if not target.exists():
            return ToolResult(success=False, error="Path does not exist")
        if not target.is_dir():
            return ToolResult(success=False, error="Not a directory")
        entries = []
        for child in sorted(target.iterdir())[:200]:
            entries.append(
                {
                    "name": child.name,
                    "is_dir": child.is_dir(),
                    "size": child.stat().st_size if child.is_file() else None,
                }
            )
        return ToolResult(success=True, data={"path": str(target), "entries": entries})


class ReadFileTool(BaseTool):
    args_model: ClassVar[type[BaseModel]] = ReadFileArgs
    metadata = ToolMetadata(
        name="read_file",
        description="Read a text file inside the sandbox (max size limited).",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_bytes": {"type": "integer"},
            },
            "required": ["path"],
        },
        risk_level=RiskLevel.LOW,
        tags=["files"],
    )

    async def execute(self, path: str, max_bytes: int = 100_000, **_: Any) -> ToolResult:
        try:
            target = get_sandbox().resolve(path)
        except PathSandboxError as exc:
            return ToolResult(success=False, error=str(exc))
        if not target.is_file():
            return ToolResult(success=False, error="Not a file")
        data = target.read_bytes()[:max_bytes]
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return ToolResult(success=False, error="Binary or non-UTF8 file")
        return ToolResult(success=True, data={"path": str(target), "content": text})


class WriteFileTool(BaseTool):
    args_model: ClassVar[type[BaseModel]] = WriteFileArgs
    metadata = ToolMetadata(
        name="write_file",
        description="Create or overwrite a text file inside the sandbox.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
        risk_level=RiskLevel.MEDIUM,
        tags=["files"],
    )

    async def execute(self, path: str, content: str, **_: Any) -> ToolResult:
        try:
            target = get_sandbox().resolve(path)
        except PathSandboxError as exc:
            return ToolResult(success=False, error=str(exc))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult(
            success=True, data={"path": str(target), "bytes": len(content.encode())}
        )


class DeleteFileTool(BaseTool):
    args_model: ClassVar[type[BaseModel]] = DeleteFileArgs
    metadata = ToolMetadata(
        name="delete_file",
        description="Delete a file inside the sandbox. Requires approval (HIGH).",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        risk_level=RiskLevel.HIGH,
        tags=["files"],
    )

    async def execute(self, path: str, **_: Any) -> ToolResult:
        try:
            target = get_sandbox().resolve(path)
        except PathSandboxError as exc:
            return ToolResult(success=False, error=str(exc))
        if not target.exists():
            return ToolResult(success=False, error="Not found")
        if target.is_dir():
            return ToolResult(success=False, error="Refusing to delete directories")
        target.unlink()
        return ToolResult(success=True, data={"deleted": str(target)})
