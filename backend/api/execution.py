"""
Execution monitoring, event streaming, and dashboard stats API endpoints.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from models.execution import (
    AgentModel,
    WorkflowModel,
    TaskModel,
    ExecutionLogModel,
)
from schemas import (
    DashboardStats,
    ExecutionLogResponse,
    ExecutionEvent,
)
from agents import queue as agent_queue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/execution", tags=["execution"])


@router.get("/stream/{task_id}")
async def stream_task_events(task_id: str, request: Request):
    """
    SSE stream for a single task's execution events.
    Streams task_started, task_completed, task_failed, heartbeat, etc.
    """
    async def event_generator():
        subscriber_id = f"stream_{task_id}_{id(request)}"
        queue: asyncio.Queue = asyncio.Queue()

        async def callback(event: dict):
            await queue.put(event)

        agent_queue.task_queue.subscribe(subscriber_id, callback)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # Guard: only forward events for this task
                    if event.get("task_id") and event.get("task_id") != task_id:
                        continue

                    data = json.dumps(event, default=str)
                    yield f"data: {data}\n\n"

                    # Graceful close when terminal state reached
                    if event.get("type") == "status_changed" and event.get(
                        "status"
                    ) in ("completed", "failed"):
                        break

                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

                if await request.is_disconnected():
                    logger.debug(f"SSE client disconnected: task_id={task_id}")
                    break

        finally:
            agent_queue.task_queue.unsubscribe(subscriber_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/workflow/{workflow_id}")
async def stream_workflow_events(workflow_id: str, request: Request):
    """
    SSE stream for all task events within a workflow.
    Streams task_started, task_completed, task_failed, heartbeat, etc.
    """
    async def event_generator():
        subscriber_id = f"workflow_stream_{workflow_id}_{id(request)}"
        queue: asyncio.Queue = asyncio.Queue()

        async def callback(event: dict):
            # Filter: only events belonging to this workflow
            if event.get("workflow_id") == workflow_id or event.get("task_id"):
                await queue.put(event)

        agent_queue.task_queue.subscribe(subscriber_id, callback)

        try:
            last_event_time = datetime.utcnow()

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=5.0)
                    last_event_time = datetime.utcnow()

                    data = json.dumps(event, default=str)
                    yield f"data: {data}\n\n"

                except asyncio.TimeoutError:
                    # Close stream after 60s of inactivity
                    if (datetime.utcnow() - last_event_time).total_seconds() > 60:
                        break
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

                if await request.is_disconnected():
                    logger.debug(f"SSE client disconnected: workflow_id={workflow_id}")
                    break

        finally:
            agent_queue.task_queue.unsubscribe(subscriber_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/task/{task_id}/status")
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    """Get the current status of an in-queue or completed task."""
    task = agent_queue.task_queue.get_task(task_id)

    if not task:
        # Not in queue – try to find it in DB
        stmt = select(TaskModel).where(TaskModel.id == task_id)
        result = await db.execute(stmt)
        db_task = result.scalar_one_or_none()

        if not db_task:
            logger.warning(f"Task status – not found: {task_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_id}' not found",
            )

        return {
            "task_id": db_task.id,
            "status": db_task.status,
            "output": db_task.output,
            "error": db_task.error,
            "retry_count": db_task.retry_count,
        }

    return {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "status": task.status.value,
        "progress": task.progress,
        "result": task.result,
        "error": task.error,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@router.get("/task/{task_id}/events")
async def get_task_events(
    task_id: str,
    after_index: int = Query(default=0, ge=0),
):
    """Retrieve stored events for a task after a given index."""
    events = await agent_queue.task_queue.get_task_events(task_id, after_index)
    return {"events": events, "count": len(events)}


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """
    Aggregate statistics for the dashboard:
    total agents, workflows, tasks; active workflows;
    tasks completed / failed today; overall success rate.
    """
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
            TaskModel.completed_at >= today_start,
        )
    )

    failed_today = await db.scalar(
        select(func.count(TaskModel.id)).where(
            TaskModel.status == "failed",
            TaskModel.completed_at >= today_start,
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

    logger.debug(
        "Dashboard stats computed",
        extra={
            "total_agents": agent_count or 0,
        },
    )

    return DashboardStats(
        total_agents=agent_count or 0,
        total_workflows=workflow_count or 0,
        total_tasks=task_count or 0,
        active_workflows=active_workflows or 0,
        completed_tasks_today=completed_today or 0,
        failed_tasks_today=failed_today or 0,
        success_rate=round(success_rate, 2),
    )


@router.post(
    "/log",
    response_model=ExecutionLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_execution_log(
    workflow_id: str,
    event_type: str,
    message: str,
    task_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    meta_data: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    """Manually create an execution log entry (used by agents/workflows)."""
    log = ExecutionLogModel(
        workflow_id=workflow_id,
        task_id=task_id,
        agent_id=agent_id,
        event_type=event_type,
        message=message,
        meta_data=meta_data,
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
        meta_data=log.meta_data,
        timestamp=log.timestamp,
    )


@router.get("/logs/{workflow_id}", response_model=List[ExecutionLogResponse])
async def get_execution_logs(
    workflow_id: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve execution logs for a specific workflow."""
    stmt = (
        select(ExecutionLogModel)
        .where(ExecutionLogModel.workflow_id == workflow_id)
        .offset(skip)
        .limit(limit)
        .order_by(ExecutionLogModel.timestamp.desc())
    )
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
            meta_data=log.meta_data,
            timestamp=log.timestamp,
        )
        for log in logs
    ]
