"""
Offline drift guard: replaying the whole Alembic history as SQL must produce exactly the tables,
columns, nullability and indexes the ORM models declare. Needs no database.
"""
import io
import os
import re

from alembic import command
from alembic.config import Config

from app.main import app  # noqa: F401  (imports every module so their tables register)
from app.shared.database import Base

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _offline_sql() -> str:
    cfg = Config(os.path.join(BACKEND, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND, "alembic"))
    buf = io.StringIO()
    cfg.output_buffer = buf
    command.upgrade(cfg, "head", sql=True)
    return buf.getvalue()


def _replay(sql: str):
    """Returns ({table: {column: nullable}}, {index names}) after applying every statement."""
    tables, indexes = {}, set()
    for m in re.finditer(r"CREATE TABLE (\w+) \((.*?)\n\)", sql, re.S):
        cols = {}
        for line in m.group(2).splitlines():
            line = line.strip().rstrip(",")
            if not line or line.startswith(("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CONSTRAINT", "CHECK")):
                continue
            cols[line.split()[0]] = "NOT NULL" not in line
        tables[m.group(1)] = cols
    tables.pop("alembic_version", None)

    for stmt in re.split(r";\s*\n", sql):
        stmt = " ".join(l for l in stmt.splitlines() if not l.strip().startswith("--"))
        stmt = " ".join(stmt.split())
        if m := re.match(r"CREATE (?:UNIQUE )?INDEX (\w+) ON", stmt):
            indexes.add(m.group(1))
        elif m := re.match(r"DROP INDEX (\w+)", stmt):
            indexes.discard(m.group(1))
        elif m := re.match(r"ALTER TABLE (\w+) ADD COLUMN (\w+) .*", stmt):
            tables[m.group(1)][m.group(2)] = "NOT NULL" not in stmt
        elif m := re.match(r"ALTER TABLE (\w+) DROP COLUMN (\w+)", stmt):
            tables[m.group(1)].pop(m.group(2))
        elif m := re.match(r"ALTER TABLE (\w+) ALTER COLUMN (\w+) DROP NOT NULL", stmt):
            tables[m.group(1)][m.group(2)] = True
        elif m := re.match(r"ALTER TABLE (\w+) ALTER COLUMN (\w+) SET NOT NULL", stmt):
            tables[m.group(1)][m.group(2)] = False
    return tables, indexes


def test_migration_history_matches_models_tables_columns_and_nullability():
    tables, _ = _replay(_offline_sql())
    expected = {t.name: {c.name: bool(c.nullable) for c in t.columns} for t in Base.metadata.tables.values()}
    assert set(tables) == set(expected), set(tables) ^ set(expected)
    for name in expected:
        assert set(tables[name]) == set(expected[name]), f"column drift in {name}: {set(tables[name]) ^ set(expected[name])}"
        for col, nullable in expected[name].items():
            if not expected[name][col] and col == "id":
                continue  # primary keys
            assert tables[name][col] == nullable or col == "id", f"nullability drift {name}.{col}: db={tables[name][col]} model={nullable}"


def test_migration_history_matches_model_indexes():
    _, indexes = _replay(_offline_sql())
    expected = {i.name for t in Base.metadata.tables.values() for i in t.indexes}
    assert indexes == expected, indexes ^ expected


def test_migrations_enable_pgvector_and_use_the_vector_type():
    sql = _offline_sql()
    assert "CREATE EXTENSION IF NOT EXISTS vector" in sql
    assert re.search(r"embedding VECTOR\(768\)", sql)
