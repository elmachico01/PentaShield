"""
Synchronous SQLAlchemy session for Celery workers.

Celery tasks are synchronous; we use psycopg2 instead of asyncpg here.
The DATABASE_URL env var uses +asyncpg — we swap the driver at runtime.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.config import get_settings


def _sync_url(async_url: str) -> str:
    return async_url.replace("+asyncpg", "+psycopg2", 1)


_engine = create_engine(
    _sync_url(get_settings().database_url),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SyncSessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_sync_db() -> Session:
    return SyncSessionLocal()
