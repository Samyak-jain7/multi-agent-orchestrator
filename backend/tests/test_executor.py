"""
Unit tests for backend/agents/executor.py AgentExecutor.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestAgentExecutorRun:
    """Test AgentExecutor._run_agent with mocked LLM."""

    async def test_run_agent_returns_expected_result_dict(
        self, db_session, mock_provider, mock_llm_response
    ):
        from agents.executor import AgentExecutor

        # Create an agent in the DB
        from models.execution import AgentModel

        agent = AgentModel(
            name="Executor Test Agent",
            model_provider="minimax",
            model_name="MiniMax-M2.7",
            system_prompt="You are a test agent.",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        executor = AgentExecutor(db_session)

        result = await executor._run_agent(agent.id, {"query": "test input"})

        # With our mock, the LLM returns mock_llm_response
        assert isinstance(result, dict)
        assert "result" in result or "timestamp" in result

    async def test_run_agent_error_when_agent_not_found(self, db_session):
        from agents.executor import AgentExecutor

        executor = AgentExecutor(db_session)

        with pytest.raises(ValueError, match="not found"):
            await executor._run_agent("nonexistent-agent-id", {})

    async def test_run_agent_calls_llm_with_correct_messages(
        self, db_session, mock_provider, mock_llm_response
    ):
        from agents.executor import AgentExecutor
        from models.execution import AgentModel

        agent = AgentModel(
            name="Mock LLM Test",
            model_provider="minimax",
            model_name="MiniMax-M2.7",
            system_prompt="You are a helpful assistant.",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        executor = AgentExecutor(db_session)
        await executor._run_agent(agent.id, {"query": "hello"})

        # Verify the provider's ainvoke was called
        mock_provider.return_value.ainvoke.assert_called_once()
        call_args = mock_provider.return_value.ainvoke.call_args
        # Should have been called with [system_msg, human_msg]
        messages = call_args[0][0]
        assert len(messages) == 2


class TestAgentExecutorOutputParsing:
    """Test _parse_output and _format_input."""

    def test_format_input_dict(self):
        from agents.executor import AgentExecutor

        executor = AgentExecutor(MagicMock())
        result = executor._format_input({"query": "test", "lang": "en"})
        assert "query" in result
        assert "test" in result

    def test_format_input_string(self):
        from agents.executor import AgentExecutor

        executor = AgentExecutor(MagicMock())
        result = executor._format_input("just a string")
        assert result == "just a string"

    def test_parse_output_valid_json(self):
        from agents.executor import AgentExecutor

        executor = AgentExecutor(MagicMock())
        result = executor._parse_output('{"result": "success", "data": 42}')
        assert result["result"] == "success"
        assert result["data"] == 42

    def test_parse_output_json_with_extra_text(self):
        from agents.executor import AgentExecutor

        executor = AgentExecutor(MagicMock())
        result = executor._parse_output(
            'Here is the result: {"result": "success"}\n\nDone.'
        )
        assert result["result"] == "success"

    def test_parse_output_non_json_returns_text(self):
        from agents.executor import AgentExecutor

        executor = AgentExecutor(MagicMock())
        result = executor._parse_output("Just plain text response")
        assert result["result"] == "Just plain text response"
        assert "timestamp" in result


class TestAgentExecutorTaskStatus:
    """Test _update_task_status."""

    async def test_update_task_sets_started_at_for_running(self, db_session):
        from agents.executor import AgentExecutor
        from models.execution import TaskModel
        from schemas import TaskStatus

        # Create a task
        task = TaskModel(
            workflow_id="wf-1",
            agent_id="agent-1",
            title="Status Test",
            status="pending",
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        executor = AgentExecutor(db_session)
        await executor._update_task_status(task.id, TaskStatus.RUNNING)

        # Re-fetch
        from sqlalchemy import select

        stmt = select(TaskModel).where(TaskModel.id == task.id)
        result = await db_session.execute(stmt)
        updated = result.scalar_one()
        assert updated.status == "running"
        assert updated.started_at is not None

    async def test_update_task_sets_completed_at_for_completed(self, db_session):
        from agents.executor import AgentExecutor
        from models.execution import TaskModel
        from schemas import TaskStatus

        task = TaskModel(
            workflow_id="wf-1",
            agent_id="agent-1",
            title="Status Test",
            status="running",
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        executor = AgentExecutor(db_session)
        await executor._update_task_status(
            task.id, TaskStatus.COMPLETED, output={"result": "done"}
        )

        from sqlalchemy import select

        stmt = select(TaskModel).where(TaskModel.id == task.id)
        result = await db_session.execute(stmt)
        updated = result.scalar_one()
        assert updated.status == "completed"
        assert updated.completed_at is not None
        assert updated.output == {"result": "done"}

    async def test_update_task_sets_error_on_failure(self, db_session):
        from agents.executor import AgentExecutor
        from models.execution import TaskModel
        from schemas import TaskStatus

        task = TaskModel(
            workflow_id="wf-1",
            agent_id="agent-1",
            title="Error Test",
            status="running",
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        executor = AgentExecutor(db_session)
        await executor._update_task_status(
            task.id, TaskStatus.FAILED, error="Something went wrong"
        )

        from sqlalchemy import select

        stmt = select(TaskModel).where(TaskModel.id == task.id)
        result = await db_session.execute(stmt)
        updated = result.scalar_one()
        assert updated.status == "failed"
        assert updated.error == "Something went wrong"


class TestAgentExecutorExecuteWorkflow:
    """Test execute_workflow."""

    async def test_execute_workflow_with_no_tasks(
        self, db_session, mock_provider
    ):
        from agents.executor import AgentExecutor
        from models.execution import WorkflowModel

        # Create a workflow with agents but no tasks
        wf = WorkflowModel(
            name="Empty WF",
            agent_ids=["agent-that-doesnt-exist"],
            status="idle",
        )
        db_session.add(wf)
        await db_session.commit()
        await db_session.refresh(wf)

        executor = AgentExecutor(db_session)
        result = await executor.execute_workflow(wf.id, {"test": "data"})

        assert result["workflow_id"] == wf.id
        assert result["status"] == "completed"
        assert "task_results" in result

    async def test_execute_workflow_not_found_raises(self, db_session):
        from agents.executor import AgentExecutor

        executor = AgentExecutor(db_session)

        with pytest.raises(ValueError, match="not found"):
            await executor.execute_workflow("nonexistent-wf-id", {})


class TestAgentExecutorBuildGraph:
    """Test build_graph."""

    def test_build_graph_returns_compiled_graph(self):
        from agents.executor import AgentExecutor

        executor = AgentExecutor(MagicMock())
        graph = executor.build_graph()

        assert graph is not None
        # Should be a compiled StateGraph
        assert hasattr(graph, "ainvoke")
