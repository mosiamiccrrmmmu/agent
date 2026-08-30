from app.tools.base import ToolResult, ToolStatus


def test_success_defaults_status():
    r = ToolResult(success=True, data={"ok": 1})
    assert r.status == ToolStatus.SUCCESS


def test_failure_defaults_status():
    r = ToolResult(success=False, error="x")
    assert r.status == ToolStatus.FAILED
    assert r.message == "x"


def test_explicit_not_configured():
    r = ToolResult(
        success=False,
        status=ToolStatus.NOT_CONFIGURED,
        error_code="GMAIL_NOT_CONFIGURED",
        error="Gmail not connected",
    )
    assert r.success is False
    assert r.status == ToolStatus.NOT_CONFIGURED
