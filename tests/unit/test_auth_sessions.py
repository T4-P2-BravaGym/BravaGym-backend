from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from app.core.database import Base, enable_sqlite_foreign_keys
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token, hash_refresh_token
from app.models import RefreshToken, RevokedToken, Role, User
from app.models.enums import RoleName
from app.models.types import utc_now
from app.services import auth_service
from freezegun import freeze_time
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker


def test_issue_session_stores_only_the_refresh_hash(db, make_user):
    assert callable(getattr(auth_service, "issue_session", None))
    user = make_user()
    tokens = auth_service.issue_session(db, user)
    saved = db.scalar(select(RefreshToken))
    assert saved.user_id == user.id
    assert saved.token_hash == hash_refresh_token(tokens.refresh_token)
    assert saved.token_hash != tokens.refresh_token
    assert saved.revoked_at is None
    assert decode_access_token(tokens.access_token)["sub"] == str(user.id)
    assert tokens.access_token not in repr(tokens)
    assert tokens.refresh_token not in repr(tokens)


def test_refresh_rotates_once_and_rejects_reuse(db, make_user):
    user = make_user()
    original = auth_service.issue_session(db, user)
    replacement = auth_service.refresh_session(db, original.refresh_token)
    assert replacement.refresh_token != original.refresh_token
    assert replacement.access_token != original.access_token
    old = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(original.refresh_token)
        )
    )
    assert old.revoked_at is not None
    with pytest.raises(UnauthorizedError):
        auth_service.refresh_session(db, original.refresh_token)
    assert db.scalar(select(func.count()).select_from(RefreshToken)) == 2


def test_failed_refresh_rolls_back_consumption(db, make_user, monkeypatch):
    original = auth_service.issue_session(db, make_user())

    def fail_to_create_replacement(*args):
        raise RuntimeError("Simulated token persistence failure")

    with monkeypatch.context() as patch:
        patch.setattr(auth_service, "_new_session_tokens", fail_to_create_replacement)
        with pytest.raises(RuntimeError):
            auth_service.refresh_session(db, original.refresh_token)
    assert db.scalar(select(func.count()).select_from(RefreshToken)) == 1
    assert auth_service.refresh_session(db, original.refresh_token)


