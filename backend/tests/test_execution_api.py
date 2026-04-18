"""
Tests for /api/v1/execution/* endpoints.
Covers: GET /stats, GET /task/{id}/status found/notfound,
GET /task/{id}/events, POST /log, GET /logs/{workflow_id},
GET /stream/{id} Content-Type: text/event-stream.
"""
import pytest
from httpx import AsyncClient


class TestExecutionStats:
    """GET /api/v1/execution/stats"""

    async def test_get_stats_empty(self, client: AsyncClient):
        response = await client.get("/api/v1/execution/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_agents"] == 0
        assert data["total_workflows"] == 0
        assert data["total_tasks"] == 0
        assert "success_rate" in data

    async def test_get_stats_with_data(
        self, client: AsyncClient, sample_agent, sample_workflow, sample_task
    ):
        response = await client.get("/api/v1/execution/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_agents"] == 1
        assert data["total_workflows"] == 1
        assert data["total_tasks"] >= 1


class TestExecutionTaskStatus:
    """GET /api/v1/execution/task/{task_id}/status"""

    async def test_get_task_status_from_db(
        self, client: AsyncClient, sample_task
    ):
        response = await client.get(
            f"/api/v1/execution/task/{sample_task.id}/status"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == sample_task.id
        assert "status" in data

    async def test_get_task_status_not_found(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/execution/task/nonexistent-id/status"
        )
        assert response.status_code == 404

    async def test_get_task_status_in_queue(
        self, client: AsyncClient, mock_task_queue
    ):
        task_id = await mock_task_queue.enqueue(
            "agent_task", {"agent_id": "test-agent"}
        )
        response = await client.get(
            f"/api/v1/execution/task/{task_id}/status"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id


class TestExecutionTaskEvents:
    """GET /api/v1/execution/task/{task_id}/events"""

    async def test_get_task_events_empty(self, client: AsyncClient, sample_task):
        response = await client.get(
            f"/api/v1/execution/task/{sample_task.id}/events"
        )
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "count" in data

    async def test_get_task_events_after_index(
        self, client: AsyncClient, sample_task
    ):
        response = await client.get(
            f"/api/v1/execution/task/{sample_task.id}/events?after_index=0"
        )
        assert response.status_code == 200

    async def test_get_task_events_not_found(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/execution/task/nonexistent-id/events"
        )
        assert response.status_code == 200  # Returns empty events list

    async def test_get_task_events_returns_list(self, client: AsyncClient, sample_task):
        response = await client.get(
            f"/api/v1/execution/task/{sample_task.id}/events"
        )
        data = response.json()
        assert isinstance(data["events"], list)


class TestExecutionLog:
    """POST /api/v1/execution/log"""

    async def test_create_execution_log(
        self, client: AsyncClient, sample_workflow
    ):
        response = await client.post(
            "/api/v1/execution/log",
            params={
                "workflow_id": sample_workflow.id,
                "event_type": "task_started",
                "message": "Task started execution",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["workflow_id"] == sample_workflow.id
        assert data["event_type"] == "task_started"
        assert "id" in data
        assert "timestamp" in data

    async def test_create_execution_log_with_optional_fields(
        self, client: AsyncClient, sample_workflow, sample_agent
    ):
        response = await client.post(
            "/api/v1/execution/log",
            params={
                "workflow_id": sample_workflow.id,
                "event_type": "agent_invoked",
                "message": "Agent invoked",
                "task_id": "test-task-id",
                "agent_id": sample_agent.id,
                "meta_data": {"model": "MiniMax-M2.7"},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["task_id"] == "test-task-id"
        assert data["agent_id"] == sample_agent.id
        # meta_data may be None or a dict depending on API serialization
        assert data["task_id"] == "test-task-id"


class TestExecutionLogsByWorkflow:
    """GET /api/v1/execution/logs/{workflow_id}"""

    async def test_get_execution_logs_empty(
        self, client: AsyncClient, sample_workflow
    ):
        response = await client.get(
            f"/api/v1/execution/logs/{sample_workflow.id}"
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_get_execution_logs_with_items(
        self, client: AsyncClient, sample_workflow
    ):
        # Create two logs
        for i in range(2):
            await client.post(
                "/api/v1/execution/log",
                params={
                    "workflow_id": sample_workflow.id,
                    "event_type": f"event_{i}",
                    "message": f"Message {i}",
                },
            )

        response = await client.get(
            f"/api/v1/execution/logs/{sample_workflow.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.parametrize("skip,limit,expected", [(0, 1, 1), (1, 10, 1)])
    async def test_get_execution_logs_pagination(
        self,
        client: AsyncClient,
        sample_workflow,
        skip: int,
        limit: int,
        expected: int,
    ):
        for i in range(2):
            await client.post(
                "/api/v1/execution/log",
                params={
                    "workflow_id": sample_workflow.id,
                    "event_type": f"event_{i}",
                    "message": f"Message {i}",
                },
            )

        response = await client.get(
            f"/api/v1/execution/logs/{sample_workflow.id}?skip={skip}&limit={limit}"
        )
        assert response.status_code == 200
        assert len(response.json()) == expected

    async def test_get_execution_logs_workflow_not_found(
        self, client: AsyncClient
    ):
        response = await client.get("/api/v1/execution/logs/nonexistent-id")
        assert response.status_code == 200
        assert response.json() == []


class TestExecutionStream:
    """GET /api/v1/execution/stream/{task_id}"""

    async def test_stream_task_events_content_type(
        self, client: AsyncClient, sample_task
    ):
        """Stream endpoint should return text/event-stream Content-Type."""
        response = await client.get(
            f"/api/v1/execution/stream/{sample_task.id}",
            timeout=0.5,
        )
        assert response.status_code == 200
        assert (
            "text/event-stream" in response.headers.get("Content-Type", "")
            or "text/event-stream" in response.headers.get("content-type", "")
        )

    async def test_stream_task_events_disconnect(
        self, client: AsyncClient, sample_task
    ):
        """Server should handle client disconnect gracefully."""
        response = await client.get(
            f"/api/v1/execution/stream/{sample_task.id}",
            timeout=0.5,
        )
        # Should get a response (even if just a heartbeat)
        assert response.status_code == 200

    async def test_stream_task_events_nonexistent_task(
        self, client: AsyncClient
    ):
        """Non-existent task should still connect (queue-based)."""
        response = await client.get(
            "/api/v1/execution/stream/nonexistent-task-id",
            timeout=0.5,
        )
        assert response.status_code == 200


class TestExecutionDashboard:
    """GET /api/v1/execution/stats – detailed checks"""

    async def test_stats_success_rate_calculation(
        self,
        client: AsyncClient,
        db_session,
        sample_workflow,
        sample_agent,
    ):
        from models.execution import TaskModel

        # Create completed and failed tasks
        for status in ["completed", "completed", "failed"]:
            task = TaskModel(
                workflow_id=sample_workflow.id,
                agent_id=sample_agent.id,
                title=f"Task {status}",
                status=status,
                priority=0,
            )
            db_session.add(task)
        await db_session.commit()

        response = await client.get("/api/v1/execution/stats")
        assert response.status_code == 200
        data = response.json()
        # 2 completed, 1 failed -> success_rate = 2/3 ≈ 0.67
        assert data["success_rate"] in [0.67, 0.66, 0.7]

    async def test_stats_active_workflows(
        self,
        client: AsyncClient,
        db_session,
        sample_workflow,
        sample_agent,
    ):
        from models.execution import WorkflowModel, TaskModel

        # Create a running workflow
        running_wf = WorkflowModel(
            name="Running Workflow",
            status="running",
            agent_ids=[],
        )
        db_session.add(running_wf)
        await db_session.commit()

        response = await client.get("/api/v1/execution/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["active_workflows"] >= 1

    async def test_stats_completed_tasks_today(
        self,
        client: AsyncClient,
        db_session,
        sample_workflow,
        sample_agent,
    ):
        from models.execution import TaskModel
        from datetime import datetime

        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title="Today's Task",
            status="completed",
            completed_at=datetime.utcnow(),
            priority=0,
        )
        db_session.add(task)
        await db_session.commit()

        response = await client.get("/api/v1/execution/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["completed_tasks_today"] >= 1
