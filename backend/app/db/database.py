"""
Database Engine & Async Session Management
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models import Base

logger = logging.getLogger("medikiosk.db")

# Determine DB URL
if settings.USE_SQLITE_FALLBACK and "sqlite" in settings.DATABASE_URL:
    db_url = settings.DATABASE_URL
elif settings.USE_SQLITE_FALLBACK and "localhost" in settings.DATABASE_URL:
    # Use SQLite for local offline testing if requested
    db_url = f"sqlite+aiosqlite:///{settings.SQLITE_DB_PATH}"
else:
    db_url = settings.DATABASE_URL

engine = create_async_engine(
    db_url,
    echo=False,
    future=True
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create tables if they don't exist (useful for testing and dev)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Dev 1 tables initialized in database.")
