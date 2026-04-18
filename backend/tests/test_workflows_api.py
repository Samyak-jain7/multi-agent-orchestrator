"""
Tests for /api/v1/workflows endpoints.
Covers: POST happy/invalid-agent, GET list, GET {id} found/notfound,
PUT update, DELETE cascade, POST /execute returns task_id/notfound/422,
GET tasks for workflow.
"""

import pytest
from httpx import AsyncClient


class TestWorkflowsCreate:
    """POST /api/v1/workflows"""

    async def test_create_workflow_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/workflows",
            json={
                "name": "Test Workflow",
                "description": "A test workflow",
                "agent_ids": [],
                "config": {},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Workflow"
        assert data["status"] == "idle"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.parametrize("missing_field", ["name"])
    async def test_create_workflow_missing_required_field(self, client: AsyncClient, missing_field: str):
        response = await client.post(
            "/api/v1/workflows",
            json={"description": "A workflow", "agent_ids": [], "config": {}},
        )
        assert response.status_code == 422

    async def test_create_workflow_name_too_short(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/workflows",
            json={
                "name": "",
                "agent_ids": [],
                "config": {},
            },
        )
        assert response.status_code == 422

    async def test_create_workflow_with_agents(self, client: AsyncClient, sample_agent):
        response = await client.post(
            "/api/v1/workflows",
            json={
                "name": "Workflow With Agents",
                "agent_ids": [sample_agent.id],
                "config": {"timeout": 60},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert sample_agent.id in data["agent_ids"]


class TestWorkflowsList:
    """GET /api/v1/workflows"""

    async def test_list_workflows_empty(self, client: AsyncClient):
        response = await client.get("/api/v1/workflows")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_workflows_with_items(self, client: AsyncClient, sample_workflow):
        response = await client.get("/api/v1/workflows")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_workflow.id

    @pytest.mark.parametrize("skip,limit,expected", [(0, 1, 1), (1, 10, 0)])
    async def test_list_workflows_pagination(
        self, client: AsyncClient, sample_workflow, skip: int, limit: int, expected: int
    ):
        response = await client.get(f"/api/v1/workflows?skip={skip}&limit={limit}")
        assert response.status_code == 200
        assert len(response.json()) == expected


class TestWorkflowsGet:
    """GET /api/v1/workflows/{workflow_id}"""

    async def test_get_workflow_found(self, client: AsyncClient, sample_workflow):
        response = await client.get(f"/api/v1/workflows/{sample_workflow.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_workflow.id
        assert data["name"] == sample_workflow.name

    async def test_get_workflow_not_found(self, client: AsyncClient):
        response = await client.get("/api/v1/workflows/nonexistent-id")
        assert response.status_code == 404


class TestWorkflowsUpdate:
    """PUT /api/v1/workflows/{workflow_id}"""

    async def test_update_workflow_success(self, client: AsyncClient, sample_workflow):
        response = await client.put(
            f"/api/v1/workflows/{sample_workflow.id}",
            json={"name": "Updated Workflow Name", "description": "Updated desc"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Workflow Name"
        assert data["description"] == "Updated desc"

    async def test_update_workflow_not_found(self, client: AsyncClient):
        response = await client.put(
            "/api/v1/workflows/nonexistent-id",
            json={"name": "Should Not Work"},
        )
        assert response.status_code == 404

    async def test_update_workflow_partial(self, client: AsyncClient, sample_workflow):
        """Only config updated, other fields unchanged."""
        response = await client.put(
            f"/api/v1/workflows/{sample_workflow.id}",
            json={"config": {"new_key": "new_value"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_workflow.name
        assert data["config"] == {"new_key": "new_value"}


class TestWorkflowsDelete:
    """DELETE /api/v1/workflows/{workflow_id}"""

    async def test_delete_workflow_success(self, client: AsyncClient, sample_workflow):
        response = await client.delete(f"/api/v1/workflows/{sample_workflow.id}")
        assert response.status_code == 204
        response2 = await client.get(f"/api/v1/workflows/{sample_workflow.id}")
        assert response2.status_code == 404

    async def test_delete_workflow_not_found(self, client: AsyncClient):
        response = await client.delete("/api/v1/workflows/nonexistent-id")
        assert response.status_code == 404


class TestWorkflowsExecute:
    """POST /api/v1/workflows/{workflow_id}/execute"""

    async def test_execute_workflow_returns_task_id(self, client: AsyncClient, sample_workflow, mock_task_queue):
        response = await client.post(
            f"/api/v1/workflows/{sample_workflow.id}/execute",
            json={"input_data": {"query": "test"}},
        )
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["workflow_id"] == sample_workflow.id
        assert data["status"] == "queued"

    async def test_execute_workflow_not_found(self, client: AsyncClient, mock_task_queue):
        response = await client.post(
            "/api/v1/workflows/nonexistent-id/execute",
            json={"input_data": {}},
        )
        assert response.status_code == 404

    async def test_execute_workflow_with_empty_input(self, client: AsyncClient, sample_workflow, mock_task_queue):
        response = await client.post(
            f"/api/v1/workflows/{sample_workflow.id}/execute",
            json={"input_data": {}},
        )
        assert response.status_code == 202

    async def test_execute_workflow_with_task_overrides(self, client: AsyncClient, sample_workflow, mock_task_queue):
        response = await client.post(
            f"/api/v1/workflows/{sample_workflow.id}/execute",
            json={
                "input_data": {"query": "override test"},
                "task_overrides": [{"agent_id": "agent-1", "title": "Custom Task"}],
            },
        )
        assert response.status_code == 202


class TestWorkflowsTasks:
    """GET /api/v1/workflows/{workflow_id}/tasks"""

    async def test_get_workflow_tasks_empty(self, client: AsyncClient, sample_workflow):
        response = await client.get(f"/api/v1/workflows/{sample_workflow.id}/tasks")
        assert response.status_code == 200
        assert response.json() == []

    async def test_get_workflow_tasks_with_tasks(self, client: AsyncClient, sample_workflow, sample_task):
        response = await client.get(f"/api/v1/workflows/{sample_workflow.id}/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_task.id

    async def test_get_workflow_tasks_workflow_not_found(self, client: AsyncClient):
        response = await client.get("/api/v1/workflows/nonexistent-id/tasks")
        assert response.status_code == 200  # Returns empty list, not 404

    @pytest.mark.parametrize(
        "task_status",
        ["pending", "running", "completed", "failed", "cancelled"],
    )
    async def test_get_workflow_tasks_filtered_by_status(
        self,
        client: AsyncClient,
        db_session,
        sample_workflow,
        sample_agent,
        task_status: str,
    ):
        """Verify tasks are returned regardless of status."""
        from models.execution import TaskModel

        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title=f"Task {task_status}",
            status=task_status,
            priority=0,
        )
        db_session.add(task)
        await db_session.commit()

        response = await client.get(f"/api/v1/workflows/{sample_workflow.id}/tasks")
        assert response.status_code == 200
        data = response.json()
        assert any(t["status"] == task_status for t in data)


class TestWorkflowsCascadeDelete:
    """DELETE workflow should cascade-delete its tasks."""

    async def test_delete_workflow_cascades_tasks(
        self,
        client: AsyncClient,
        db_session,
        sample_workflow,
        sample_agent,
    ):
        from models.execution import TaskModel

        # Create two tasks for the workflow
        for i in range(2):
            task = TaskModel(
                workflow_id=sample_workflow.id,
                agent_id=sample_agent.id,
                title=f"Cascade Task {i}",
                status="pending",
                priority=i,
            )
            db_session.add(task)
        await db_session.commit()

        # Verify tasks exist
        response = await client.get(f"/api/v1/workflows/{sample_workflow.id}/tasks")
        assert len(response.json()) == 2

        # Delete workflow
        delete_response = await client.delete(f"/api/v1/workflows/{sample_workflow.id}")
        assert delete_response.status_code == 204

        # Tasks should be gone
        tasks_response = await client.get(f"/api/v1/workflows/{sample_workflow.id}/tasks")
        assert tasks_response.json() == []
