"""
Tests for /api/v1/tasks endpoints.
Covers: CRUD happy/error paths, POST /retry 400 for running/pending,
200 for failed/cancelled, filter by workflow_id, filter by status.
"""

import pytest
from httpx import AsyncClient


class TestTasksCreate:
    """POST /api/v1/tasks"""

    async def test_create_task_success(self, client: AsyncClient, sample_workflow, sample_agent):
        response = await client.post(
            "/api/v1/tasks",
            json={
                "workflow_id": sample_workflow.id,
                "agent_id": sample_agent.id,
                "title": "New Task",
                "description": "A new task",
                "input_data": {"query": "search"},
                "priority": 1,
                "dependencies": [],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Task"
        assert data["status"] == "pending"
        assert "id" in data

    async def test_create_task_missing_required_field(self, client: AsyncClient, sample_workflow, sample_agent):
        response = await client.post(
            "/api/v1/tasks",
            json={
                "workflow_id": sample_workflow.id,
                "agent_id": sample_agent.id,
                # Missing title intentionally
            },
        )
        # title is required, so this should be 422
        assert response.status_code == 422

    async def test_create_task_invalid_agent(self, client: AsyncClient, sample_workflow):
        response = await client.post(
            "/api/v1/tasks",
            json={
                "workflow_id": sample_workflow.id,
                "agent_id": "nonexistent-agent-id",
                "title": "Task With Bad Agent",
            },
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    async def test_create_task_empty_title(self, client: AsyncClient, sample_workflow, sample_agent):
        response = await client.post(
            "/api/v1/tasks",
            json={
                "workflow_id": sample_workflow.id,
                "agent_id": sample_agent.id,
                "title": "",
            },
        )
        assert response.status_code == 422


class TestTasksList:
    """GET /api/v1/tasks"""

    async def test_list_tasks_empty(self, client: AsyncClient):
        response = await client.get("/api/v1/tasks")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_tasks_with_items(self, client: AsyncClient, sample_task):
        response = await client.get("/api/v1/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_task.id

    async def test_list_tasks_filter_by_workflow_id(self, client: AsyncClient, sample_task, db_session, sample_agent):
        from models.execution import TaskModel, WorkflowModel

        # Second task with different workflow
        wf2 = WorkflowModel(name="Second Workflow")
        db_session.add(wf2)
        await db_session.commit()
        await db_session.refresh(wf2)

        task2 = TaskModel(
            workflow_id=wf2.id,
            agent_id=sample_agent.id,
            title="Task for Other Workflow",
            status="pending",
            priority=0,
        )
        db_session.add(task2)
        await db_session.commit()

        response = await client.get(f"/api/v1/tasks?workflow_id={sample_task.workflow_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["workflow_id"] == sample_task.workflow_id

    @pytest.mark.parametrize("status_filter", ["pending", "running", "completed", "failed", "cancelled"])
    async def test_list_tasks_filter_by_status(
        self,
        client: AsyncClient,
        db_session,
        sample_workflow,
        sample_agent,
        status_filter: str,
    ):
        from models.execution import TaskModel

        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title=f"Task status {status_filter}",
            status=status_filter,
            priority=0,
        )
        db_session.add(task)
        await db_session.commit()

        response = await client.get(f"/api/v1/tasks?status={status_filter}")
        assert response.status_code == 200
        data = response.json()
        assert any(t["status"] == status_filter for t in data)

    @pytest.mark.parametrize("skip,limit,expected", [(0, 1, 1), (1, 10, 0)])
    async def test_list_tasks_pagination(self, client: AsyncClient, sample_task, skip: int, limit: int, expected: int):
        response = await client.get(f"/api/v1/tasks?skip={skip}&limit={limit}")
        assert response.status_code == 200
        assert len(response.json()) == expected


class TestTasksGet:
    """GET /api/v1/tasks/{task_id}"""

    async def test_get_task_found(self, client: AsyncClient, sample_task):
        response = await client.get(f"/api/v1/tasks/{sample_task.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_task.id
        assert data["title"] == sample_task.title

    async def test_get_task_not_found(self, client: AsyncClient):
        response = await client.get("/api/v1/tasks/nonexistent-id")
        assert response.status_code == 404


class TestTasksUpdate:
    """PUT /api/v1/tasks/{task_id}"""

    async def test_update_task_success(self, client: AsyncClient, sample_task):
        response = await client.put(
            f"/api/v1/tasks/{sample_task.id}",
            json={"title": "Updated Task Title", "priority": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Task Title"
        assert data["priority"] == 5

    async def test_update_task_not_found(self, client: AsyncClient):
        response = await client.put(
            "/api/v1/tasks/nonexistent-id",
            json={"title": "Should Not Work"},
        )
        assert response.status_code == 404

    async def test_update_task_status_to_running(self, client: AsyncClient, sample_task):
        response = await client.put(
            f"/api/v1/tasks/{sample_task.id}",
            json={"status": "running"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        # started_at should be set
        assert data["started_at"] is not None

    async def test_update_task_status_to_completed(self, client: AsyncClient, sample_task):
        response = await client.put(
            f"/api/v1/tasks/{sample_task.id}",
            json={"status": "completed"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None


class TestTasksDelete:
    """DELETE /api/v1/tasks/{task_id}"""

    async def test_delete_task_success(self, client: AsyncClient, sample_task):
        response = await client.delete(f"/api/v1/tasks/{sample_task.id}")
        assert response.status_code == 204
        response2 = await client.get(f"/api/v1/tasks/{sample_task.id}")
        assert response2.status_code == 404

    async def test_delete_task_not_found(self, client: AsyncClient):
        response = await client.delete("/api/v1/tasks/nonexistent-id")
        assert response.status_code == 404


class TestTasksRetry:
    """POST /api/v1/tasks/{task_id}/retry"""

    @pytest.mark.parametrize("task_status", ["running", "pending"])
    async def test_retry_task_bad_status(
        self, client: AsyncClient, db_session, sample_workflow, sample_agent, task_status: str
    ):
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
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/tasks/{task.id}/retry")
        assert response.status_code == 400
        assert "cannot retry" in response.json()["detail"].lower()

    @pytest.mark.parametrize("task_status", ["failed", "cancelled"])
    async def test_retry_task_good_status(
        self,
        client: AsyncClient,
        db_session,
        sample_workflow,
        sample_agent,
        mock_task_queue,
        task_status: str,
    ):
        from models.execution import TaskModel

        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title=f"Task {task_status}",
            status=task_status,
            priority=0,
            error="Previous error" if task_status == "failed" else None,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/tasks/{task.id}/retry")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["retry_count"] == 1
        assert data["error"] is None

    async def test_retry_task_not_found(self, client: AsyncClient, mock_task_queue):
        response = await client.post("/api/v1/tasks/nonexistent-id/retry")
        assert response.status_code == 404

    async def test_retry_task_increments_retry_count(
        self,
        client: AsyncClient,
        db_session,
        sample_workflow,
        sample_agent,
        mock_task_queue,
    ):
        from models.execution import TaskModel

        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title="Retry Counter Task",
            status="failed",
            retry_count=2,
            priority=0,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/tasks/{task.id}/retry")
        assert response.status_code == 200
        assert response.json()["retry_count"] == 3

    async def test_retry_task_resets_output(
        self,
        client: AsyncClient,
        db_session,
        sample_workflow,
        sample_agent,
        mock_task_queue,
    ):
        from models.execution import TaskModel

        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title="Reset Output Task",
            status="cancelled",
            output={"old": "result"},
            priority=0,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await client.post(f"/api/v1/tasks/{task.id}/retry")
        assert response.status_code == 200
        assert response.json()["output"] is None
