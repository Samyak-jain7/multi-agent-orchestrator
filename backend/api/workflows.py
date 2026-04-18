"""
Workflow CRUD and execution API endpoints.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.memory import WorkflowMemory
from agents.queue import task_queue
from core.database import get_db
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from models.execution import TaskModel, UserModel, WorkflowModel
from pydantic import BaseModel, Field
from schemas import (
    TaskResponse,
    TaskStatus,
    WorkflowCreate,
    WorkflowExecuteRequest,
    WorkflowResponse,
    WorkflowStatus,
    WorkflowUpdate,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class WorkflowDefinitionCreate(BaseModel):
    """Create a workflow with DAG definition."""

    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    max_iterations: int = Field(default=10)


class WorkflowCreateV2(BaseModel):
    """Enhanced workflow creation with DAG support."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    workflow_definition: Optional[Dict[str, Any]] = None  # DAG definition
    agent_ids: List[str] = Field(default_factory=list)  # Legacy support
    config: Dict[str, Any] = Field(default_factory=dict)
    memory_enabled: bool = True
    max_iterations: int = 10


class WorkflowUpdateV2(BaseModel):
    """Enhanced workflow update."""

    name: Optional[str] = None
    description: Optional[str] = None
    workflow_definition: Optional[Dict[str, Any]] = None
    agent_ids: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None
    memory_enabled: Optional[bool] = None
    max_iterations: Optional[int] = None


class WorkflowMemoryResponse(BaseModel):
    """Response for workflow memory."""

    workflow_id: str
    messages: List[Dict[str, Any]]
    summary: str


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


async def get_current_user(
    x_api_key: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)
) -> Optional[UserModel]:
    """Get current user from API key (optional)."""
    if not x_api_key:
        return None

    import hashlib

    hashed = hashlib.sha256(x_api_key.encode()).hexdigest()
    stmt = select(UserModel).where(UserModel.hashed_api_key == hashed)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _workflow_to_response(wf: WorkflowModel) -> WorkflowResponse:
    """Convert WorkflowModel to WorkflowResponse."""
    return WorkflowResponse(
        id=wf.id,
        name=wf.name,
        description=wf.description,
        agent_ids=wf.agent_ids or [],
        config=wf.config or {},
        status=WorkflowStatus(wf.status),
        created_at=wf.created_at,
        updated_at=wf.updated_at,
        started_at=wf.started_at,
        completed_at=wf.completed_at,
        output=wf.output,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=List[WorkflowResponse])
