from app.agent.privacy import PrivacyLevel, cloud_allowed, prefer_local


def test_strict_no_cloud():
    assert cloud_allowed(PrivacyLevel.STRICT) is False
    assert prefer_local(PrivacyLevel.STRICT) is True


def test_standard_cloud_ok():
    assert cloud_allowed(PrivacyLevel.STANDARD) is True
