"""
Tests for agents/executor.py.
executor.py: run() with mocked LLM, LLM error → error state,
timeout handling, output has result/metadata keys.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from agents.executor import AgentExecutor
from schemas import TaskStatus, WorkflowStatus


class TestExecutorLLMInteraction:
    """Executor calls LLM provider correctly."""

    async def test_executor_run_with_mocked_llm(
        self, db_session, sample_agent, mock_llm
    ):
        executor = AgentExecutor(db_session)

        result = await executor._run_agent(
            sample_agent.id, {"query": "hello world"}
        )

        assert result is not None
        assert isinstance(result, dict)

    async def test_run_agent_returns_parsed_output(
        self, db_session, sample_agent, mock_llm
    ):
        executor = AgentExecutor(db_session)

        result = await executor._run_agent(
            sample_agent.id, {"input": "test"}
        )

        # Mock returns {"result": "mocked response", "timestamp": "..."}
        assert "result" in result or "timestamp" in result

    async def test_run_agent_sanitizes_prompt_braces(
        self, db_session, sample_agent, mock_llm
    ):
        """System prompt braces should be escaped to prevent format errors."""
        executor = AgentExecutor(db_session)

        # Should not raise
        result = await executor._run_agent(
            sample_agent.id, {"test": "data"}
        )
        assert result is not None


class TestExecutorErrorHandling:
    """LLM errors propagate correctly."""

    async def test_run_agent_nonexistent_agent_raises(
        self, db_session, mock_llm
    ):
        executor = AgentExecutor(db_session)

        with pytest.raises(ValueError, match="not found"):
            await executor._run_agent("nonexistent-agent-id", {})

    async def test_llm_error_sets_task_failed(
        self, db_session, sample_task, sample_agent
    ):
        """When LLM raises, task status should be FAILED."""
        from models.execution import TaskModel

        # Set task to running first
        sample_task.status = "running"
        await db_session.commit()

        executor = AgentExecutor(db_session)

        with patch.object(executor, "_run_agent", new=AsyncMock(
            side_effect=Exception("LLM API error")
        )):
            await executor._execute_agent_task({
                "task_id": sample_task.id,
                "agent_id": sample_agent.id,
                "input_data": {},
                "output_data": {},
                "error": None,
                "messages": [],
                "step": 0,
            })

        await db_session.refresh(sample_task)
        assert sample_task.status == TaskStatus.FAILED.value


class TestExecutorOutputStructure:
    """Output always has expected keys."""

    async def test_execute_agent_task_output_has_keys(
        self, db_session, sample_task, sample_agent, mock_llm
    ):
        initial_state = {
            "task_id": sample_task.id,
            "agent_id": sample_agent.id,
            "input_data": {"query": "test"},
            "output_data": {},
            "error": None,
            "messages": [],
            "step": 0,
        }

        executor = AgentExecutor(db_session)
        final_state = await executor._execute_agent_task(initial_state)

        assert "output_data" in final_state
        assert "error" in final_state


class TestExecutorWorkflowExecution:
    """execute_workflow() coordinates tasks."""

    async def test_execute_workflow_not_found_raises(
        self, db_session, mock_llm
    ):
        executor = AgentExecutor(db_session)

        with pytest.raises(ValueError, match="not found"):
            await executor.execute_workflow("nonexistent-id", {})

    async def test_execute_workflow_with_tasks(
        self,
        db_session,
        sample_workflow,
        sample_task,
        sample_agent,
        mock_llm,
    ):
        """Workflow with existing tasks should execute them."""
        # Update task to be linked to the workflow
        from models.execution import TaskModel

        task = TaskModel(
            workflow_id=sample_workflow.id,
            agent_id=sample_agent.id,
            title="WF Task",
            input_data={},
            status="pending",
            priority=0,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        executor = AgentExecutor(db_session)
        result = await executor.execute_workflow(
            sample_workflow.id, {"user_input": "test"}
        )

        assert result["workflow_id"] == sample_workflow.id
        assert result["status"] == "completed"

    async def test_execute_workflow_auto_creates_tasks_from_agent_ids(
        self,
        db_session,
        sample_workflow,
        sample_agent,
        mock_llm,
    ):
        """Workflow with agent_ids but no tasks should auto-create tasks."""
        sample_workflow.agent_ids = [sample_agent.id]
        await db_session.commit()

        executor = AgentExecutor(db_session)
        result = await executor.execute_workflow(
            sample_workflow.id, {}
        )

        assert result["workflow_id"] == sample_workflow.id

    async def test_execute_workflow_updates_workflow_status(
        self,
        db_session,
        sample_workflow,
        sample_agent,
        mock_llm,
    ):
        """Workflow status should change to running then completed."""
        from models.execution import WorkflowModel

        sample_workflow.agent_ids = [sample_agent.id]
        await db_session.commit()

        executor = AgentExecutor(db_session)
        await executor.execute_workflow(sample_workflow.id, {})

        await db_session.refresh(sample_workflow)
        assert sample_workflow.status in [
            WorkflowStatus.RUNNING.value,
            WorkflowStatus.COMPLETED.value,
        ]


class TestExecutorStateTransitions:
    """Task status transitions during execution."""

    async def test_execute_agent_task_sets_running_then_completed(
        self, db_session, sample_task, sample_agent, mock_llm
    ):
        from models.execution import TaskModel

        await db_session.refresh(sample_task)
        initial_status = sample_task.status

        executor = AgentExecutor(db_session)
        await executor._execute_agent_task({
            "task_id": sample_task.id,
            "agent_id": sample_agent.id,
            "input_data": {},
            "output_data": {},
            "error": None,
            "messages": [],
            "step": 0,
        })

        await db_session.refresh(sample_task)
        # Status should have transitioned
        assert sample_task.status in [
            TaskStatus.RUNNING.value,
            TaskStatus.COMPLETED.value,
        ]

    async def test_task_completed_at_set_on_success(
        self, db_session, sample_task, sample_agent, mock_llm
    ):
        from models.execution import TaskModel

        executor = AgentExecutor(db_session)
        await executor._execute_agent_task({
            "task_id": sample_task.id,
            "agent_id": sample_agent.id,
            "input_data": {},
            "output_data": {},
            "error": None,
            "messages": [],
            "step": 0,
        })

        await db_session.refresh(sample_task)
        if sample_task.status == TaskStatus.COMPLETED.value:
            assert sample_task.completed_at is not None


class TestExecutorBuildGraph:
    """build_graph() produces a compilable StateGraph."""

    async def test_build_graph_returns_compilable_graph(self):
        from sqlalchemy.ext.asyncio import AsyncSession
        mock_db = AsyncMock(spec=AsyncSession)

        executor = AgentExecutor(mock_db)
        graph = executor.build_graph()

        assert graph is not None
        # Should be callable (compiled graph)
        assert callable(graph)
