"""
Tests for /api/v1/workflows endpoints.
"""
import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# POST /api/v1/workflows
# ---------------------------------------------------------------------------

async def test_create_workflow_happy_path(client: AsyncClient, sample_workflow_data):
    response = await client.post("/api/v1/workflows", json=sample_workflow_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_workflow_data["name"]
    assert data["description"] == sample_workflow_data["description"]
    assert data["agent_ids"] == []
    assert data["status"] == "idle"
    assert "id" in data
    assert "created_at" in data


async def test_create_workflow_with_agents(client: AsyncClient, sample_agent_data):
    # Create an agent first
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    response = await client.post(
        "/api/v1/workflows",
        json={
            "name": "Workflow With Agent",
            "agent_ids": [agent_id],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["agent_ids"] == [agent_id]


async def test_create_workflow_empty_agents_list(client: AsyncClient):
    response = await client.post(
        "/api/v1/workflows",
        json={
            "name": "Empty Agents Workflow",
            "agent_ids": [],
        },
    )
    assert response.status_code == 201
    assert response.json()["agent_ids"] == []


async def test_create_workflow_missing_name(client: AsyncClient):
    response = await client.post(
        "/api/v1/workflows",
        json={"description": "No name"},
    )
    assert response.status_code == 422


async def test_create_workflow_empty_name(client: AsyncClient):
    response = await client.post(
        "/api/v1/workflows",
        json={"name": "", "agent_ids": []},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/workflows
# ---------------------------------------------------------------------------

async def test_list_workflows_empty(client: AsyncClient):
    response = await client.get("/api/v1/workflows")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_workflows_with_items(client: AsyncClient, sample_workflow_data):
    await client.post("/api/v1/workflows", json=sample_workflow_data)
    await client.post(
        "/api/v1/workflows",
        json={**sample_workflow_data, "name": "Second Workflow"},
    )
    response = await client.get("/api/v1/workflows")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


async def test_list_workflows_pagination(client: AsyncClient, sample_workflow_data):
    for i in range(5):
        await client.post(
            "/api/v1/workflows",
            json={**sample_workflow_data, "name": f"Workflow-{i}"},
        )
    response = await client.get("/api/v1/workflows?skip=2&limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# GET /api/v1/workflows/{id}
# ---------------------------------------------------------------------------

async def test_get_workflow_found(client: AsyncClient, sample_workflow_data):
    create_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/workflows/{workflow_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workflow_id


async def test_get_workflow_not_found(client: AsyncClient):
    response = await client.get("/api/v1/workflows/nonexistent-id-xyz")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/v1/workflows/{id}
# ---------------------------------------------------------------------------

async def test_update_workflow_name(client: AsyncClient, sample_workflow_data):
    create_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/workflows/{workflow_id}",
        json={"name": "Updated Workflow Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Workflow Name"


async def test_update_workflow_agents_list(
    client: AsyncClient, sample_workflow_data, sample_agent_data
):
    create_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = create_resp.json()["id"]

    # Create two agents
    a1_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    a1_id = a1_resp.json()["id"]
    a2_resp = await client.post(
        "/api/v1/agents",
        json={**sample_agent_data, "name": "Second Agent"},
    )
    a2_id = a2_resp.json()["id"]

    response = await client.put(
        f"/api/v1/workflows/{workflow_id}",
        json={"agent_ids": [a1_id, a2_id]},
    )
    assert response.status_code == 200
    assert response.json()["agent_ids"] == [a1_id, a2_id]


async def test_update_workflow_not_found(client: AsyncClient):
    response = await client.put(
        "/api/v1/workflows/nonexistent-id-xyz",
        json={"name": "New Name"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/workflows/{id}
# ---------------------------------------------------------------------------

async def test_delete_workflow_success(client: AsyncClient, sample_workflow_data):
    create_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/workflows/{workflow_id}")
    assert response.status_code == 204

    get_resp = await client.get(f"/api/v1/workflows/{workflow_id}")
    assert get_resp.status_code == 404


async def test_delete_workflow_cascade_deletes_tasks(
    client: AsyncClient, sample_workflow_data, sample_agent_data
):
    """Deleting a workflow should also delete its associated tasks."""
    # Create workflow
    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    # Create an agent
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    # Create a task for this workflow
    task_resp = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Task for cascade test",
            "workflow_id": workflow_id,
            "agent_id": agent_id,
        },
    )
    assert task_resp.status_code == 201
    task_id = task_resp.json()["id"]

    # Verify task exists
    get_task_resp = await client.get(f"/api/v1/tasks/{task_id}")
    assert get_task_resp.status_code == 200

    # Delete workflow
    del_resp = await client.delete(f"/api/v1/workflows/{workflow_id}")
    assert del_resp.status_code == 204

    # Verify task is gone (cascaded)
    get_task_resp = await client.get(f"/api/v1/tasks/{task_id}")
    assert get_task_resp.status_code == 404


async def test_delete_workflow_not_found(client: AsyncClient):
    response = await client.delete("/api/v1/workflows/nonexistent-id-xyz")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/workflows/{id}/execute
# ---------------------------------------------------------------------------

async def test_execute_workflow_returns_task_id(
    client: AsyncClient, sample_workflow_data, mock_task_queue
):
    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    response = await client.post(
        f"/api/v1/workflows/{workflow_id}/execute",
        json={"input_data": {"query": "test"}},
    )
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["workflow_id"] == workflow_id
    assert data["status"] == "queued"


async def test_execute_workflow_missing_input_data(
    client: AsyncClient, sample_workflow_data, mock_task_queue
):
    """Execute without input_data should still be valid (empty dict default)."""
    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    response = await client.post(
        f"/api/v1/workflows/{workflow_id}/execute",
        json={},
    )
    # WorkflowExecuteRequest.input_data has default={}, so this is fine
    assert response.status_code == 202


async def test_execute_workflow_not_found(client: AsyncClient):
    response = await client.post(
        "/api/v1/workflows/nonexistent-id/execute",
        json={"input_data": {}},
    )
    assert response.status_code == 404


async def test_execute_workflow_fires_queue(
    client: AsyncClient, sample_workflow_data
):
    """Verify the queue's enqueue method was called."""
    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    from unittest.mock import AsyncMock, patch

    with patch("api.workflows.task_queue.enqueue", new_callable=AsyncMock) as mock_enqueue:
        mock_enqueue.return_value = "test-task-id"
        
        await client.post(
            f"/api/v1/workflows/{workflow_id}/execute",
            json={"input_data": {"foo": "bar"}},
        )

        mock_enqueue.assert_called()
        call_kwargs = mock_enqueue.call_args
        assert call_kwargs.kwargs["task_type"] == "workflow_execution"


# ---------------------------------------------------------------------------
# GET /api/v1/workflows/{id}/tasks
# ---------------------------------------------------------------------------

async def test_get_workflow_tasks_empty(
    client: AsyncClient, sample_workflow_data
):
    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    response = await client.get(f"/api/v1/workflows/{workflow_id}/tasks")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_workflow_tasks_with_tasks(
    client: AsyncClient, sample_workflow_data, sample_agent_data
):
    # Create workflow and agent
    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    # Create two tasks
    await client.post(
        "/api/v1/tasks",
        json={
            "title": "Task 1",
            "workflow_id": workflow_id,
            "agent_id": agent_id,
        },
    )
    await client.post(
        "/api/v1/tasks",
        json={
            "title": "Task 2",
            "workflow_id": workflow_id,
            "agent_id": agent_id,
        },
    )

    response = await client.get(f"/api/v1/workflows/{workflow_id}/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


async def test_get_workflow_tasks_not_found(client: AsyncClient):
    response = await client.get("/api/v1/workflows/nonexistent-id/tasks")
    assert response.status_code == 200  # Returns empty list, not 404
