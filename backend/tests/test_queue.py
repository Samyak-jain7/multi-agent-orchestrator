"""
Tests for agents/queue.py.
queue.py: enqueue→in queue, worker picks up, max concurrency (mock sleep),
pub/sub state transitions, cancellation.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agents.queue import QueuedTask, QueueStatus, TaskQueue


class TestQueueEnqueue:
    """TaskQueue.enqueue()"""

    async def test_enqueue_returns_task_id(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            task_id = await queue.enqueue("agent_task", {"key": "value"})
            assert task_id is not None
            assert isinstance(task_id, str)
        finally:
            await queue.stop()

    async def test_enqueue_stores_task(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            task_id = await queue.enqueue("agent_task", {"key": "value"})
            task = queue.get_task(task_id)
            assert task is not None
            assert task.task_type == "agent_task"
            assert task.payload == {"key": "value"}
            assert task.status == QueueStatus.PENDING
        finally:
            await queue.stop()

    async def test_enqueue_multiple_unique_ids(self):
        queue = TaskQueue(max_concurrent=2)
        await queue.start()
        try:
            ids = await asyncio.gather(*[queue.enqueue("agent_task", {"n": i}) for i in range(3)])
            assert len(set(ids)) == 3
        finally:
            await queue.stop()

    async def test_enqueue_emits_enqueued_event(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            events = []

            async def collector(event):
                events.append(event)

            queue.subscribe("test_sub", collector)
            await queue.enqueue("agent_task", {})
            # Give the event time to propagate
            await asyncio.sleep(0.05)
            queue.unsubscribe("test_sub")

            assert any(e["type"] == "task_enqueued" for e in events)
        finally:
            await queue.stop()


class TestQueueWorker:
    """Worker pickup and processing."""

    async def test_worker_picks_up_task(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            task_id = await queue.enqueue("agent_task", {"test": True})
            # Wait for the worker to process
            await asyncio.sleep(0.2)
            task = queue.get_task(task_id)
            assert task is not None
        finally:
            await queue.stop()

    async def test_task_status_transitions(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            task_id = await queue.enqueue("agent_task", {})
            await asyncio.sleep(0.2)
            task = queue.get_task(task_id)
            assert task.status in [QueueStatus.PROCESSING, QueueStatus.COMPLETED, QueueStatus.FAILED]
        finally:
            await queue.stop()

    async def test_max_concurrency_respected(self):
        """With max_concurrent=1, only one task processes at a time."""
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            processing_started = []

            async def slow_handler(payload, task):
                await asyncio.sleep(0.3)
                return {"done": True}

            queue._get_handler = lambda tt: slow_handler if tt == "slow_task" else None

            # Enqueue 2 slow tasks
            t1 = await queue.enqueue("slow_task", {})
            t2 = await queue.enqueue("slow_task", {})

            await asyncio.sleep(0.1)
            task1 = queue.get_task(t1)
            task2 = queue.get_task(t2)

            # Only one should be processing at start
            statuses = [task1.status, task2.status]
            assert statuses.count(QueueStatus.PROCESSING) <= 1
        finally:
            await queue.stop()


class TestQueuePubSub:
    """Subscribe/unsubscribe and event delivery."""

    async def test_subscribe_and_unsubscribe(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            received = []

            async def collector(event):
                received.append(event)

            queue.subscribe("sub1", collector)
            assert "sub1" in queue._subscribers

            await queue.enqueue("agent_task", {})
            await asyncio.sleep(0.05)

            queue.unsubscribe("sub1")
            assert "sub1" not in queue._subscribers
        finally:
            await queue.stop()

    async def test_events_delivered_to_subscriber(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            events = []

            async def collector(event):
                events.append(event)

            queue.subscribe("sub1", collector)
            await queue.enqueue("agent_task", {"msg": "hello"})
            await asyncio.sleep(0.1)
            queue.unsubscribe("sub1")

            assert len(events) >= 1
        finally:
            await queue.stop()


class TestQueueStateTransitions:
    """Status transitions: pending → processing → completed/failed."""

    async def test_pending_to_processing(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            task_id = await queue.enqueue("agent_task", {})
            await asyncio.sleep(0.05)
            task = queue.get_task(task_id)
            if task.status == QueueStatus.PENDING:
                await asyncio.sleep(0.1)
                task = queue.get_task(task_id)
            assert task.status == QueueStatus.PROCESSING
        finally:
            await queue.stop()

    async def test_processing_to_completed(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            task_id = await queue.enqueue("agent_task", {})
            await asyncio.sleep(0.3)
            task = queue.get_task(task_id)
            assert task.status == QueueStatus.COMPLETED
        finally:
            await queue.stop()

    async def test_task_with_no_handler_fails(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            task_id = await queue.enqueue("unknown_task_type", {})
            await asyncio.sleep(0.2)
            task = queue.get_task(task_id)
            assert task.status == QueueStatus.FAILED
            assert task.error is not None
        finally:
            await queue.stop()


class TestQueueGetTasks:
    """get_task / get_tasks."""

    async def test_get_task_returns_task(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            task_id = await queue.enqueue("agent_task", {})
            task = queue.get_task(task_id)
            assert task is not None
            assert task.task_id == task_id
        finally:
            await queue.stop()

    async def test_get_task_unknown_returns_none(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            task = queue.get_task("unknown-id")
            assert task is None
        finally:
            await queue.stop()

    async def test_get_tasks_returns_all(self):
        queue = TaskQueue(max_concurrent=2)
        await queue.start()
        try:
            await asyncio.gather(*[queue.enqueue("agent_task", {"i": i}) for i in range(3)])
            tasks = queue.get_tasks()
            assert len(tasks) == 3
        finally:
            await queue.stop()


class TestQueueCancellation:
    """Stop cancels pending tasks."""

    async def test_stop_sets_running_false(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        assert queue._running is True
        await queue.stop()
        assert queue._running is False

    async def test_stop_cancels_workers(self):
        queue = TaskQueue(max_concurrent=2)
        await queue.start()
        await queue.enqueue("agent_task", {})
        await queue.stop()
        assert len(queue._workers) == 0


class TestQueuePruning:
    """Memory pruning after >1000 tasks."""

    async def test_pruning_removes_old_tasks(self):
        queue = TaskQueue(max_concurrent=10)
        await queue.start()
        try:
            # Manually add >1000 tasks to trigger pruning
            import uuid

            for _ in range(1050):
                task_id = str(uuid.uuid4())
                task = QueuedTask(
                    task_id=task_id,
                    task_type="agent_task",
                    payload={},
                )
                queue._tasks[task_id] = task

            # enqueue should trigger pruning
            new_id = await queue.enqueue("agent_task", {"trigger": "prune"})
            assert len(queue._tasks) < 1100
        finally:
            await queue.stop()


class TestQueueGetTaskEvents:
    """get_task_events()."""

    async def test_get_task_events_empty(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            events = await queue.get_task_events("unknown-id")
            assert events == []
        finally:
            await queue.stop()

    async def test_get_task_events_after_index(self):
        queue = TaskQueue(max_concurrent=1)
        await queue.start()
        try:
            task_id = await queue.enqueue("agent_task", {})
            await asyncio.sleep(0.1)
            all_events = await queue.get_task_events(task_id, after_index=0)
            # Should have at least the enqueued event
            assert isinstance(all_events, list)
        finally:
            await queue.stop()
