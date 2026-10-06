import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_missing_secret_key_fails_and_names_it(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert "secret_key" in str(error.value)