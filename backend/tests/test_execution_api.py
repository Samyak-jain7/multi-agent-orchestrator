"""
Tests for /api/v1/execution endpoints.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

# ---------------------------------------------------------------------------
# GET /api/v1/execution/stats
# ---------------------------------------------------------------------------

async def test_get_stats_empty_db(client: AsyncClient):
    response = await client.get("/api/v1/execution/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_agents" in data
    assert "total_workflows" in data
    assert "total_tasks" in data
    assert "active_workflows" in data
    assert "completed_tasks_today" in data
    assert "failed_tasks_today" in data
    assert "success_rate" in data
    assert data["total_agents"] == 0
    assert data["total_workflows"] == 0
    assert data["total_tasks"] == 0


async def test_get_stats_with_data(
    client: AsyncClient, sample_agent_data, sample_workflow_data, sample_task_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )

    response = await client.get("/api/v1/execution/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_agents"] == 1
    assert data["total_workflows"] == 1
    assert data["total_tasks"] == 1


async def test_get_stats_success_rate_calculation(
    client: AsyncClient, sample_agent_data, sample_workflow_data, sample_task_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    t1_resp = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    t1_id = t1_resp.json()["id"]
    await client.put(f"/api/v1/tasks/{t1_id}", json={"status": "completed"})

    t2_resp = await client.post(
        "/api/v1/tasks",
        json={
            **sample_task_data,
            "title": "Failed Task",
            "workflow_id": workflow_id,
            "agent_id": agent_id,
        },
    )
    t2_id = t2_resp.json()["id"]
    await client.put(f"/api/v1/tasks/{t2_id}", json={"status": "failed"})

    response = await client.get("/api/v1/execution/stats")
    data = response.json()
    assert data["success_rate"] == 0.5


# ---------------------------------------------------------------------------
# GET /api/v1/execution/task/{id}/status
# ---------------------------------------------------------------------------

async def test_get_task_status_from_queue(client: AsyncClient, mock_task_queue):
    mock_task_queue.get_task.return_value = None
    response = await client.get("/api/v1/execution/task/nonexistent-id/status")
    assert response.status_code == 404


async def test_get_task_status_not_found_anywhere(client: AsyncClient, mock_task_queue):
    mock_task_queue.get_task.return_value = None
    response = await client.get("/api/v1/execution/task/nonexistent-id/status")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/execution/task/{id}/events
# ---------------------------------------------------------------------------

async def test_get_task_events_empty(client: AsyncClient, mock_task_queue):
    mock_task_queue.get_task_events.return_value = []
    response = await client.get("/api/v1/execution/task/some-task-id/events")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert "count" in data


async def test_get_task_events_with_after_index(client: AsyncClient):
    with patch("api.execution.task_queue.get_task_events", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        response = await client.get("/api/v1/execution/task/some-id/events?after_index=5")
        assert response.status_code == 200
        mock_get.assert_called_with("some-id", 5)


# ---------------------------------------------------------------------------
# POST /api/v1/execution/log
# ---------------------------------------------------------------------------

async def test_create_execution_log_happy_path(client: AsyncClient, sample_workflow_data):
    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    response = await client.post(
        "/api/v1/execution/log",
        params={
            "workflow_id": workflow_id,
            "event_type": "task_started",
            "message": "Task started successfully",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["workflow_id"] == workflow_id
    assert data["event_type"] == "task_started"
    assert data["message"] == "Task started successfully"
    assert "id" in data
    assert "timestamp" in data


async def test_create_execution_log_with_optional_fields(
    client: AsyncClient, sample_workflow_data, sample_agent_data
):
    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    response = await client.post(
        "/api/v1/execution/log",
        params={
            "workflow_id": workflow_id,
            "event_type": "agent_called",
            "message": "Agent was invoked",
            "task_id": "some-task-id",
            "agent_id": agent_id,
        },
        json={"duration_ms": 150, "model": "MiniMax-M2.7"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["task_id"] == "some-task-id"
    assert data["agent_id"] == agent_id
    assert data["meta_data"]["duration_ms"] == 150


# ---------------------------------------------------------------------------
# GET /api/v1/execution/logs/{workflow_id}
# ---------------------------------------------------------------------------

async def test_get_execution_logs_empty(client: AsyncClient, sample_workflow_data):
    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    response = await client.get(f"/api/v1/execution/logs/{workflow_id}")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_execution_logs_with_entries(
    client: AsyncClient, sample_workflow_data, sample_agent_data
):
    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    for i in range(3):
        await client.post(
            "/api/v1/execution/log",
            params={
                "workflow_id": workflow_id,
                "event_type": f"event_{i}",
                "message": f"Message {i}",
            },
        )

    response = await client.get(f"/api/v1/execution/logs/{workflow_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


async def test_get_execution_logs_pagination(client: AsyncClient, sample_workflow_data):
    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    for i in range(5):
        await client.post(
            "/api/v1/execution/log",
            params={
                "workflow_id": workflow_id,
                "event_type": f"event_{i}",
                "message": f"Message {i}",
            },
        )

    response = await client.get(f"/api/v1/execution/logs/{workflow_id}?skip=2&limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2