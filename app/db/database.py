from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database_if_missing():
    database_url = settings.database_url

    target_db = database_url.rsplit("/", 1)[-1]
    admin_url = database_url.rsplit("/", 1)[0] + "/postgres"

    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": target_db},
        ).fetchone()

        if not exists:
            conn.execute(text(f'CREATE DATABASE "{target_db}"'))

