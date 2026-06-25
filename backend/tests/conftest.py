from unittest.mock import AsyncMock, patch

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture
async def db_session():
    from app.db.session import async_session_factory

    async with async_session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
def bypass_upload_rate_limit():
    with patch(
        "app.api.v1.documents.enforce_upload_rate_limit",
        new_callable=AsyncMock,
    ):
        yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
