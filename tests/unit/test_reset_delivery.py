from concurrent.futures import ThreadPoolExecutor

import pytest
from app.core.config import Settings
from app.core.rate_limit import AttemptWindowLimiter
from pydantic import ValidationError


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://user:pass@example.com",
        "https://example.com/path",
        "https://example.com?x=1",
        "https://example.com#token",
        "https://example.com\\evil",
    ],
)
def test_reset_frontend_url_rejects_untrusted_shapes(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, secret_key="demo", frontend_url=url)


def test_reset_frontend_url_requires_https_outside_local():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            secret_key="demo",
            environment="production",
            frontend_url="http://example.com",
        )
    settings = Settings(
        _env_file=None,
        secret_key="demo",
        environment="production",
        frontend_url="https://brava.example.com",
    )
    assert settings.frontend_url == "https://brava.example.com"


def test_delivery_limit_is_atomic():
    limiter = AttemptWindowLimiter(max_attempts=3, window_seconds=900)
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(
            pool.map(lambda _: limiter.record_if_allowed("same-email"), range(20))
        )
    assert sum(outcomes) == 3
