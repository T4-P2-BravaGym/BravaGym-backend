from datetime import timedelta
from hashlib import sha256

import pytest
from app import models
from app.models.types import utc_now
from sqlalchemy.exc import IntegrityError


def test_refresh_tokens_store_hashes_and_have_no_plain_token_column():
    assert hasattr(models, "RefreshToken")
    columns = models.RefreshToken.__table__.columns
    assert "token_hash" in columns
    assert "token" not in columns
    assert "refresh_token" not in columns


def test_refresh_token_can_be_saved_for_an_existing_user(db, make_user):
    user = make_user()
    token_hash = sha256(b"fictional-token-for-model-test").hexdigest()
    token = models.RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=utc_now() + timedelta(days=7),
    )
    db.add(token)
    db.commit()
    db.expire_all()

    saved = db.get(models.RefreshToken, token.id)
    assert saved.user_id == user.id
    assert saved.token_hash == token_hash
    assert saved.revoked_at is None
    assert saved.created_at is not None


def test_refresh_token_hash_must_be_unique(db, make_user):
    user = make_user()
    expires_at = utc_now() + timedelta(days=7)
    db.add_all(
        [
            models.RefreshToken(
                user_id=user.id, token_hash="a" * 64, expires_at=expires_at
            ),
            models.RefreshToken(
                user_id=user.id, token_hash="a" * 64, expires_at=expires_at
            ),
        ]
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_refresh_token_cannot_reference_a_missing_user(db):
    db.add(
        models.RefreshToken(
            user_id=999999,
            token_hash="b" * 64,
            expires_at=utc_now() + timedelta(days=7),
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_refresh_token_can_record_revocation(db, make_user):
    now = utc_now()
    token = models.RefreshToken(
        user_id=make_user().id,
        token_hash="c" * 64,
        expires_at=now + timedelta(days=7),
        revoked_at=now,
    )
    db.add(token)
    db.commit()
    db.expire_all()
    assert db.get(models.RefreshToken, token.id).revoked_at == now


def test_revoked_access_token_preserves_its_id_and_expiry(db):
    expires_at = utc_now() + timedelta(minutes=60)
    db.add(models.RevokedToken(jti="access-id-for-model-test", expires_at=expires_at))
    db.commit()
    saved = db.get(models.RevokedToken, "access-id-for-model-test")
    assert saved.expires_at == expires_at


def test_revoked_access_token_id_must_be_unique(db):
    expires_at = utc_now() + timedelta(minutes=60)
    db.add_all(
        [
            models.RevokedToken(jti="duplicate-access-id", expires_at=expires_at),
            models.RevokedToken(jti="duplicate-access-id", expires_at=expires_at),
        ]
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
