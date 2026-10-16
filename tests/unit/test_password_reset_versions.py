import jwt
import pytest
from app import models
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, decode_access_token
from app.models import User
from app.models.types import utc_now
from app.services import auth_service
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


def test_reset_model_stores_hash_only_and_enforces_uniqueness(db, make_user):
    assert hasattr(models, "PasswordResetToken")
    model = models.PasswordResetToken
    assert "token" not in model.__table__.columns
    user = make_user()
    for _ in range(2):
        db.add(model(user_id=user.id, token_hash="a" * 64, expires_at=utc_now()))
    with pytest.raises(IntegrityError):
        db.flush()


def test_new_account_and_new_tokens_have_session_version_zero(db, make_user):
    user = make_user()
    assert user.session_version == 0
    payload = decode_access_token(create_access_token(user.id, user.role.name))
    assert payload["ver"] == 0


def test_new_login_uses_current_account_session_version(db, make_user):
    user = make_user()
    user.session_version = 2
    db.commit()
    tokens = auth_service.issue_session(db, user)
    assert decode_access_token(tokens.access_token)["ver"] == 2
    assert auth_service.decode_refresh_token(tokens.refresh_token)["ver"] == 2


@pytest.mark.parametrize("version", [-1, True, "1", 1.5, None])
def test_present_invalid_token_version_is_rejected(version):
    settings = get_settings()
    payload = decode_access_token(create_access_token(1, "member"))
    payload["ver"] = version
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_old_access_refresh_and_logout_rejected_after_version_increment(
    db, make_user, client
):
    user = make_user()
    old = auth_service.issue_session(db, user)
    payload = decode_access_token(old.access_token)
    payload.pop("ver", None)
    settings = get_settings()
    legacy = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    assert (
        client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {legacy}"}
        ).status_code
        == 200
    )
    user.session_version = 1
    db.commit()
    for token in (old.access_token, legacy):
        assert (
            client.get(
                "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
            ).status_code
            == 401
        )
    with pytest.raises(UnauthorizedError):
        auth_service.refresh_session(db, old.refresh_token)
    with pytest.raises(UnauthorizedError):
        auth_service.logout_session(db, old.access_token, old.refresh_token)
    current = auth_service.issue_session(db, db.scalar(select(User)))
    assert (
        client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {current.access_token}"},
        ).status_code
        == 200
    )
