import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
