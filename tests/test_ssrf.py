from app.browser.ssrf import is_ssrf_blocked


def test_blocks_localhost():
    blocked, _ = is_ssrf_blocked("http://127.0.0.1/admin")
    assert blocked
    blocked2, _ = is_ssrf_blocked("http://localhost:8080/")
    assert blocked2


def test_blocks_file_scheme():
    blocked, _ = is_ssrf_blocked("file:///etc/passwd")
    assert blocked


def test_blocks_metadata():
    blocked, _ = is_ssrf_blocked("http://169.254.169.254/latest/meta-data/")
    assert blocked


def test_allows_public_https():
    blocked, reason = is_ssrf_blocked("https://example.com/path")
    assert not blocked
    assert reason == "ok"
