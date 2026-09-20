"""
Asynchronous PostgreSQL Database Engine and Session Management.
Uses SQLAlchemy 2.0 Async with asyncpg and pgvector support.
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
from app.core.config import settings

# Initialize Async Engine with robust pooling and pre-ping
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

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

async def init_db() -> None:
    """
    Initializes database schemas and creates required extensions like pgvector.
    Safe for idempotent startup sequences.
    """
    async with engine.begin() as conn:
        # Enable pgvector extension for dense embedding similarity lookups
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        # Create all registered tables
        await conn.run_sync(Base.metadata.create_all)

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
