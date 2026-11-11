#!/usr/bin/env python3
"""
Read-only database status for the configured DATABASE_URL (no writes, no DDL).

Reports: reachable?, server version, pgvector installed/enabled?, current Alembic revision.
Credentials are never printed.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.shared.config import settings  # noqa: E402


async def main() -> int:
    url = make_url(settings.DATABASE_URL)
    print(f"target: {url.host}:{url.port}/{url.database} as role '{url.username}'")
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            version = (await conn.execute(text("SHOW server_version"))).scalar()
            print(f"reachable: yes (PostgreSQL {version})")
            available = (await conn.execute(text("SELECT count(*) FROM pg_available_extensions WHERE name='vector'"))).scalar()
            enabled = (await conn.execute(text("SELECT count(*) FROM pg_extension WHERE extname='vector'"))).scalar()
            print(f"pgvector available on server: {'yes' if available else 'NO'}; enabled in this database: {'yes' if enabled else 'no'}")
            has_alembic = (await conn.execute(text("SELECT to_regclass('public.alembic_version') IS NOT NULL"))).scalar()
            if has_alembic:
                rev = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
                print(f"alembic revision: {rev}")
            else:
                print("alembic revision: none (migrations not applied)")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"reachable: NO ({type(exc).__name__}: {str(exc).splitlines()[0][:140]})")
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
