import pytest
from pydantic import ValidationError
from schemas import (
    AgentCreate,
    AgentUpdate,
    TaskCreate,
    TaskUpdate,
    WorkflowCreate,
    WorkflowUpdate,
    LLMProvider,
    ToolDefinition,
)


def test_agent_create_valid():
    agent = AgentCreate(
        name="Test Agent",
        model_provider=LLMProvider.OPENAI,
        model_name="gpt-4o",
        system_prompt="You are helpful."
    )
    assert agent.name == "Test Agent"
    assert agent.model_provider == LLMProvider.OPENAI


def test_agent_create_empty_name_fails():
    with pytest.raises(ValidationError):
        AgentCreate(
            name="",
            model_provider=LLMProvider.OPENAI,
            system_prompt="test"
        )


def test_tool_definition():
    tool = ToolDefinition(
        name="test_tool",
        description="A test tool",
        parameters={"type": "object"}
    )
    assert tool.name == "test_tool"
    assert tool.parameters["type"] == "object"


def test_workflow_create():
    wf = WorkflowCreate(
        name="Test Workflow",
        agent_ids=["agent-1", "agent-2"]
    )
    assert wf.name == "Test Workflow"
    assert len(wf.agent_ids) == 2


def test_task_update_status():
    from schemas import TaskStatus
    update = TaskUpdate(status=TaskStatus.RUNNING)
    assert update.status == TaskStatus.RUNNING