"""
Database Engine & Async Session Management
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models import Base

logger = logging.getLogger("medikiosk.db")

# Expected Alembic head — update when new migrations are added
EXPECTED_ALEMBIC_HEAD = "003_reconcile_schema"

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

# Enable SQLite foreign key enforcement on every connection
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable FK enforcement for SQLite connections."""
    if "sqlite" in db_url:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
async_session_maker = async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# Schema readiness state — set by verify_schema_ready()
_schema_ready: bool = False
_schema_error: str | None = None


async def verify_schema_ready() -> None:
    """
    Verify that the database schema is at the expected Alembic migration head.
    Raises RuntimeError if migrations haven't been applied or schema is out of date.

    This replaces the old init_db() which used create_all + ALTER TABLE patching.
    """
    global _schema_ready, _schema_error
    try:
        async with engine.connect() as conn:
            # Check if alembic_version table exists
            if "sqlite" in db_url:
                result = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
                )
            else:
                result = await conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE tablename='alembic_version'")
                )
            if result.scalar_one_or_none() is None:
                _schema_error = (
                    "Database has no alembic_version table. "
                    "Run 'alembic upgrade head' before starting the application."
                )
                raise RuntimeError(_schema_error)

            # Check current head matches expected
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            current_heads = [row[0] for row in result.fetchall()]

            if not current_heads:
                _schema_error = (
                    "alembic_version table is empty — no migrations applied. "
                    "Run 'alembic upgrade head'."
                )
                raise RuntimeError(_schema_error)

            if EXPECTED_ALEMBIC_HEAD not in current_heads:
                _schema_error = (
                    f"Schema version mismatch: expected '{EXPECTED_ALEMBIC_HEAD}', "
                    f"found {current_heads}. Run 'alembic upgrade head'."
                )
                raise RuntimeError(_schema_error)

        _schema_ready = True
        _schema_error = None
        logger.info(f"Schema verified at migration head: {EXPECTED_ALEMBIC_HEAD}")
    except RuntimeError:
        _schema_ready = False
        raise
    except Exception as e:
        _schema_error = f"Schema verification failed: {e}"
        _schema_ready = False
        raise RuntimeError(_schema_error) from e


def is_schema_ready() -> bool:
    """Return whether schema verification passed."""
    return _schema_ready


def get_schema_error() -> str | None:
    """Return the schema error message if verification failed."""
    return _schema_error


async def init_db() -> None:
    """
    Legacy init_db — replaced by verify_schema_ready() for production.
    Kept for backward compat during dev/testing transition.
    Delegates to verify_schema_ready().
    """
    await verify_schema_ready()


async def init_db_for_testing(test_engine=None) -> None:
    """
    Create all tables from ORM metadata for isolated test databases.
    Only use with disposable in-memory or temporary SQLite databases.
    """
    target = test_engine or engine
    async with target.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _reconcile_sqlite_columns(connection):
            res = connection.exec_driver_sql("PRAGMA table_info(fhir_push_queue)").fetchall()
            existing_cols = {row[1] for row in res}
            if existing_cols and "idempotency_key" not in existing_cols:
                cols_to_add = [
                    ("idempotency_key", "VARCHAR(128)"),
                    ("patient_abha_id", "VARCHAR(64)"),
                    ("summary_version", "INTEGER DEFAULT 1"),
                    ("affirmed_by_doctor_id", "VARCHAR(64)"),
                    ("max_retry_count", "INTEGER DEFAULT 5"),
                    ("attempt_history", "JSON"),
                    ("locked_at", "DATETIME"),
                    ("locked_by", "VARCHAR(64)"),
                    ("delivered_at", "DATETIME"),
                    ("abdm_transaction_id", "VARCHAR(128)"),
                    ("consent_verified_at", "DATETIME"),
                ]
                for col_name, col_type in cols_to_add:
                    if col_name not in existing_cols:
                        try:
                            connection.exec_driver_sql(f"ALTER TABLE fhir_push_queue ADD COLUMN {col_name} {col_type}")
                        except Exception:
                            pass
                try:
                    connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_fhir_push_idempotency ON fhir_push_queue (idempotency_key)")
                except Exception:
                    pass

        await conn.run_sync(_reconcile_sqlite_columns)
    logger.info("Test database tables created from ORM metadata.")
