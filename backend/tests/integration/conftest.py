"""
Integration test configuration and fixtures.
All tests use REAL aiosqlite in-memory database (no mocks for DB).
Only LLM providers are mocked.
"""

import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Must set BEFORE importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["MINIMAX_API_KEY"] = "test-key"
os.environ["APP_API_KEY"] = ""  # Disable API key middleware in tests

from agents.queue import task_queue
from core.database import close_db, engine, init_db
from main import app
from models.execution import Base

# ---------------------------------------------------------------------------
# DB Engine & Session (real in-memory)
# ---------------------------------------------------------------------------
TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
)

TestAsyncSessionLocal = async_sessionmaker(
    TEST_ENGINE,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Share one loop for the whole test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a real aiosqlite in-memory session.
    Each test gets a pristine DB by recreating tables.
    """
    # Create all tables
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Override database dependency so /api/v1/* routes use our test session
# ---------------------------------------------------------------------------
async def override_get_db():
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Mock LLM provider
# ---------------------------------------------------------------------------
class MockLLMProvider:
    """Returns a fixed JSON response without making real API calls."""

    async def ainvoke(self, messages):
        return type("obj", (object,), {"content": '{"result": "mock response", "timestamp": "2026-01-01T00:00:00"}'})()


def _mock_load_provider(**kwargs):
    return MockLLMProvider()


# ---------------------------------------------------------------------------
# AsyncClient – real app, real DB, mocked LLM
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="function")
async def client():
    """
    Provides an AsyncClient wired to the real FastAPI app.
    DB is real in-memory; LLM calls are mocked.
    """
    from agents import providers
    from core.database import get_db

    # Patch the LLM provider loader
    original_load = providers.load_provider_from_agent
    providers.load_provider_from_agent = _mock_load_provider

    # Swap DB dependency
    app.dependency_overrides[get_db] = override_get_db

    # Ensure task_queue is running (don't start real workers)
    task_queue._running = True

    # Re-init DB so tables exist
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Restore
    providers.load_provider_from_agent = original_load
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper factories (real DB, no mocking)
# ---------------------------------------------------------------------------
async def create_agent(db: AsyncSession, **overrides):
    from models.execution import AgentModel

    agent = AgentModel(
        name=overrides.get("name", "Test Agent"),
        description=overrides.get("description", "A test agent"),
        model_provider=overrides.get("model_provider", "minimax"),
        model_name=overrides.get("model_name", "MiniMax-M2.7"),
        system_prompt=overrides.get("system_prompt", "You are a helpful assistant."),
        tools=overrides.get("tools", []),
        config=overrides.get("config", {}),
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def create_workflow(db: AsyncSession, **overrides):
    from models.execution import WorkflowModel

    workflow = WorkflowModel(
        name=overrides.get("name", "Test Workflow"),
        description=overrides.get("description", "A test workflow"),
        agent_ids=overrides.get("agent_ids", []),
        config=overrides.get("config", {}),
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return workflow


async def create_task(db: AsyncSession, **overrides):
    from models.execution import TaskModel

    task = TaskModel(
        workflow_id=overrides["workflow_id"],
        agent_id=overrides["agent_id"],
        title=overrides.get("title", "Test Task"),
        description=overrides.get("description"),
        input_data=overrides.get("input_data", {}),
        priority=overrides.get("priority", 0),
        dependencies=overrides.get("dependencies", []),
        status=overrides.get("status", "pending"),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@pytest.fixture
async def make_agent(client: AsyncClient):
    """Factory fixture: POST /api/v1/agents and return the created agent."""

    async def _make(**kwargs):
        payload = {
            "name": kwargs.get("name", "Test Agent"),
            "description": kwargs.get("description", "Test description"),
            "model_provider": kwargs.get("model_provider", "minimax"),
            "model_name": kwargs.get("model_name", "MiniMax-M2.7"),
            "system_prompt": kwargs.get("system_prompt", "You are helpful."),
            "tools": kwargs.get("tools", []),
            "config": kwargs.get("config", {}),
        }
        resp = await client.post("/api/v1/agents", json=payload)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest.fixture
async def make_workflow(client: AsyncClient):
    """Factory fixture: POST /api/v1/workflows and return the created workflow."""

    async def _make(**kwargs):
        payload = {
            "name": kwargs.get("name", "Test Workflow"),
            "description": kwargs.get("description", "Test description"),
            "agent_ids": kwargs.get("agent_ids", []),
            "config": kwargs.get("config", {}),
        }
        resp = await client.post("/api/v1/workflows", json=payload)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make
