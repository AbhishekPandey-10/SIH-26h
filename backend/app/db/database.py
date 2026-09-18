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
        from sqlalchemy import text
        for col_def in [
            "ALTER TABLE red_flag_events ADD COLUMN acknowledged_by VARCHAR(64)",
            "ALTER TABLE red_flag_events ADD COLUMN action_taken TEXT",
            "ALTER TABLE red_flag_events ADD COLUMN is_acknowledged BOOLEAN DEFAULT 0",
            "ALTER TABLE sessions ADD COLUMN caregiver_name VARCHAR(128)",
            "ALTER TABLE sessions ADD COLUMN caregiver_relationship VARCHAR(64)",
            "ALTER TABLE sessions ADD COLUMN caregiver_phone VARCHAR(16)",
            "ALTER TABLE sessions ADD COLUMN voice_only_mode BOOLEAN DEFAULT 0",
            "ALTER TABLE sessions ADD COLUMN body_map_selections JSON",
            "ALTER TABLE sessions ADD COLUMN interview_mode VARCHAR(32) DEFAULT 'allopathic'",
            "ALTER TABLE sessions ADD COLUMN prakriti_result JSON",
            "ALTER TABLE interview_transcripts ADD COLUMN is_proxy BOOLEAN DEFAULT 0",
            "ALTER TABLE interview_transcripts ADD COLUMN proxy_name VARCHAR(128)",
            "ALTER TABLE interview_transcripts ADD COLUMN proxy_relationship VARCHAR(64)",
            "ALTER TABLE summaries ADD COLUMN lens VARCHAR(32) DEFAULT 'allopathic'",
            "ALTER TABLE summaries ADD COLUMN ayush_json JSON",
        ]:
            try:
                await conn.execute(text(col_def))
            except Exception:
                pass
    logger.info("Dev 1 tables initialized in database.")
