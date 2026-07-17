"""Async SQLAlchemy engine and session factory.

All direct DB access (chat CRUD, retrieval queries) imports ``AsyncSession``
from here.  The Supabase REST client is *not* used for these operations — raw
SQL through psycopg3 is faster and lets us write the hybrid-search queries we
need later.

The engine is created once at module import time.  ``get_session`` is a
FastAPI dependency that yields a transactional session and commits on success
or rolls back on error.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# psycopg3 async driver — swap postgresql:// → postgresql+psycopg://
_db_url = settings.database_url.replace(
    "postgresql://", "postgresql+psycopg://", 1
).replace(
    "postgres://", "postgresql+psycopg://", 1
)

engine = create_async_engine(
    _db_url,
    pool_pre_ping=True,   # detect stale connections before use
    pool_size=5,
    max_overflow=10,
)

_SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an open session, commits on exit."""
    async with _SessionFactory() as session:
        async with session.begin():
            yield session
