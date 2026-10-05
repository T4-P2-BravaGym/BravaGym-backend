"""Shared test fixtures: an in-memory SQLite database and a test client.

TODO(HU-03): add an auth_headers(role) fixture that returns {"Authorization": "Bearer …"}
for a user with that role, so everyone can test protected endpoints from day 1.
"""
import os

# Settings need a secret; tests use a fake one (set before importing the app).
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, enable_sqlite_foreign_keys, get_db
from app.main import app

test_engine = create_engine(
    "sqlite://",  # in memory
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # one shared connection, so every session sees the same data
)
enable_sqlite_foreign_keys(test_engine)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db():
    """A clean database for every test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db):
    """HTTP client that uses the test database instead of the real one."""
    app.dependency_overrides[get_db] = lambda: db
    # Without "with", the app's startup (create tables in the real file) does not run.
    yield TestClient(app)
    app.dependency_overrides.clear()
