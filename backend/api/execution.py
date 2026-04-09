from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import datetime, timedelta
import asyncio
import json

from core.database import get_db
from models.execution import (
    AgentModel,
    WorkflowModel,
    TaskModel,
    ExecutionLogModel
)
from schemas import (
    DashboardStats,
    ExecutionLogResponse,
    ExecutionEvent
)
from agents.queue import task_queue

router = APIRouter(prefix="/execution", tags=["execution"])


@router.get("/stream/{task_id}")
async def stream_task_events(task_id: str, request: Request):
    from fastapi.responses import StreamingResponse
    import asyncio

    async def event_generator():
        subscriber_id = f"stream_{task_id}_{id(request)}"

        queue = asyncio.Queue()

        async def callback(event):
            await queue.put(event)

        task_queue.subscribe(subscriber_id, callback)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)

                    data = json.dumps(event, default=str)
                    yield f"data: {data}\n\n"

                    if event.get("type") in ["status_changed"] and event.get("status") in ["completed", "failed"]:
                        break

                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

                if await request.is_disconnected():
                    break

        finally:
            task_queue.unsubscribe(subscriber_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/stream/workflow/{workflow_id}")
async def stream_workflow_events(workflow_id: str, request: Request):
    from fastapi.responses import StreamingResponse
    import asyncio

    async def event_generator():
        subscriber_id = f"workflow_stream_{workflow_id}_{id(request)}"

        queue = asyncio.Queue()

        async def callback(event):
            if event.get("workflow_id") == workflow_id or event.get("task_id"):
                await queue.put(event)

        task_queue.subscribe(subscriber_id, callback)

        try:
            last_event_time = datetime.utcnow()

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=5.0)
                    last_event_time = datetime.utcnow()

                    data = json.dumps(event, default=str)
                    yield f"data: {data}\n\n"

                except asyncio.TimeoutError:
                    if (datetime.utcnow() - last_event_time).total_seconds() > 60:
                        break

                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

                if await request.is_disconnected():
                    break

        finally:
            task_queue.unsubscribe(subscriber_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/task/{task_id}/status")
async def get_task_status(task_id: str):
    task = task_queue.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    return {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "status": task.status.value,
        "progress": task.progress,
        "result": task.result,
        "error": task.error,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None
    }


@router.get("/task/{task_id}/events")
async def get_task_events(task_id: str, after_index: int = 0):
    events = await task_queue.get_task_events(task_id, after_index)
    return {"events": events, "count": len(events)}


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    agent_count = await db.scalar(select(func.count(AgentModel.id)))
    workflow_count = await db.scalar(select(func.count(WorkflowModel.id)))
    task_count = await db.scalar(select(func.count(TaskModel.id)))

    active_workflows = await db.scalar(
        select(func.count(WorkflowModel.id)).where(WorkflowModel.status == "running")
    )

    completed_today = await db.scalar(
        select(func.count(TaskModel.id)).where(
            TaskModel.status == "completed",
            TaskModel.completed_at >= today_start
        )
    )

    failed_today = await db.scalar(
        select(func.count(TaskModel.id)).where(
            TaskModel.status == "failed",
            TaskModel.completed_at >= today_start
        )
    )

    total_completed = await db.scalar(
        select(func.count(TaskModel.id)).where(TaskModel.status == "completed")
    )
    total_failed = await db.scalar(
        select(func.count(TaskModel.id)).where(TaskModel.status == "failed")
    )

    total_finished = (total_completed or 0) + (total_failed or 0)
    success_rate = (total_completed or 0) / total_finished if total_finished > 0 else 0.0

    return DashboardStats(
        total_agents=agent_count or 0,
        total_workflows=workflow_count or 0,
        total_tasks=task_count or 0,
        active_workflows=active_workflows or 0,
        completed_tasks_today=completed_today or 0,
        failed_tasks_today=failed_today or 0,
        success_rate=round(success_rate, 2)
    )


@router.post("/log", response_model=ExecutionLogResponse)
async def create_execution_log(
    workflow_id: str,
    event_type: str,
    message: str,
    task_id: str = None,
    agent_id: str = None,
    metadata: dict = None,
    db: AsyncSession = Depends(get_db)
):
    log = ExecutionLogModel(
        workflow_id=workflow_id,
        task_id=task_id,
        agent_id=agent_id,
        event_type=event_type,
        message=message,
        metadata=metadata
    )

    db.add(log)
    await db.commit()
    await db.refresh(log)

    return ExecutionLogResponse(
        id=log.id,
        workflow_id=log.workflow_id,
        task_id=log.task_id,
        agent_id=log.agent_id,
        event_type=log.event_type,
        message=log.message,
        metadata=log.metadata,
        timestamp=log.timestamp
    )


@router.get("/logs/{workflow_id}", response_model=List[ExecutionLogResponse])
async def get_execution_logs(
    workflow_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ExecutionLogModel).where(
        ExecutionLogModel.workflow_id == workflow_id
    ).offset(skip).limit(limit).order_by(ExecutionLogModel.timestamp.desc())

    result = await db.execute(stmt)
    logs = result.scalars().all()

    return [
        ExecutionLogResponse(
            id=log.id,
            workflow_id=log.workflow_id,
            task_id=log.task_id,
            agent_id=log.agent_id,
            event_type=log.event_type,
            message=log.message,
            metadata=log.metadata,
            timestamp=log.timestamp
        )
        for log in logs
    ]
