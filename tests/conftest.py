import os
from pathlib import Path

# Ensure required environment variables exist before importing the app/settings.
_TEST_DB_PATH = Path(__file__).resolve().parent / "test.sqlite"
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TEST_DB_PATH}")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("EMAIL_HOST", "smtp.example.com")
os.environ.setdefault("EMAIL_PORT", "587")
os.environ.setdefault("EMAIL_USER", "test@example.com")
os.environ.setdefault("EMAIL_PASSWORD", "test")
os.environ.setdefault("EMAIL_FROM", "Test <test@example.com>")
os.environ.setdefault("STRIPE_API_KEY", "sk_test_xxx")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_xxx")
os.environ.setdefault("PAYPAL_CLIENT_ID", "test")
os.environ.setdefault("PAYPAL_CLIENT_SECRET", "test")
os.environ.setdefault("PAYPAL_WEBHOOK_ID", "test")

import pytest
from sqlalchemy import text

from app.core.database import AsyncSessionLocal, Base, engine
from app.core.events import event_dispatcher

# Import models so Base.metadata includes all needed tables for tests.
from app.modules.auth import models as _auth_models  # noqa: F401
from app.modules.couriers import models as _courier_models  # noqa: F401
from app.modules.orders import models as _order_models  # noqa: F401
from app.modules.stores import models as _store_models  # noqa: F401
from app.modules.notifications import models as _notification_models  # noqa: F401


@pytest.fixture(scope="session", autouse=True)
async def _create_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        # Clean up tables between tests (SQLite).
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(text(f'DELETE FROM "{table.name}"'))
        await session.commit()
        yield session


@pytest.fixture(autouse=True)
def _disable_event_dispatch_for_sqlite_tests(monkeypatch):
    async def _noop_dispatch(*args, **kwargs):
        return None

    monkeypatch.setattr(event_dispatcher, "dispatch", _noop_dispatch)
