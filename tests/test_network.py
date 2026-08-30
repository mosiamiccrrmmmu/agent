from app.core.network import NetworkMode, probe_internet


def test_probe_returns_mode():
    mode = probe_internet(timeout=0.5)
    assert mode in (NetworkMode.ONLINE, NetworkMode.OFFLINE)
