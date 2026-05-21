import asyncio
import os

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from shared.db.models import Base
from shared.db.session import get_db
from apps.api.app import app


TEST_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/test_db",
)

# -------------------------
# ENGINE (function scoped, NOT session scoped)
# -------------------------
@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# -------------------------
# SESSION MAKER
# -------------------------
@pytest_asyncio.fixture
def sessionmaker_fixture(engine):
    return async_sessionmaker(bind=engine, expire_on_commit=False)


# -------------------------
# DB OVERRIDE (IMPORTANT: uses fixture properly)
# -------------------------
@pytest_asyncio.fixture
def override_dependency(sessionmaker_fixture):
    async def override_get_db():
        async with sessionmaker_fixture() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()


# -------------------------
# HTTP CLIENT (must depend on override fixture)
# -------------------------
@pytest_asyncio.fixture
async def client(override_dependency):
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac


# -------------------------
# EVENT LOOP (keep single loop policy clean)
# -------------------------
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()