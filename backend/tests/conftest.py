"""Pytest fixtures for backend integration tests."""

import base64
import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

os.environ.setdefault("USE_MOCK_GMAIL", "true")
os.environ.setdefault(
    "TOKEN_ENCRYPTION_KEY",
    base64.b64encode(b"0" * 32).decode(),
)
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_minimum_32_chars_long")
os.environ.setdefault("UNSUBSCRIBE_SECRET", "test_unsubscribe_secret_key_32ch")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://outreach:outreach@localhost:5432/outreach_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")

import app.models  # noqa: F401

from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.models.user import User
from app.services.auth_service import AuthService

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    auth = AuthService(db_session)
    user = await auth.register(
        email=f"test_{uuid4().hex[:8]}@example.com",
        password="TestPass1",
        full_name="Test User",
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: User) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "TestPass1"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