async def list_workflows(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    owner_id: Optional[str] = Query(default=None, description="Filter by owner"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """List all workflows with pagination. Optionally filter by owner."""
    stmt = select(WorkflowModel)

    # Multi-tenant: filter by owner_id
    if owner_id:
        stmt = stmt.where(WorkflowModel.owner_id == owner_id)
    elif current_user:
        stmt = stmt.where(WorkflowModel.owner_id == current_user.org_id)

    stmt = stmt.offset(skip).limit(limit).order_by(WorkflowModel.created_at.desc())
    result = await db.execute(stmt)
    workflows = result.scalars().all()

    return [_workflow_to_response(wf) for wf in workflows]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """Get a single workflow by ID."""
    stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    if not workflow:
        logger.warning(f"Workflow not found: {workflow_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found",
        )

    # Multi-tenant check
    if current_user and workflow.owner_id and workflow.owner_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return _workflow_to_response(workflow)


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreateV2,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """Create a new workflow with optional DAG definition."""
    logger.info(f"Creating workflow: name={workflow_data.name!r}")

    # Determine owner_id
    owner_id = None
    if current_user:
        owner_id = current_user.org_id

    # Use workflow_definition if provided, otherwise build from agent_ids
    workflow_def = workflow_data.workflow_definition
    if not workflow_def and workflow_data.agent_ids:
        # Build simple DAG from agent_ids
        nodes = []
        edges = []
        for i, agent_id in enumerate(workflow_data.agent_ids):
            node_id = f"agent_{i}"
            nodes.append(
                {
                    "id": node_id,
                    "type": "agent",
                    "agent_id": agent_id,
                    "tools": [],
                }
            )
            if i == 0:
                edges.append({"from": "supervisor", "to": node_id})
            edges.append({"from": node_id, "to": "supervisor"})

        workflow_def = {
            "nodes": [{"id": "supervisor", "type": "supervisor", "config": {}}] + nodes,
            "edges": edges,
            "max_iterations": workflow_data.max_iterations,
        }

    workflow = WorkflowModel(
        name=workflow_data.name,
        description=workflow_data.description,
        agent_ids=workflow_data.agent_ids,
        workflow_definition=workflow_def,
        config=workflow_data.config,
        memory_enabled=workflow_data.memory_enabled,
        max_iterations=workflow_data.max_iterations,
        owner_id=owner_id,
    )

    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    logger.info(f"Workflow created: id={workflow.id}")

    return _workflow_to_response(workflow)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    workflow_data: WorkflowUpdateV2,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """Update an existing workflow."""
    stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    if not workflow:
        logger.warning(f"Update failed – workflow not found: {workflow_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found",
        )

    # Multi-tenant check
    if current_user and workflow.owner_id and workflow.owner_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    update_dict = workflow_data.model_dump(exclude_unset=True)
    update_dict["updated_at"] = datetime.utcnow()

    for key, value in update_dict.items():
        setattr(workflow, key, value)

    await db.commit()
    await db.refresh(workflow)
    logger.info(f"Workflow updated: id={workflow.id}")

    return _workflow_to_response(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """Delete a workflow and all its tasks."""
    stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    if not workflow:
        logger.warning(f"Delete failed – workflow not found: {workflow_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found",
        )

    # Multi-tenant check
    if current_user and workflow.owner_id and workflow.owner_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Delete associated tasks first
    await db.execute(delete(TaskModel).where(TaskModel.workflow_id == workflow_id))
    await db.execute(delete(WorkflowModel).where(WorkflowModel.id == workflow_id))
    await db.commit()
    logger.info(f"Workflow deleted: id={workflow_id}, cascade deleted tasks")


@router.post("/{workflow_id}/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_workflow(
    workflow_id: str,
    request: WorkflowExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """Execute a workflow by enqueuing a workflow_execution task."""
    stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    if not workflow:
        logger.warning(f"Execute failed – workflow not found: {workflow_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found",
        )

    # Multi-tenant check
    if current_user and workflow.owner_id and workflow.owner_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    task_id = await task_queue.enqueue(
        task_type="workflow_execution",
        payload={
            "workflow_id": workflow_id,
            "input_data": request.input_data,
            "use_executor_v2": True,  # Use the new SupervisorExecutor
        },
    )

    logger.info(f"Workflow execution queued: workflow_id={workflow_id}, task_id={task_id}")
    return {"task_id": task_id, "workflow_id": workflow_id, "status": "queued"}


@router.get("/{workflow_id}/memory", response_model=WorkflowMemoryResponse)
async def get_workflow_memory(
    workflow_id: str,
    agent_id: Optional[str] = Query(default=None, description="Filter by agent"),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """
    Get the shared memory state for a workflow.

    This shows all messages exchanged between agents during workflow execution.
    """
    stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found",
        )

    # Multi-tenant check
    if current_user and workflow.owner_id and workflow.owner_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    memory = WorkflowMemory(workflow_id)

    if agent_id:
        messages = memory.get_agent_messages(agent_id)
    else:
        messages = memory.read(limit=limit)

    summary = memory.get_summary()

    return WorkflowMemoryResponse(
        workflow_id=workflow_id,
        messages=messages,
        summary=summary,
    )


@router.delete("/{workflow_id}/memory", status_code=status.HTTP_204_NO_CONTENT)
async def clear_workflow_memory(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """Clear the shared memory for a workflow."""
    stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found",
        )

    # Multi-tenant check
    if current_user and workflow.owner_id and workflow.owner_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    memory = WorkflowMemory(workflow_id)
    memory.clear()

    logger.info(f"Workflow memory cleared: {workflow_id}")


@router.get("/{workflow_id}/tasks", response_model=List[TaskResponse])
async def get_workflow_tasks(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """Get all tasks belonging to a workflow."""
    stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    # Return empty list if workflow not found (backward compatibility)
    if not workflow:
        return []

    # Multi-tenant check
    if current_user and workflow.owner_id and workflow.owner_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    stmt = select(TaskModel).where(TaskModel.workflow_id == workflow_id).order_by(TaskModel.priority.desc())
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    return [
        TaskResponse(
            id=task.id,
            workflow_id=task.workflow_id,
            agent_id=task.agent_id,
            title=task.title,
            description=task.description,
            input_data=task.input_data or {},
            priority=task.priority,
            dependencies=task.dependencies or [],
            status=TaskStatus(task.status),
            output=task.output,
            error=task.error,
            retry_count=task.retry_count,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
        )
        for task in tasks
    ]
