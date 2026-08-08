import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

# SQLite does not support JSONB; swap it for generic JSON before any model imports.
from sqlalchemy import JSON
import sqlalchemy.dialects.postgresql as _pg_dialect
_pg_dialect.JSONB = JSON  # type: ignore[attr-defined]

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Patch out the PostgreSQL-only helper before the app is imported.
import app.db.database as _db_module

_db_module.create_database_if_missing = lambda: None

from app.db.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
