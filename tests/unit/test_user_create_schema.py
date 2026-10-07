"""Unit tests for UserCreate name rules (HU-02.6)."""
import pytest
from pydantic import ValidationError

from app.schemas.auth import UserCreate

# A valid body; each test changes only the field it cares about
VALID_DATA = {
    "email": "nueva@example.com",
    "password": "BravaDemo2026!",
    "first_name": "Ana",
    "last_name": "Torres",
    "phone": None,
}


def build(**overrides):
    """Returns VALID_DATA with some fields replaced."""
    return {**VALID_DATA, **overrides}


# parametrize runs the same test once per value in the list
@pytest.mark.parametrize("name", ["Ana", "María José", "Ana-Belén", "O'Connor", "Begoña", "Zoë"])
def test_user_create_accepts_real_names(name):
    user = UserCreate(**build(first_name=name, last_name=name))
    assert user.first_name == name


@pytest.mark.parametrize("name", ["Ana3", "123", "Ana_Belén", "Ana@"])
def test_user_create_rejects_names_with_digits_or_symbols(name):
    # pytest.raises passes only if the code inside raises that error
    with pytest.raises(ValidationError):
        UserCreate(**build(first_name=name))