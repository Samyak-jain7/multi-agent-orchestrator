from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from datetime import datetime

from core.database import get_db
from models.execution import TaskModel, AgentModel
from schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskStatus
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    skip: int = 0,
    limit: int = 100,
    workflow_id: str = None,
    status_filter: TaskStatus = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TaskModel)

    if workflow_id:
        stmt = stmt.where(TaskModel.workflow_id == workflow_id)
    if status_filter:
        stmt = stmt.where(TaskModel.status == status_filter.value)

    stmt = stmt.offset(skip).limit(limit).order_by(TaskModel.priority.desc(), TaskModel.created_at.desc())
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
            completed_at=task.completed_at
        )
        for task in tasks
    ]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(TaskModel).where(TaskModel.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
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
        completed_at=task.completed_at
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task_data: TaskCreate, db: AsyncSession = Depends(get_db)):
    agent_stmt = select(AgentModel).where(AgentModel.id == task_data.agent_id)
    agent_result = await db.execute(agent_stmt)
    agent = agent_result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent {task_data.agent_id} not found"
        )

    task = TaskModel(
        workflow_id=task_data.workflow_id,
        agent_id=task_data.agent_id,
        title=task_data.title,
        description=task_data.description,
        input_data=task_data.input_data,
        priority=task_data.priority,
        dependencies=task_data.dependencies
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

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
        completed_at=task.completed_at
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TaskModel).where(TaskModel.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
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
        completed_at=task.completed_at
    )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(TaskModel).where(TaskModel.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    await db.execute(delete(TaskModel).where(TaskModel.id == task_id))
    await db.commit()


@router.post("/{task_id}/retry")
async def retry_task(task_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(TaskModel).where(TaskModel.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    if task.status not in [TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry task with status {task.status}"
        )

    task.status = TaskStatus.PENDING.value
    task.retry_count = task.retry_count + 1
    task.error = None
    task.output = None
    task.started_at = None
    task.completed_at = None

    await db.commit()
    await db.refresh(task)

    from agents.queue import task_queue
    await task_queue.enqueue(
        task_type="workflow_execution",
        payload={
            "workflow_id": task.workflow_id,
            "input_data": task.input_data or {}
        }
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
        completed_at=task.completed_at
    )
