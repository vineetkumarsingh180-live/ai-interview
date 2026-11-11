"""
Asynchronous PostgreSQL Database Engine and Session Management.
Uses SQLAlchemy 2.0 Async with asyncpg. The schema is managed by Alembic migrations.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.shared.config import settings

# Initialize Async Engine with robust pooling and pre-ping
_db_url = settings.DATABASE_URL
_engine_kwargs = {"echo": False, "future": True}

if _db_url.startswith("sqlite"):
    if not _db_url.startswith("sqlite+aiosqlite"):
        _db_url = _db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
else:
    _engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 5,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })

engine: AsyncEngine = create_async_engine(_db_url, **_engine_kwargs)

# Async sessionmaker producing non-blocking AsyncSession instances
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Declarative Base for all Domain ORM models
class Base(DeclarativeBase):
    pass

async def check_database() -> bool:
    """Connectivity probe. Schema is owned by Alembic (`alembic upgrade head`), never created here."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an asynchronous database session.
    Guarantees session closure and automatic transaction cleanup.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
