"""
Shared fixtures. Persistence tests run against the real isolated Synapse PostgreSQL inside a single
outer transaction that is rolled back, so nothing is left behind. They skip if it is unreachable.
"""
import os
import sys
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend"))
sys.path.insert(0, os.path.join(HERE, ".."))

import app.main  # noqa: E402,F401  (registers every table, incl. ingestion_runs)
from app.shared.config import settings  # noqa: E402

_TABLES = ("leaderboard_scores", "voice_sessions", "outreach_drafts", "lead_embeddings", "job_leads", "raw_posts",
           "benchmark_suites", "code_evaluation_results", "candidate_repos", "ingestion_runs")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def conn():
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        connection = await engine.connect()
        outer = await connection.begin()
        await connection.execute(text("SELECT 1 FROM ingestion_runs"))
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"Synapse database (with migration 003) not available: {type(exc).__name__}")
    for table in _TABLES:   # clean slate *inside* the transaction only; rolled back at the end
        await connection.execute(text(f"DELETE FROM {table}"))
    try:
        yield connection
    finally:
        await outer.rollback()
        await connection.close()
        await engine.dispose()


@pytest.fixture
def session_factory(conn):
    """A callable returning an async context manager that yields a session joined to the test transaction."""

    @asynccontextmanager
    async def factory():
        session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            await session.close()

    return factory


@pytest.fixture
def read(conn):
    """read(sql) -> list of row tuples, inside the test transaction."""

    async def _read(sql: str, **params):
        return (await conn.execute(text(sql), params)).all()

    return _read
