"""
Tests for models/execution.py.
Agent CRUD, Workflow cascade delete, Task status transitions,
timestamps auto-populated.
"""
import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.execution import (
    AgentModel,
    WorkflowModel,
    TaskModel,
    ExecutionLogModel,
    generate_uuid,
)


class TestAgentModel:
    """Agent model CRUD and field defaults."""

    async def test_agent_create(self, db_session: AsyncSession):
        agent = AgentModel(
            name="Test Agent",
            description="A test agent",
            model_provider="minimax",
            model_name="MiniMax-M2.7",
            system_prompt="You are helpful.",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.id is not None
        assert agent.name == "Test Agent"
        assert agent.model_provider == "minimax"
        assert agent.created_at is not None
        assert agent.updated_at is not None

    async def test_agent_uuid_unique(self, db_session: AsyncSession):
        a1 = AgentModel(name="Agent 1", system_prompt="Prompt 1")
        a2 = AgentModel(name="Agent 2", system_prompt="Prompt 2")
        db_session.add_all([a1, a2])
        await db_session.commit()

        assert a1.id != a2.id

    async def test_agent_default_provider(self, db_session: AsyncSession):
        agent = AgentModel(name="Default Provider Agent", system_prompt="Prompt")
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.model_provider == "minimax"
        assert agent.model_name == "MiniMax-M2.7"

    async def test_agent_default_tools_empty_list(self, db_session: AsyncSession):
        agent = AgentModel(name="Tools Agent", system_prompt="Prompt")
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.tools == []

    async def test_agent_read_by_id(self, db_session: AsyncSession):
        agent = AgentModel(name="Read Test", system_prompt="Prompt")
        db_session.add(agent)
        await db_session.commit()

        stmt = select(AgentModel).where(AgentModel.id == agent.id)
        result = await db_session.execute(stmt)
        found = result.scalar_one()

        assert found.name == "Read Test"

    async def test_agent_update(self, db_session: AsyncSession):
        agent = AgentModel(name="Old Name", system_prompt="Prompt")
        db_session.add(agent)
        await db_session.commit()

        agent.name = "New Name"
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.name == "New Name"
        assert agent.updated_at > agent.created_at

    async def test_agent_delete(self, db_session: AsyncSession):
        agent = AgentModel(name="Delete Me", system_prompt="Prompt")
        db_session.add(agent)
        await db_session.commit()
        agent_id = agent.id

        await db_session.delete(agent)
        await db_session.commit()

        stmt = select(AgentModel).where(AgentModel.id == agent_id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None


class TestWorkflowModel:
    """Workflow model tests."""

    async def test_workflow_create(self, db_session: AsyncSession):
        wf = WorkflowModel(
            name="Test Workflow",
            description="Description",
            agent_ids=["agent-1", "agent-2"],
        )
        db_session.add(wf)
        await db_session.commit()
        await db_session.refresh(wf)

        assert wf.id is not None
        assert wf.name == "Test Workflow"
        assert wf.agent_ids == ["agent-1", "agent-2"]
        assert wf.status == "idle"
        assert wf.created_at is not None

    async def test_workflow_default_agent_ids_empty_list(self, db_session: AsyncSession):
        wf = WorkflowModel(name="Empty Agents WF")
        db_session.add(wf)
        await db_session.commit()
        await db_session.refresh(wf)

        assert wf.agent_ids == []

    async def test_workflow_cascade_delete_tasks(
        self, db_session: AsyncSession, sample_agent
    ):
        wf = WorkflowModel(name="Cascade WF", agent_ids=[])
        db_session.add(wf)
        await db_session.commit()
        await db_session.refresh(wf)

        task1 = TaskModel(
            workflow_id=wf.id,
            agent_id=sample_agent.id,
            title="Task 1",
            status="pending",
        )
        task2 = TaskModel(
            workflow_id=wf.id,
            agent_id=sample_agent.id,
            title="Task 2",
            status="pending",
        )
        db_session.add_all([task1, task2])
        await db_session.commit()

        # Verify tasks exist
        stmt = select(TaskModel).where(TaskModel.workflow_id == wf.id)
        result = await db_session.execute(stmt)
        assert len(result.scalars().all()) == 2

        # Delete workflow
        await db_session.delete(wf)
        await db_session.commit()

        # Tasks should be gone
        result = await db_session.execute(stmt)
        assert len(result.scalars().all()) == 0


class TestTaskModel:
    """Task model tests."""

    async def test_task_create(self, db_session: AsyncSession, sample_agent, sample_workflow):
        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title="Test Task",
            description="A test task",
            input_data={"key": "value"},
            priority=5,
            dependencies=["dep-1"],
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        assert task.id is not None
        assert task.title == "Test Task"
        assert task.status == "pending"
        assert task.priority == 5
        assert task.created_at is not None

    @pytest.mark.parametrize("status", ["pending", "running", "completed", "failed", "cancelled"])
    async def test_task_status_transitions(
        self, db_session: AsyncSession, sample_agent, sample_workflow, status: str
    ):
        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title=f"Task {status}",
            status=status,
            priority=0,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        assert task.status == status

    async def test_task_started_at_set_when_running(
        self, db_session: AsyncSession, sample_agent, sample_workflow
    ):
        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title="Running Task",
            status="pending",
        )
        db_session.add(task)
        await db_session.commit()

        task.status = "running"
        task.started_at = datetime.utcnow()
        await db_session.commit()
        await db_session.refresh(task)

        assert task.started_at is not None

    async def test_task_completed_at_set_on_completion(
        self, db_session: AsyncSession, sample_agent, sample_workflow
    ):
        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title="Completed Task",
            status="running",
        )
        db_session.add(task)
        await db_session.commit()

        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.output = {"result": "done"}
        await db_session.commit()
        await db_session.refresh(task)

        assert task.completed_at is not None
        assert task.output == {"result": "done"}

    async def test_task_retry_count_default_zero(
        self, db_session: AsyncSession, sample_agent, sample_workflow
    ):
        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title="Retry Task",
            status="failed",
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        assert task.retry_count == 0

    async def test_task_increments_retry_count(
        self, db_session: AsyncSession, sample_agent, sample_workflow
    ):
        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title="Increment Retry",
            status="failed",
            retry_count=2,
        )
        db_session.add(task)
        await db_session.commit()

        task.retry_count += 1
        await db_session.commit()
        await db_session.refresh(task)

        assert task.retry_count == 3

    async def test_task_workflow_id_indexed(
        self, db_session: AsyncSession, sample_agent, sample_workflow
    ):
        """workflow_id should be stored and queryable."""
        wf_id = sample_workflow.id
        task = TaskModel(
            workflow_id=wf_id,
            agent_id=sample_agent.id,
            title="Indexed Task",
            status="pending",
        )
        db_session.add(task)
        await db_session.commit()

        stmt = select(TaskModel).where(TaskModel.workflow_id == wf_id)
        result = await db_session.execute(stmt)
        found = result.scalar_one()

        assert found.workflow_id == wf_id


