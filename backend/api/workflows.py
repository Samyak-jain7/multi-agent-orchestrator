from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from datetime import datetime

from core.database import get_db
from models.execution import WorkflowModel, TaskModel
from schemas import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowStatus,
    WorkflowExecuteRequest
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", response_model=List[WorkflowResponse])
async def list_workflows(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(WorkflowModel).offset(skip).limit(limit).order_by(WorkflowModel.created_at.desc())
    result = await db.execute(stmt)
    workflows = result.scalars().all()

    return [
        WorkflowResponse(
            id=wf.id,
            name=wf.name,
            description=wf.description,
            agent_ids=wf.agent_ids or [],
            config=wf.config or {},
            status=WorkflowStatus(wf.status),
            created_at=wf.created_at,
            updated_at=wf.updated_at,
            started_at=wf.started_at,
            completed_at=wf.completed_at
        )
        for wf in workflows
    ]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        agent_ids=workflow.agent_ids or [],
        config=workflow.config or {},
        status=WorkflowStatus(workflow.status),
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        started_at=workflow.started_at,
        completed_at=workflow.completed_at
    )


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(workflow_data: WorkflowCreate, db: AsyncSession = Depends(get_db)):
    workflow = WorkflowModel(
        name=workflow_data.name,
        description=workflow_data.description,
        agent_ids=workflow_data.agent_ids,
        config=workflow_data.config
    )

    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)

    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        agent_ids=workflow.agent_ids or [],
        config=workflow.config or {},
        status=WorkflowStatus(workflow.status),
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        started_at=workflow.started_at,
        completed_at=workflow.completed_at
    )


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    workflow_data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    update_dict = workflow_data.model_dump(exclude_unset=True)
    update_dict["updated_at"] = datetime.utcnow()

    for key, value in update_dict.items():
        setattr(workflow, key, value)

    await db.commit()
    await db.refresh(workflow)

    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        agent_ids=workflow.agent_ids or [],
        config=workflow.config or {},
        status=WorkflowStatus(workflow.status),
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        started_at=workflow.started_at,
        completed_at=workflow.completed_at
    )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    await db.execute(delete(TaskModel).where(TaskModel.workflow_id == workflow_id))
    await db.execute(delete(WorkflowModel).where(WorkflowModel.id == workflow_id))
    await db.commit()


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    request: WorkflowExecuteRequest,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    from agents.queue import task_queue
    task_id = await task_queue.enqueue(
        task_type="workflow_execution",
        payload={
            "workflow_id": workflow_id,
            "input_data": request.input_data
        }
    )

    return {"task_id": task_id, "workflow_id": workflow_id, "status": "queued"}


@router.get("/{workflow_id}/tasks")
async def get_workflow_tasks(
    workflow_id: str,
    db: AsyncSession = Depends(get_db)
):
    from schemas import TaskResponse, TaskStatus

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
            completed_at=task.completed_at
        )
        for task in tasks
    ]
