import os
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

# Disable API key auth for tests
os.environ["APP_API_KEY"] = ""


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def setup_db():
    """Initialize fresh DB for each test."""
    from core.database import init_db, close_db
    await init_db()
    yield
    await close_db()


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Multi-Agent Orchestrator"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_agents_crud(client):
    # Create agent
    resp = await client.post("/api/v1/agents", json={
        "name": "Test Agent",
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "system_prompt": "You are a helpful assistant.",
        "tools": [],
        "config": {}
    })
    assert resp.status_code == 201
    agent = resp.json()
    assert agent["name"] == "Test Agent"
    agent_id = agent["id"]

    # List agents
    resp = await client.get("/api/v1/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) == 1
    assert agents[0]["id"] == agent_id

    # Get single agent
    resp = await client.get(f"/api/v1/agents/{agent_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == agent_id

    # Update agent
    resp = await client.put(f"/api/v1/agents/{agent_id}", json={
        "name": "Updated Agent"
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Agent"

    # Delete agent
    resp = await client.delete(f"/api/v1/agents/{agent_id}")
    assert resp.status_code == 204

    # Verify deleted
    resp = await client.get(f"/api/v1/agents/{agent_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_workflows_crud(client):
    # Create workflow
    resp = await client.post("/api/v1/workflows", json={
        "name": "Test Workflow",
        "description": "Test description",
        "agent_ids": [],
        "config": {}
    })
    assert resp.status_code == 201
    wf = resp.json()
    assert wf["name"] == "Test Workflow"
    wf_id = wf["id"]

    # List workflows
    resp = await client.get("/api/v1/workflows")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Get single workflow
    resp = await client.get(f"/api/v1/workflows/{wf_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == wf_id

    # Update workflow
    resp = await client.put(f"/api/v1/workflows/{wf_id}", json={
        "name": "Updated Workflow"
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Workflow"

    # Delete workflow
    resp = await client.delete(f"/api/v1/workflows/{wf_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_task_requires_valid_agent(client):
    # Create task without agent
    resp = await client.post("/api/v1/tasks", json={
        "workflow_id": "nonexistent",
        "agent_id": "nonexistent",
        "title": "Test Task",
        "input_data": {},
        "priority": 0,
        "dependencies": []
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_execution_stats(client):
    resp = await client.get("/api/v1/execution/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_agents" in data
    assert "total_workflows" in data
    assert "total_tasks" in data