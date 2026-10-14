from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app import models  # noqa: F401
from app.core.database import Base

ROOT = Path(__file__).resolve().parents[2]


def test_migrations_match_the_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", url)

    command.upgrade(config, "head")

    engine = create_engine(url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []