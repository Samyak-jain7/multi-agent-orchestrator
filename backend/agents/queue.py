import asyncio
import uuid
from typing import Dict, Any, Callable, Awaitable, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QueueStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QueuedTask:
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    status: QueueStatus = QueueStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: float = 0.0
    events: List[Dict[str, Any]] = field(default_factory=list)


class TaskQueue:
    def __init__(self, max_concurrent: int = 10):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._tasks: Dict[str, QueuedTask] = {}
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._subscribers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}

    async def start(self):
        if self._running:
            return

        self._running = True
        for i in range(self._max_concurrent):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

        logger.info(f"TaskQueue started with {self._max_concurrent} workers")

    async def stop(self):
        self._running = False

        for worker in self._workers:
            worker.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("TaskQueue stopped")

    async def _worker(self, worker_id: int):
        logger.debug(f"Worker {worker_id} started")

        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            async with self._semaphore:
                await self._process_task(task)

            self._queue.task_done()

        logger.debug(f"Worker {worker_id} stopped")

    async def _process_task(self, task: QueuedTask):
        task.status = QueueStatus.PROCESSING
        task.started_at = datetime.utcnow()

        await self._emit_event(task.task_id, {
            "type": "status_changed",
            "task_id": task.task_id,
            "status": "processing",
            "timestamp": task.started_at.isoformat()
        })

        try:
            handler = self._get_handler(task.task_type)
            if handler is None:
                raise ValueError(f"No handler for task type: {task.task_type}")

            result = await handler(task.payload, task)

            task.status = QueueStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.utcnow()
            task.progress = 1.0

            await self._emit_event(task.task_id, {
                "type": "status_changed",
                "task_id": task.task_id,
                "status": "completed",
                "result": result,
                "timestamp": task.completed_at.isoformat()
            })

        except Exception as e:
            task.status = QueueStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()

            logger.error(f"Task {task.task_id} failed: {str(e)}")

            await self._emit_event(task.task_id, {
                "type": "status_changed",
                "task_id": task.task_id,
                "status": "failed",
                "error": str(e),
                "timestamp": task.completed_at.isoformat()
            })

    def _get_handler(self, task_type: str) -> Optional[Callable]:
        handlers = {
            "workflow_execution": self._handle_workflow_execution,
            "agent_task": self._handle_agent_task,
        }
        return handlers.get(task_type)

    async def _handle_workflow_execution(
        self,
        payload: Dict[str, Any],
        task: QueuedTask
    ) -> Dict[str, Any]:
        from agents.executor_v1 import AgentExecutor as AgentExecutorV1
        from agents.executor_v2 import SupervisorExecutor
        from core.database import get_db_context
        from schemas import WorkflowExecuteRequest

        workflow_id = payload["workflow_id"]
        input_data = payload.get("input_data", {})
        use_executor_v2 = payload.get("use_executor_v2", False)

        async with get_db_context() as db:
            if use_executor_v2:
                # Use the new SupervisorExecutor with LangGraph
                executor = SupervisorExecutor(db, event_callback=self._publish_event)
            else:
                # Use legacy AgentExecutor
                executor = AgentExecutorV1(db, event_callback=self._publish_event)
            result = await executor.execute_workflow(workflow_id, input_data)
            return result

    async def _handle_agent_task(
        self,
        payload: Dict[str, Any],
        task: QueuedTask
    ) -> Dict[str, Any]:
        await asyncio.sleep(0.1)
        return {"status": "completed", "agent_id": payload.get("agent_id")}

    async def _emit_event(self, task_id: str, event: Dict[str, Any]):
        task = self._tasks.get(task_id)
        if task:
            task.events.append(event)

        for subscriber_id, callback in self._subscribers.items():
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Subscriber {subscriber_id} error: {e}")

    async def _publish_event(self, event):
        await self._emit_event(event.task_id or "", {
            "type": "execution_event",
            "event_type": event.event_type,
            "workflow_id": event.workflow_id,
            "task_id": event.task_id,
            "agent_id": event.agent_id,
            "message": event.message,
            "meta_data": event.meta_data,
            "timestamp": event.timestamp.isoformat()
        })

    def subscribe(
        self,
        subscriber_id: str,
        callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        self._subscribers[subscriber_id] = callback

    def unsubscribe(self, subscriber_id: str):
        self._subscribers.pop(subscriber_id, None)

    async def enqueue(
        self,
        task_type: str,
        payload: Dict[str, Any]
    ) -> str:
        # Prevent memory leak by pruning old tasks
        if len(self._tasks) > 1000:
            # Remove 100 oldest tasks
            oldest_ids = sorted(self._tasks.keys(), key=lambda x: self._tasks[x].created_at)[:100]
            for tid in oldest_ids:
                del self._tasks[tid]

        task_id = str(uuid.uuid4())

        task = QueuedTask(
            task_id=task_id,
            task_type=task_type,
            payload=payload
        )

        self._tasks[task_id] = task
        await self._queue.put(task)

        await self._emit_event(task_id, {
            "type": "task_enqueued",
            "task_id": task_id,
            "task_type": task_type,
            "timestamp": task.created_at.isoformat()
        })

        return task_id

    def get_task(self, task_id: str) -> Optional[QueuedTask]:
        return self._tasks.get(task_id)

    def get_tasks(self) -> List[QueuedTask]:
        return list(self._tasks.values())

    async def get_task_events(
        self,
        task_id: str,
        after_index: int = 0
    ) -> List[Dict[str, Any]]:
        task = self._tasks.get(task_id)
        if not task:
            return []
        return task.events[after_index:]


task_queue = TaskQueue(max_concurrent=10)
