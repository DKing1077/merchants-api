import hashlib
import os
import uuid

_TEST_DATABASE_URL = "sqlite:///:memory:"
os.environ.setdefault("DATABASE_URL", _TEST_DATABASE_URL)

from sqlalchemy import JSON, create_engine
import sqlalchemy.dialects.postgresql as _pg_dialect

_pg_dialect.JSONB = JSON  # type: ignore[attr-defined]

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.database as _db_module

_db_module.create_database_if_missing = lambda: None

from app.db.database import Base, get_db
from app.db.models import ApiKey
from app.main import app

engine = create_engine(
    _TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
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
def auth_headers() -> dict[str, str]:
    return {"Authorization": "test-key"}


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"Authorization": "admin-key"}


@pytest.fixture
def client(auth_headers, admin_headers):
    db = TestingSessionLocal()
    try:
        for raw_key, is_admin in ((auth_headers["Authorization"], False), (admin_headers["Authorization"], True)):
            db.add(
                ApiKey(
                    id=str(uuid.uuid4()),
                    key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
                    merchant_id="merchant_1",
                    is_active=True,
                    is_admin=is_admin,
                )
            )
        db.commit()
    finally:
        db.close()

    test_client = TestClient(app)
    test_client.headers.update(auth_headers)
    return test_client


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
