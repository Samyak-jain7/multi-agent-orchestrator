"""
Task CRUD and retry API endpoints.
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from core.database import get_db
from models.execution import TaskModel, AgentModel
from schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskStatus,
)
from agents.queue import task_queue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    workflow_id: Optional[str] = Query(default=None),
    status_filter: Optional[TaskStatus] = Query(
        default=None, alias="status", description="Filter by task status"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    List tasks with optional filtering by workflow_id and status.
    The `status` query parameter maps to `status_filter` internally.
    """
    stmt = select(TaskModel)

    if workflow_id:
        stmt = stmt.where(TaskModel.workflow_id == workflow_id)
    if status_filter is not None:
        stmt = stmt.where(TaskModel.status == status_filter.value)

    stmt = stmt.offset(skip).limit(limit).order_by(
        TaskModel.priority.desc(), TaskModel.created_at.desc()
    )
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


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single task by ID."""
    stmt = select(TaskModel).where(TaskModel.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )

    return TaskResponse(
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


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task_data: TaskCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new task. The referenced agent_id is validated to exist.
    """
    # Validate agent exists
    agent_stmt = select(AgentModel).where(AgentModel.id == task_data.agent_id)
    agent_result = await db.execute(agent_stmt)
    agent = agent_result.scalar_one_or_none()

    if not agent:
        logger.warning(f"Task create failed – agent not found: {task_data.agent_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent '{task_data.agent_id}' not found",
        )

    task = TaskModel(
        workflow_id=task_data.workflow_id,
        agent_id=task_data.agent_id,
        title=task_data.title,
        description=task_data.description,
        input_data=task_data.input_data,
        priority=task_data.priority,
        dependencies=task_data.dependencies,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)
    logger.info(f"Task created: id={task.id}, workflow={task.workflow_id}, agent={task.agent_id}")

    return TaskResponse(
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


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing task's fields."""
    stmt = select(TaskModel).where(TaskModel.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        logger.warning(f"Update failed – task not found: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )

    update_dict = task_data.model_dump(exclude_unset=True)

    if "status" in update_dict and update_dict["status"]:
        update_dict["status"] = update_dict["status"].value
        if update_dict["status"] == TaskStatus.RUNNING.value:
            update_dict["started_at"] = datetime.utcnow()
        elif update_dict["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
            update_dict["completed_at"] = datetime.utcnow()

    for key, value in update_dict.items():
        setattr(task, key, value)

    await db.commit()
    await db.refresh(task)
    logger.info(f"Task updated: id={task.id}")

    return TaskResponse(
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


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a task."""
    stmt = select(TaskModel).where(TaskModel.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        logger.warning(f"Delete failed – task not found: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )

    await db.execute(delete(TaskModel).where(TaskModel.id == task_id))
    await db.commit()
    logger.info(f"Task deleted: id={task_id}")


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retry a failed or cancelled task by resetting its state
    and re-enqueuing it.
    """
    stmt = select(TaskModel).where(TaskModel.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        logger.warning(f"Retry failed – task not found: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )

    if task.status not in [TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
        logger.warning(f"Retry rejected – task {task_id} has status {task.status}, not failed/cancelled")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry task with status '{task.status}'. "
                   "Only tasks in 'failed' or 'cancelled' state can be retried.",
        )

    task.status = TaskStatus.PENDING.value
    task.retry_count = (task.retry_count or 0) + 1
    task.error = None
    task.output = None
    task.started_at = None
    task.completed_at = None

    await db.commit()
    await db.refresh(task)

    # Re-enqueue for processing
    await task_queue.enqueue(
        task_type="workflow_execution",
        payload={
            "workflow_id": task.workflow_id,
            "input_data": task.input_data or {},
        },
    )

    logger.info(f"Task re-queued for retry: id={task.id}, retry_count={task.retry_count}")

    return TaskResponse(
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
