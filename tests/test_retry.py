from app.agent.retry import RetryPolicy, is_retryable_error


def test_non_retryable():
    assert is_retryable_error("PERMISSION_DENIED") is False
    assert is_retryable_error("VALIDATION_ERROR") is False


def test_retryable():
    assert is_retryable_error("NETWORK_TIMEOUT") is True
    assert is_retryable_error("RATE_LIMITED") is True


def test_policy_enum():
    assert RetryPolicy.NO_RETRY.value == "no_retry"
