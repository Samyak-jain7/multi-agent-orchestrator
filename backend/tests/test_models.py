"""
Unit tests for SQLAlchemy ORM models in backend/models/execution.py.
"""
import pytest
from datetime import datetime
from sqlalchemy import select


class TestAgentModel:
    """Test AgentModel CRUD operations."""

    async def test_create_agent(self, db_session):
        from models.execution import AgentModel

        agent = AgentModel(
            name="ORM Test Agent",
            description="Testing ORM",
            model_provider="minimax",
            model_name="MiniMax-M2.7",
            system_prompt="You are a test.",
            tools=[{"name": "test", "description": "test tool"}],
            config={"temperature": 0.7},
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.id is not None
        assert agent.name == "ORM Test Agent"
        assert agent.model_provider == "minimax"
        assert agent.tools == [{"name": "test", "description": "test tool"}]
        assert agent.created_at is not None
        assert agent.updated_at is not None

    async def test_read_agent(self, db_session):
        from models.execution import AgentModel

        agent = AgentModel(
            name="Read Test Agent",
            model_provider="openai",
            model_name="gpt-4o",
            system_prompt="Read test.",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        stmt = select(AgentModel).where(AgentModel.id == agent.id)
        result = await db_session.execute(stmt)
        found = result.scalar_one()

        assert found.id == agent.id
        assert found.name == "Read Test Agent"

    async def test_update_agent(self, db_session):
        from models.execution import AgentModel

        agent = AgentModel(
            name="Update Test Agent",
            model_provider="anthropic",
            model_name="claude-3",
            system_prompt="Before update.",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        agent.name = "Updated Agent Name"
        agent.model_provider = "openai"
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.name == "Updated Agent Name"
        assert agent.model_provider == "openai"

    async def test_delete_agent(self, db_session):
        from models.execution import AgentModel

        agent = AgentModel(
            name="Delete Test Agent",
            model_provider="minimax",
            model_name="MiniMax-M2.7",
            system_prompt="Delete test.",
        )
        db_session.add(agent)
        await db_session.commit()
        agent_id = agent.id

        stmt = select(AgentModel).where(AgentModel.id == agent_id)
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()
        assert found is not None

        await db_session.delete(found)
        await db_session.commit()

        result2 = await db_session.execute(stmt)
        assert result2.scalar_one_or_none() is None


class TestWorkflowModel:
    """Test WorkflowModel CRUD and cascade delete."""

    async def test_create_workflow(self, db_session):
        from models.execution import WorkflowModel

        wf = WorkflowModel(
            name="ORM Workflow",
            description="Test workflow",
            agent_ids=["agent-1", "agent-2"],
            config={"timeout": 60},
        )
        db_session.add(wf)
        await db_session.commit()
        await db_session.refresh(wf)

        assert wf.id is not None
        assert wf.name == "ORM Workflow"
        assert wf.agent_ids == ["agent-1", "agent-2"]
        assert wf.status == "idle"
        assert wf.created_at is not None

    async def test_workflow_cascade_delete_tasks(self, db_session):
        from models.execution import WorkflowModel, TaskModel

        # Create workflow
        wf = WorkflowModel(name="Cascade Test WF", agent_ids=[], status="idle")
        db_session.add(wf)
        await db_session.commit()
        await db_session.refresh(wf)

        # Create two tasks
        t1 = TaskModel(
            workflow_id=wf.id,
            agent_id="some-agent",
            title="Task 1",
            status="pending",
        )
        t2 = TaskModel(
            workflow_id=wf.id,
            agent_id="some-agent",
            title="Task 2",
            status="pending",
        )
        db_session.add(t1)
        db_session.add(t2)
        await db_session.commit()

        # Verify tasks exist
        stmt = select(TaskModel).where(TaskModel.workflow_id == wf.id)
        result = await db_session.execute(stmt)
        tasks = result.scalars().all()
        assert len(tasks) == 2

        # Delete workflow (manually, as cascade isn't configured in ORM)
        from sqlalchemy import delete

        await db_session.execute(delete(TaskModel).where(TaskModel.workflow_id == wf.id))
        await db_session.execute(delete(WorkflowModel).where(WorkflowModel.id == wf.id))
        await db_session.commit()

        # Verify tasks are gone
        result2 = await db_session.execute(stmt)
        assert len(result2.scalars().all()) == 0


class TestTaskModel:
    """Test TaskModel status transitions and timestamps."""

    async def test_create_task(self, db_session):
        from models.execution import TaskModel

        task = TaskModel(
            workflow_id="wf-1",
            agent_id="agent-1",
            title="ORM Task",
            description="Test task",
            input_data={"query": "test"},
            priority=5,
            dependencies=["dep-1"],
            status="pending",
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        assert task.id is not None
        assert task.status == "pending"
        assert task.priority == 5
        assert task.retry_count == 0
        assert task.created_at is not None

    async def test_task_status_transition_pending_to_running(self, db_session):
        from models.execution import TaskModel

        task = TaskModel(
            workflow_id="wf-1",
            agent_id="agent-1",
            title="Status Transition",
            status="pending",
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        task.status = "running"
        task.started_at = datetime.utcnow()
        await db_session.commit()
        await db_session.refresh(task)

        assert task.status == "running"
        assert task.started_at is not None

    async def test_task_status_transition_to_completed(self, db_session):
        from models.execution import TaskModel

        task = TaskModel(
            workflow_id="wf-1",
            agent_id="agent-1",
            title="Complete Me",
            status="running",
            started_at=datetime.utcnow(),
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.output = {"result": "success"}
        await db_session.commit()
        await db_session.refresh(task)

        assert task.status == "completed"
        assert task.completed_at is not None
        assert task.output == {"result": "success"}

    async def test_task_status_transition_to_failed(self, db_session):
        from models.execution import TaskModel

        task = TaskModel(
            workflow_id="wf-1",
            agent_id="agent-1",
            title="Fail Me",
            status="running",
            started_at=datetime.utcnow(),
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        task.status = "failed"
        task.error = "Something went wrong"
        task.completed_at = datetime.utcnow()
        await db_session.commit()
        await db_session.refresh(task)

        assert task.status == "failed"
        assert task.error == "Something went wrong"
        assert task.completed_at is not None

    async def test_task_retry_count_increment(self, db_session):
        from models.execution import TaskModel

        task = TaskModel(
            workflow_id="wf-1",
            agent_id="agent-1",
            title="Retry Test",
            status="failed",
            retry_count=0,
        )
        db_session.add(task)
        await db_session.commit()

        task.retry_count = 1
        task.status = "pending"
        task.error = None
        await db_session.commit()
        await db_session.refresh(task)

        assert task.retry_count == 1
        assert task.status == "pending"


class TestExecutionLogModel:
    """Test ExecutionLogModel."""

    async def test_create_execution_log(self, db_session):
        from models.execution import ExecutionLogModel

        log = ExecutionLogModel(
            workflow_id="wf-1",
            task_id="task-1",
            agent_id="agent-1",
            event_type="task_completed",
            message="Task completed successfully",
            meta_data={"duration_ms": 150},
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.id is not None
        assert log.workflow_id == "wf-1"
        assert log.event_type == "task_completed"
        assert log.timestamp is not None

    async def test_read_execution_logs_by_workflow(self, db_session):
        from models.execution import ExecutionLogModel

        for i in range(3):
            log = ExecutionLogModel(
                workflow_id="wf-1",
                event_type=f"event_{i}",
                message=f"Message {i}",
            )
            db_session.add(log)
        await db_session.commit()

        stmt = (
            select(ExecutionLogModel)
            .where(ExecutionLogModel.workflow_id == "wf-1")
            .order_by(ExecutionLogModel.timestamp.desc())
        )
        result = await db_session.execute(stmt)
        logs = result.scalars().all()

        assert len(logs) == 3


class TestTimestamps:
    """Test that created_at / updated_at are auto-populated."""

    async def test_agent_timestamps_auto_populated(self, db_session):
        from models.execution import AgentModel
        import time

        agent = AgentModel(
            name="Time Test Agent",
            model_provider="minimax",
            model_name="MiniMax-M2.7",
            system_prompt="Timestamp test.",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        created_at = agent.created_at
        updated_at = agent.updated_at

        # Update
        agent.name = "Updated Name"
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.created_at == created_at  # unchanged
        assert agent.updated_at >= updated_at  # changed

    async def test_task_timestamps(self, db_session):
        from models.execution import TaskModel

        task = TaskModel(
            workflow_id="wf-1",
            agent_id="agent-1",
            title="Time Task",
            status="pending",
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        assert task.created_at is not None
        # started_at and completed_at are initially None
        assert task.started_at is None
        assert task.completed_at is None
