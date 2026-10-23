import os
import sys
import tempfile

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BACKEND, "bot"))
sys.path.insert(0, BACKEND)

# The bot writes logs under DATA_DIR at import time; keep tests out of /data.
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="applier-test-data-"))
os.environ.pop("APPLIER_CONFIG_FILE", None)
os.environ.pop("APPLIER_DATABASE_URL", None)
os.environ.pop("APPLIER_RUN_ID", None)

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("UI_PASSWORD", "test-password")
os.environ.setdefault("SESSION_SECRET", "test-session-secret-" + "x" * 32)


@pytest.fixture(scope="session")
def engine():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set (`make test` sets it)")
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    eng = create_engine(TEST_DATABASE_URL)
    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    cfg = Config(os.path.join(BACKEND, "alembic.ini"))
    cfg.attributes["configure_logger"] = False
    cfg.set_main_option("script_location", os.path.join(BACKEND, "migrations"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(cfg, "head")
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    """A session whose work is rolled back after the test (commits become savepoints)."""
    from sqlalchemy.orm import Session

    conn = engine.connect()
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    yield session
    session.close()
    outer.rollback()
    conn.close()


@pytest.fixture
def committed_db(engine):
    """Real commits, for tests where another process or thread reads the data."""
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    from app.models import Base

    session = Session(bind=engine, expire_on_commit=False)
    yield session
    session.close()
    with engine.begin() as conn:
        tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        conn.execute(text("INSERT INTO bot_control (id, desired) VALUES (1, 'stopped')"))
        conn.execute(text("INSERT INTO linkedin_session (id, state) VALUES (1, 'unknown')"))
