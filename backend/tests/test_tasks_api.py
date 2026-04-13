"""
Tests for /api/v1/tasks endpoints.
"""
import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# POST /api/v1/tasks
# ---------------------------------------------------------------------------

async def test_create_task_happy_path(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    # Create required agent and workflow
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    task_payload = {
        **sample_task_data,
        "agent_id": agent_id,
        "workflow_id": workflow_id,
    }
    response = await client.post("/api/v1/tasks", json=task_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == sample_task_data["title"]
    assert data["status"] == "pending"
    assert data["retry_count"] == 0


async def test_create_task_invalid_agent(
    client: AsyncClient, sample_task_data, sample_workflow_data
):
    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    response = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": "nonexistent"},
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


async def test_create_task_missing_title(client: AsyncClient, sample_task_data, sample_agent_data):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post(
        "/api/v1/workflows",
        json={"name": "WF", "agent_ids": []},
    )
    workflow_id = wf_resp.json()["id"]

    response = await client.post(
        "/api/v1/tasks",
        json={
            "workflow_id": workflow_id,
            "agent_id": agent_id,
            "title": "",  # empty title
        },
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/tasks
# ---------------------------------------------------------------------------

async def test_list_tasks_empty(client: AsyncClient):
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_tasks_with_items(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    await client.post(
        "/api/v1/tasks",
        json={
            **sample_task_data,
            "title": "Second Task",
            "workflow_id": workflow_id,
            "agent_id": agent_id,
        },
    )

    response = await client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_tasks_filter_by_workflow_id(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf1_resp = await client.post(
        "/api/v1/workflows", json={**sample_workflow_data, "name": "WF1"}
    )
    wf1_id = wf1_resp.json()["id"]

    wf2_resp = await client.post(
        "/api/v1/workflows", json={**sample_workflow_data, "name": "WF2"}
    )
    wf2_id = wf2_resp.json()["id"]

    await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": wf1_id, "agent_id": agent_id},
    )
    await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": wf2_id, "agent_id": agent_id},
    )

    response = await client.get(f"/api/v1/tasks?workflow_id={wf1_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["workflow_id"] == wf1_id


async def test_list_tasks_filter_by_status(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    # Create a task and manually update its status to completed via PUT
    create_resp = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    task_id = create_resp.json()["id"]

    # Update status to completed
    await client.put(
        f"/api/v1/tasks/{task_id}",
        json={"status": "completed"},
    )

    # Now list with status=completed filter
    response = await client.get("/api/v1/tasks?status=completed")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all(t["status"] == "completed" for t in data)


async def test_list_tasks_filter_by_status_pending(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )

    response = await client.get("/api/v1/tasks?status=pending")
    assert response.status_code == 200
    data = response.json()
    assert all(t["status"] == "pending" for t in data)


async def test_list_tasks_combined_filters(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    await client.post(
        "/api/v1/tasks",
        json={
            **sample_task_data,
            "workflow_id": workflow_id,
            "agent_id": agent_id,
            "priority": 10,
        },
    )

    response = await client.get(
        f"/api/v1/tasks?workflow_id={workflow_id}&status=pending"
    )
    assert response.status_code == 200
    assert all(t["workflow_id"] == workflow_id for t in response.json())


# ---------------------------------------------------------------------------
# GET /api/v1/tasks/{id}
# ---------------------------------------------------------------------------

async def test_get_task_found(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    task_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["id"] == task_id


async def test_get_task_not_found(client: AsyncClient):
    response = await client.get("/api/v1/tasks/nonexistent-task-id")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/v1/tasks/{id}
# ---------------------------------------------------------------------------

async def test_update_task_partial(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    task_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Updated Task Title"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Task Title"


async def test_update_task_status_to_running(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    task_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/tasks/{task_id}",
        json={"status": "running"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["started_at"] is not None


async def test_update_task_status_to_completed(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    task_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/tasks/{task_id}",
        json={"status": "completed"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["completed_at"] is not None


async def test_update_task_not_found(client: AsyncClient):
    response = await client.put(
        "/api/v1/tasks/nonexistent-task-id",
        json={"title": "New Title"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/tasks/{id}
# ---------------------------------------------------------------------------

async def test_delete_task_success(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    task_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 204

    get_resp = await client.get(f"/api/v1/tasks/{task_id}")
    assert get_resp.status_code == 404


async def test_delete_task_not_found(client: AsyncClient):
    response = await client.delete("/api/v1/tasks/nonexistent-task-id")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/tasks/{id}/retry
# ---------------------------------------------------------------------------

async def test_retry_task_failed(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    # Create a task
    create_resp = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    task_id = create_resp.json()["id"]

    # Set to failed
    await client.put(
        f"/api/v1/tasks/{task_id}",
        json={"status": "failed", "error": "Something went wrong"},
    )

    # Retry
    retry_resp = await client.post(f"/api/v1/tasks/{task_id}/retry")
    assert retry_resp.status_code == 200
    data = retry_resp.json()
    assert data["status"] == "pending"
    assert data["retry_count"] == 1
    assert data["error"] is None


async def test_retry_task_cancelled(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    task_id = create_resp.json()["id"]

    # Set to cancelled
    await client.put(f"/api/v1/tasks/{task_id}", json={"status": "cancelled"})

    retry_resp = await client.post(f"/api/v1/tasks/{task_id}/retry")
    assert retry_resp.status_code == 200
    assert retry_resp.json()["status"] == "pending"


async def test_retry_task_running_rejected(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    task_id = create_resp.json()["id"]

    # Set to running
    await client.put(f"/api/v1/tasks/{task_id}", json={"status": "running"})

    retry_resp = await client.post(f"/api/v1/tasks/{task_id}/retry")
    assert retry_resp.status_code == 400
    assert "cannot retry" in retry_resp.json()["detail"].lower()


async def test_retry_task_pending_rejected(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    task_id = create_resp.json()["id"]

    # pending is the default — try to retry it
    retry_resp = await client.post(f"/api/v1/tasks/{task_id}/retry")
    assert retry_resp.status_code == 400


async def test_retry_task_completed_rejected(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    task_id = create_resp.json()["id"]

    await client.put(f"/api/v1/tasks/{task_id}", json={"status": "completed"})

    retry_resp = await client.post(f"/api/v1/tasks/{task_id}/retry")
    assert retry_resp.status_code == 400


async def test_retry_task_not_found(client: AsyncClient):
    response = await client.post("/api/v1/tasks/nonexistent-id/retry")
    assert response.status_code == 404


async def test_retry_task_increments_retry_count(
    client: AsyncClient, sample_task_data, sample_agent_data, sample_workflow_data
):
    agent_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = agent_resp.json()["id"]

    wf_resp = await client.post("/api/v1/workflows", json=sample_workflow_data)
    workflow_id = wf_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/tasks",
        json={**sample_task_data, "workflow_id": workflow_id, "agent_id": agent_id},
    )
    task_id = create_resp.json()["id"]

    # Fail it
    await client.put(f"/api/v1/tasks/{task_id}", json={"status": "failed"})

    # Retry twice
    await client.post(f"/api/v1/tasks/{task_id}/retry")
    await client.put(f"/api/v1/tasks/{task_id}", json={"status": "failed"})
    retry2_resp = await client.post(f"/api/v1/tasks/{task_id}/retry")

    assert retry2_resp.json()["retry_count"] == 2
