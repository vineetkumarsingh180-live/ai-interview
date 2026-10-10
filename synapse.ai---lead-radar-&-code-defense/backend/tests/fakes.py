"""Test doubles shared by the backend tests (no PostgreSQL needed)."""
import uuid
from types import SimpleNamespace


class FakeResult:
    def __init__(self, value=None, rows=None):
        self._value, self._rows = value, rows or []

    def scalar_one_or_none(self):
        return self._value

    def scalar(self):
        return self._value if self._value is not None else 0

    def scalars(self):
        return SimpleNamespace(all=lambda: list(self._rows))


class FakeDb:
    """Just enough of AsyncSession for the services under test."""

    def __init__(self, objects=None):
        self.objects = objects or {}
        self.added = []
        self.commits = 0

    async def get(self, model, key):
        return self.objects.get((model, key))

    async def execute(self, _stmt):
        return FakeResult(None)

    def add(self, obj):
        self.added.append(obj)

    @staticmethod
    def _apply_defaults(obj):
        for col in obj.__table__.columns:
            if getattr(obj, col.name, None) is None and col.default is not None:
                arg = col.default.arg
                setattr(obj, col.name, arg(None) if callable(arg) else arg)

    async def flush(self):
        for obj in self.added:
            self._apply_defaults(obj)

    async def rollback(self):
        pass

    async def commit(self):
        for obj in self.added:
            self._apply_defaults(obj)
        self.commits += 1

    async def refresh(self, obj):
        self._apply_defaults(obj)
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()

    async def close(self):
        pass


def install_db(app, db):
    """Override FastAPI's DB dependency with `db`; returns a callable that removes the override."""
    from app.shared.database import get_db

    async def override():
        yield db

    app.dependency_overrides[get_db] = override
    return lambda: app.dependency_overrides.pop(get_db, None)