def test_concurrent_refresh_has_only_one_success(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'refresh-race.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with sessions() as db:
            user = User(
                email="concurrency-demo@example.com",
                password_hash="not-used-for-this-token-test",
                first_name="Concurrency",
                last_name="Demo",
                role=Role(name=RoleName.MEMBER),
            )
            db.add(user)
            db.commit()
            original = auth_service.issue_session(db, user)
        barrier = Barrier(2)

        def refresh_once():
            with sessions() as db:
                barrier.wait(timeout=5)
                try:
                    auth_service.refresh_session(db, original.refresh_token)
                except UnauthorizedError:
                    return "rejected"
                return "success"

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(refresh_once)
            second = pool.submit(refresh_once)
            assert sorted([first.result(), second.result()]) == ["rejected", "success"]
        with sessions() as db:
            active = db.scalar(
                select(func.count())
                .select_from(RefreshToken)
                .where(RefreshToken.revoked_at.is_(None))
            )
            assert active == 1
    finally:
        engine.dispose()


def test_refresh_rejects_inactive_user(db, make_user):
    user = make_user()
    tokens = auth_service.issue_session(db, user)
    user.is_active = False
    db.commit()
    with pytest.raises(UnauthorizedError):
        auth_service.refresh_session(db, tokens.refresh_token)
    assert db.scalar(select(func.count()).select_from(RefreshToken)) == 1


def test_issue_session_rejects_inactive_user(db, make_user):
    with pytest.raises(UnauthorizedError):
        auth_service.issue_session(db, make_user(is_active=False))
    assert db.scalar(select(func.count()).select_from(RefreshToken)) == 0


def test_refresh_rejects_expiry_at_seven_days(db, make_user):
    with freeze_time("2026-10-06 10:00:00"):
        tokens = auth_service.issue_session(db, make_user())
    with freeze_time("2026-10-13 10:00:00"), pytest.raises(UnauthorizedError):
        auth_service.refresh_session(db, tokens.refresh_token)


def test_refresh_rejects_invalid_and_wrong_type_tokens(db, make_user):
    tokens = auth_service.issue_session(db, make_user())
    for invalid in ["not-a-jwt", tokens.access_token]:
        with pytest.raises(UnauthorizedError):
            auth_service.refresh_session(db, invalid)


def test_logout_revokes_refresh_and_current_access(db, make_user, client):
    tokens = auth_service.issue_session(db, make_user())
    headers = {"Authorization": "Bearer " + tokens.access_token}
    assert client.get("/api/v1/users/me", headers=headers).status_code == 200
    auth_service.logout_session(db, tokens.access_token, tokens.refresh_token)
    jti = decode_access_token(tokens.access_token)["jti"]
    assert db.get(RevokedToken, jti) is not None
    assert client.get("/api/v1/users/me", headers=headers).status_code == 401
    with pytest.raises(UnauthorizedError):
        auth_service.refresh_session(db, tokens.refresh_token)


def test_logout_cannot_revoke_another_users_refresh(db, make_user):
    first = auth_service.issue_session(db, make_user())
    other = auth_service.issue_session(db, make_user())
    with pytest.raises(UnauthorizedError):
        auth_service.logout_session(db, first.access_token, other.refresh_token)
    assert db.scalar(select(func.count()).select_from(RevokedToken)) == 0
    assert auth_service.refresh_session(db, other.refresh_token)


def test_logout_twice_does_not_duplicate_revocation(db, make_user):
    tokens = auth_service.issue_session(db, make_user())
    auth_service.logout_session(db, tokens.access_token, tokens.refresh_token)
    auth_service.logout_session(db, tokens.access_token, tokens.refresh_token)
    assert db.scalar(select(func.count()).select_from(RevokedToken)) == 1


def test_concurrent_logout_does_not_fail_or_duplicate_revocation(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'logout-race.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    start = Barrier(2)
    reads = Barrier(2)

    def synchronize_revocation_reads(
        conn, cursor, statement, parameters, context, many
    ):
        # Force both real SELECTs to observe the absent row before either inserts.
        if (
            statement.lstrip().startswith("SELECT")
            and "FROM revoked_tokens" in statement
        ):
            reads.wait(timeout=5)

    try:
        with sessions() as db:
            user = User(
                email="logout-demo@example.com",
                password_hash="not-used-for-this-token-test",
                first_name="Logout",
                last_name="Demo",
                role=Role(name=RoleName.MEMBER),
            )
            db.add(user)
            db.commit()
            tokens = auth_service.issue_session(db, user)
        event.listen(engine, "after_cursor_execute", synchronize_revocation_reads)

        def logout_once():
            with sessions() as db:
                start.wait(timeout=5)
                auth_service.logout_session(
                    db, tokens.access_token, tokens.refresh_token
                )

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(logout_once)
                second = pool.submit(logout_once)
                first.result(timeout=15)
                second.result(timeout=15)
        finally:
            event.remove(engine, "after_cursor_execute", synchronize_revocation_reads)
        with sessions() as db:
            assert db.scalar(select(func.count()).select_from(RevokedToken)) == 1
            saved = db.scalar(select(RefreshToken))
            assert saved.revoked_at is not None
    finally:
        engine.dispose()


def test_cleanup_preserves_unexpired_revocations(db):
    now = utc_now()
    db.add_all(
        [
            RevokedToken(jti="expired", expires_at=now - timedelta(seconds=1)),
            RevokedToken(jti="boundary", expires_at=now),
            RevokedToken(jti="valid", expires_at=now + timedelta(minutes=5)),
        ]
    )
    db.commit()
    with freeze_time(now):
        assert auth_service.cleanup_expired_tokens(db) == 2
    assert db.get(RevokedToken, "expired") is None
    assert db.get(RevokedToken, "boundary") is None
    assert db.get(RevokedToken, "valid") is not None
