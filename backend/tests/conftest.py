"""
conftest.py — Pytest fixtures and test environment setup.
"""
import asyncio
import os
import sys
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# Ensure backend is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Environment — set BEFORE importing app
# ---------------------------------------------------------------------------
TEST_API_KEY = "test-secret-api-key-12345"
os.environ["APP_API_KEY"] = TEST_API_KEY
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# ---------------------------------------------------------------------------
# In-memory async SQLite engine
# ---------------------------------------------------------------------------
_test_engine: AsyncEngine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)

_test_session_factory = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Patch the app's database module globals
from core import database
database.engine = _test_engine
database.AsyncSessionLocal = _test_session_factory


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """A fresh async DB session per test — all changes auto-rollback."""
    from models.execution import Base

    # Create tables in-memory
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with _test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # Drop tables after each test
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def db_session_without_commit() -> AsyncGenerator[AsyncSession, None]:
    """DB session without auto-commit for tests that need explicit control."""
    from models.execution import Base

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with _test_session_factory() as session:
        yield session

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Patch get_db to use test session
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
async def app(db_session: AsyncSession):
    """FastAPI app with patched database dependency."""
    from core.database import get_db

    async def _override_get_db():
        yield db_session

    # Import app after env vars are set
    from main import app as fastapi_app

    fastapi_app.dependency_overrides[get_db] = _override_get_db

    yield fastapi_app

    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": TEST_API_KEY},
    ) as ac:
        yield ac


@pytest.fixture(scope="function")
async def unauthenticated_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client without API key header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture(scope="function")
async def wrong_auth_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with wrong API key header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": "wrong-key-xyz"},
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_agent_data() -> dict:
    return {
        "name": "Test Agent",
        "description": "A test agent for unit tests",
        "model_provider": "minimax",
        "model_name": "MiniMax-M2.7",
        "system_prompt": "You are a helpful test agent.",
        "tools": [{"name": "test_tool", "description": "A test tool", "parameters": {}}],
        "config": {"temperature": 0.5},
    }


@pytest.fixture
def sample_workflow_data() -> dict:
    return {
        "name": "Test Workflow",
        "description": "A test workflow",
        "agent_ids": [],
        "config": {},
    }


@pytest.fixture
def sample_task_data() -> dict:
    return {
        "title": "Test Task",
        "description": "A test task",
        "workflow_id": "placeholder-workflow-id",
        "agent_id": "placeholder-agent-id",
        "input_data": {"query": "test query"},
        "priority": 5,
        "dependencies": [],
    }


# ---------------------------------------------------------------------------
# Mock LLM provider — prevents real API calls in executor tests
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_llm_response():
    """Returns a mock LLM response object."""
    mock_response = MagicMock()
    mock_response.content = '{"result": "Mock LLM response", "status": "success"}'
    return mock_response


@pytest.fixture
def mock_provider(mock_llm_response):
    """Patches the LLM provider so no real calls are made."""
    with patch("agents.executor.AgentExecutor._get_llm") as mock_get_llm:
        mock_provider_instance = AsyncMock()
        mock_provider_instance.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_provider_instance
        yield mock_get_llm


# ---------------------------------------------------------------------------
# Mock task queue — prevents real queue processing
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_task_queue():
    """Patches task_queue.enqueue to avoid real async processing."""
    with patch("agents.queue.task_queue") as mock_queue:
        mock_queue.enqueue = AsyncMock(return_value="mock-task-id-123")
        mock_queue.get_task = MagicMock(return_value=None)
        mock_queue.subscribe = MagicMock()
        mock_queue.unsubscribe = MagicMock()
        mock_queue.get_task_events = AsyncMock(return_value=[])
        yield mock_queue


# ---------------------------------------------------------------------------
# Mock db engine for health check tests
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_db_failure():
    """Patches the database engine to simulate a failure for /ready tests."""
    with patch("core.database.engine") as mock_engine:
        mock_engine.connect = AsyncMock(
            side_effect=Exception("Simulated DB connection failure")
        )
        yield mock_engine
