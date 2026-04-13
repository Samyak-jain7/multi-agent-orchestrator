"""
pytest fixtures: in-memory SQLite, AsyncClient, sample data, mocked LLM.
"""
import asyncio
import os
from datetime import datetime
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

os.environ["APP_API_KEY"] = "test-api-key"
os.environ["LOG_LEVEL"] = "DEBUG"

from models.execution import Base

# ---------------------------------------------------------------------------
# Shared in-memory SQLite with file backing (so all connections share schema)
# ---------------------------------------------------------------------------
TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true",
    echo=False,
    connect_args={"check_same_thread": False, "uri": True},
)

TEST_SESSION_FACTORY = async_sessionmaker(
    TEST_ENGINE,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Create schema once at module load
import inspect
_sentinel = object()
_last_create = [_sentinel]


async def _ensure_tables():
    """Create all tables. Idempotent – only runs once."""
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Run table creation now
asyncio.get_event_loop().run_until_complete(_ensure_tables())


# ---------------------------------------------------------------------------
# Per-test cleanup: truncate all data (keep schema)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function", autouse=True)
async def _cleanup_db():
    """Delete all rows from every table after each test."""
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------------------------------------------------------------------------
# DB session fixture
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TEST_SESSION_FACTORY() as session:
        yield session


# ---------------------------------------------------------------------------
# App + client fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
async def app():
    from main import app as fastapi_app
    from core.database import get_db

    async def _override():
        async with TEST_SESSION_FACTORY() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = _override
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-api-key"},
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Auth header fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def auth_headers() -> dict:
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def no_auth_headers() -> dict:
    return {}


@pytest.fixture
def wrong_auth_headers() -> dict:
    return {"X-API-Key": "wrong-key"}


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_agent_data() -> dict:
    return {
        "name": "Test Agent",
        "description": "A test agent",
        "model_provider": "minimax",
        "model_name": "MiniMax-M2.7",
        "system_prompt": "You are a helpful assistant.",
        "tools": [{"name": "web_search", "description": "Search the web", "parameters": {}}],
        "config": {"temperature": 0.7},
    }


@pytest.fixture
async def sample_agent(db_session) -> dict:
    from models.execution import AgentModel

    agent = AgentModel(
        name="Sample Agent",
        description="A sample agent",
        model_provider="minimax",
        model_name="MiniMax-M2.7",
        system_prompt="You are a sample agent.",
        tools=[{"name": "web_search", "description": "Search the web", "parameters": {}}],
        config={"temperature": 0.7},
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


@pytest.fixture
async def sample_workflow(db_session) -> dict:
    from models.execution import WorkflowModel

    workflow = WorkflowModel(
        name="Sample Workflow",
        description="A sample workflow",
        agent_ids=[],
        config={},
    )
    db_session.add(workflow)
    await db_session.commit()
    await db_session.refresh(workflow)
    return workflow


@pytest.fixture
async def sample_task(db_session, sample_agent) -> dict:
    from models.execution import TaskModel

    task = TaskModel(
        workflow_id="test-workflow-id",
        agent_id=sample_agent.id,
        title="Sample Task",
        description="A sample task",
        input_data={"query": "hello"},
        status="pending",
        priority=0,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


# ---------------------------------------------------------------------------
# Mock LLM provider
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_llm():
    mock_response = MagicMock()
    mock_response.content = '{"result": "mocked response", "timestamp": "2026-01-01T00:00:00"}'

    mock_provider = AsyncMock()
    mock_provider.ainvoke = AsyncMock(return_value=mock_response)

    with patch("agents.providers.load_provider_from_agent", return_value=mock_provider):
        yield mock_provider


# ---------------------------------------------------------------------------
# Task queue mock fixture
# ---------------------------------------------------------------------------
@pytest.fixture
async def mock_task_queue():
    from agents.queue import TaskQueue, QueuedTask
    import uuid

    queue = TaskQueue(max_concurrent=10)
    task_store = {}

    async def mock_enqueue(task_type: str, payload: dict) -> str:
        task_id = str(uuid.uuid4())
        task = QueuedTask(task_id=task_id, task_type=task_type, payload=payload)
        task_store[task_id] = task
        return task_id

    async def mock_start():
        queue._running = True

    async def mock_stop():
        queue._running = False

    queue.enqueue = mock_enqueue
    queue.start = mock_start
    queue.stop = mock_stop
    queue.get_task = lambda tid: task_store.get(tid)
    queue._tasks = task_store
    queue._subscribers = {}

    with patch("agents.queue.task_queue", queue):
        yield queue
