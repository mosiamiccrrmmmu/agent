from app.apps.manager import AppEntry, ApplicationManager


def test_not_allowlisted():
    m = ApplicationManager()
    r = m.launch("malware")
    assert r["success"] is False
    assert r["error"] == "APP_NOT_ALLOWLISTED"


def test_list_apps():
    m = ApplicationManager()
    ids = {a["id"] for a in m.list_apps()}
    assert "notepad" in ids
    assert "chrome" in ids


def test_launch_missing_returns_not_found():
    m = ApplicationManager(
        allowlist=[
            AppEntry(
                id="nope",
                name="Nope",
                windows_candidates=["does-not-exist-xyz.exe"],
                linux_candidates=["does-not-exist-xyz-binary"],
            )
        ]
    )
    r = m.launch("nope")
    assert r["success"] is False
    assert r["error"] == "APP_NOT_FOUND"