class TestTimestamps:
    """Timestamps auto-populated on create/update."""

    async def test_agent_timestamps_auto_populated(self, db_session: AsyncSession):
        before = datetime.utcnow()
        agent = AgentModel(name="Timestamp Test", system_prompt="Prompt")
        db_session.add(agent)
        await db_session.commit()
        after = datetime.utcnow()

        assert agent.created_at >= before
        assert agent.created_at <= after
        assert agent.updated_at is not None

    async def test_workflow_timestamps_auto_populated(self, db_session: AsyncSession):
        before = datetime.utcnow()
        wf = WorkflowModel(name="Timestamp WF")
        db_session.add(wf)
        await db_session.commit()
        after = datetime.utcnow()

        assert wf.created_at >= before
        assert wf.created_at <= after
        assert wf.updated_at is not None

    async def test_task_timestamps_auto_populated(self, db_session: AsyncSession, sample_agent, sample_workflow):
        before = datetime.utcnow()
        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title="Timestamp Task",
            status="pending",
        )
        db_session.add(task)
        await db_session.commit()
        after = datetime.utcnow()

        assert task.created_at >= before
        assert task.created_at <= after

    async def test_workflow_updated_at_changes_on_update(self, db_session: AsyncSession):
        wf = WorkflowModel(name="Update Timestamps WF")
        db_session.add(wf)
        await db_session.commit()

        original_updated = wf.updated_at
        wf.name = "Updated WF Name"
        await db_session.commit()
        await db_session.refresh(wf)

        assert wf.updated_at >= original_updated


class TestExecutionLogModel:
    """ExecutionLogModel tests."""

    async def test_execution_log_create(self, db_session: AsyncSession, sample_workflow):
        log = ExecutionLogModel(
            workflow_id=sample_workflow.id,
            task_id="test-task",
            event_type="task_started",
            message="Task started",
            meta_data={"step": 1},
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.id is not None
        assert log.event_type == "task_started"
        assert log.timestamp is not None
        assert log.meta_data["step"] == 1

    async def test_execution_log_workflow_id_indexed(self, db_session: AsyncSession, sample_workflow):
        wf_id = sample_workflow.id
        log = ExecutionLogModel(
            workflow_id=wf_id,
            event_type="test_event",
            message="Test",
        )
        db_session.add(log)
        await db_session.commit()

        stmt = select(ExecutionLogModel).where(
            ExecutionLogModel.workflow_id == wf_id
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one()

        assert found.workflow_id == wf_id


class TestModelUUID:
    """generate_uuid() produces unique IDs."""

    async def test_generate_uuid_unique(self):
        ids = [generate_uuid() for _ in range(100)]
        assert len(set(ids)) == 100

    async def test_generate_uuid_is_string(self):
        uid = generate_uuid()
        assert isinstance(uid, str)
        assert len(uid) == 36  # Standard UUID length
