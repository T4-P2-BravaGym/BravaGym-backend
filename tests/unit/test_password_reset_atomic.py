from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from hashlib import sha256
from threading import Barrier

import pytest
from app.core.database import Base, enable_sqlite_foreign_keys
from app.core.exceptions import AppError
from app.core.security import verify_password
from app.models import PasswordResetToken, Role, User
from app.models.enums import RoleName
from app.models.types import utc_now
from app.services import auth_service, password_reset_service
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


def test_failed_confirmation_rolls_back_password_token_and_version(
    db, make_user, monkeypatch
):
    user = make_user()
    token = PasswordResetToken(
        user_id=user.id,
        token_hash=sha256(b"demo-reset-token").hexdigest(),
        expires_at=utc_now() + timedelta(minutes=30),
    )
    db.add(token)
    db.commit()
    old_hash = user.password_hash

    def fail():
        raise RuntimeError("simulated database error")

    monkeypatch.setattr(db, "commit", fail)
    with pytest.raises(RuntimeError):
        password_reset_service.confirm_password_reset(
            db, "demo-reset-token", "NewPassword2026!"
        )
    db.refresh(user)
    db.refresh(token)
    assert user.password_hash == old_hash and user.session_version == 0
    assert token.used_at is None


@pytest.mark.parametrize("race", ["confirm", "refresh"])
def test_concurrent_recovery_is_atomic_and_old_sessions_cannot_survive(tmp_path, race):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'reset-race.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with factory() as db:
            user = User(
                email="demo@example.com",
                first_name="Demo",
                last_name="Test",
                password_hash="not-needed",
                role=Role(name=RoleName.MEMBER),
            )
            db.add(user)
            db.commit()
            old = auth_service.issue_session(db, user)
            db.add(
                PasswordResetToken(
                    user_id=user.id,
                    token_hash=sha256(b"demo-reset-token").hexdigest(),
                    expires_at=utc_now() + timedelta(minutes=30),
                )
            )
            db.commit()
        barrier = Barrier(2)

        def run(operation):
            with factory() as db:
                barrier.wait(timeout=5)
                try:
                    if operation == "refresh":
                        return auth_service.refresh_session(db, old.refresh_token)
                    password_reset_service.confirm_password_reset(
                        db, "demo-reset-token", "NewPassword2026!"
                    )
                    return "reset"
                except AppError:
                    return "rejected"

        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(run, "confirm"), pool.submit(run, race)
            results = [a.result(), b.result()]
        if race == "confirm":
            assert sorted(results) == ["rejected", "reset"]
        else:
            assert results[0] == "reset"
        with factory() as db:
            user = db.scalar(select(User))
            assert user.session_version == 1
            assert verify_password("NewPassword2026!", user.password_hash)
            for result in results:
                if isinstance(result, auth_service.SessionTokens):
                    assert (
                        auth_service.decode_refresh_token(result.refresh_token).get(
                            "ver", 0
                        )
                        < user.session_version
                    )
                    with pytest.raises(AppError):
                        auth_service.refresh_session(db, result.refresh_token)
    finally:
        engine.dispose()
