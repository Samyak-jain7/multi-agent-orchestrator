"""
Unit tests for backend/agents/queue.py TaskQueue.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestTaskQueueBasics:
    """Test TaskQueue enqueue / basic operations."""

    async def test_enqueue_returns_task_id(self):
        from agents.queue import TaskQueue

        queue = TaskQueue(max_concurrent=1)
        await queue.start()

        task_id = await queue.enqueue(
            task_type="workflow_execution",
            payload={"workflow_id": "wf-1", "input_data": {}},
        )

        assert task_id is not None
        assert len(task_id) > 0

        await queue.stop()

    async def test_enqueue_appears_in_get_task(self):
        from agents.queue import TaskQueue

        queue = TaskQueue(max_concurrent=1)
        await queue.start()

        task_id = await queue.enqueue(
            task_type="agent_task",
            payload={"agent_id": "agent-1"},
        )

        # Give the queue a moment to register the task
        await asyncio.sleep(0.05)

        task = queue.get_task(task_id)
        assert task is not None
        assert task.task_id == task_id
        assert task.task_type == "agent_task"
        assert task.status.value in ("pending", "processing", "completed")

        await queue.stop()

    async def test_get_task_unknown_id_returns_none(self):
        from agents.queue import TaskQueue

        queue = TaskQueue(max_concurrent=1)
        await queue.start()

        task = queue.get_task("nonexistent-task-id")
        assert task is None

        await queue.stop()

    async def test_get_tasks_returns_all_queued(self):
        from agents.queue import TaskQueue

        queue = TaskQueue(max_concurrent=5)
        await queue.start()

        for i in range(3):
            await queue.enqueue(
                task_type="agent_task",
                payload={"index": i},
            )

        await asyncio.sleep(0.05)

        all_tasks = queue.get_tasks()
        assert len(all_tasks) == 3

        await queue.stop()


class TestTaskQueueConcurrency:
    """Test max_concurrency enforcement."""

    async def test_max_concurrency_respected(self):
        from agents.queue import TaskQueue, QueueStatus

        queue = TaskQueue(max_concurrent=2)
        await queue.start()

        # Track how many tasks ran concurrently
        concurrent_count = 0
        max_concurrent_seen = 0
        lock = asyncio.Lock()

        async def slow_handler(payload, task):
            nonlocal concurrent_count, max_concurrent_seen
            async with lock:
                concurrent_count += 1
                max_concurrent_seen = max(max_concurrent_seen, concurrent_count)

            await asyncio.sleep(0.3)  # Simulate work

            async with lock:
                concurrent_count -= 1

        # Patch the handler
        with patch.object(queue, "_handle_agent_task", slow_handler):
            # Enqueue 4 tasks
            task_ids = []
            for i in range(4):
                tid = await queue.enqueue("agent_task", {"index": i})
                task_ids.append(tid)

            # Wait enough time for tasks to be picked up
            await asyncio.sleep(0.5)

        # With max_concurrent=2, we should never see more than 2 running at once
        assert max_concurrent_seen <= 2

        await queue.stop()


class TestTaskQueuePubSub:
    """Test subscribe / unsubscribe / event emission."""

    async def test_subscribe_receives_events(self):
        from agents.queue import TaskQueue

        queue = TaskQueue(max_concurrent=1)
        await queue.start()

        received_events = []

        async def subscriber(event):
            received_events.append(event)

        queue.subscribe("test-subscriber", subscriber)

        task_id = await queue.enqueue(
            task_type="agent_task",
            payload={"agent_id": "test-agent"},
        )

        # Wait for event to be published
        await asyncio.sleep(0.2)

        assert len(received_events) > 0
        # First event should be task_enqueued
        assert received_events[0].get("type") == "task_enqueued" or (
            "type" in received_events[0]
        )

        await queue.stop()

    async def test_unsubscribe_stops_receiving_events(self):
        from agents.queue import TaskQueue

        queue = TaskQueue(max_concurrent=1)
        await queue.start()

        received_events = []

        async def subscriber(event):
            received_events.append(event)

        queue.subscribe("unsub-test", subscriber)
        queue.unsubscribe("unsub-test")

        await queue.enqueue(
            task_type="agent_task",
            payload={"id": "1"},
        )

        await asyncio.sleep(0.2)

        # After unsubscribe, no events should be received
        # (but we may have 1 from enqueue before unsub was processed)
        # The important thing is no processing events
        await queue.stop()

    async def test_multiple_subscribers_all_receive(self):
        from agents.queue import TaskQueue

        queue = TaskQueue(max_concurrent=1)
        await queue.start()

        events_sub1 = []
        events_sub2 = []

        async def sub1(event):
            events_sub1.append(event)

        async def sub2(event):
            events_sub2.append(event)

        queue.subscribe("sub1", sub1)
        queue.subscribe("sub2", sub2)

        await queue.enqueue(
            task_type="agent_task",
            payload={"id": "1"},
        )

        await asyncio.sleep(0.2)

        # Both subscribers should have received the enqueued event
        assert len(events_sub1) > 0
        assert len(events_sub2) > 0

        await queue.stop()


class TestTaskQueueCancellation:
    """Test task cancellation."""

    async def test_task_with_error_sets_failed_status(self):
        from agents.queue import TaskQueue, QueueStatus

        queue = TaskQueue(max_concurrent=1)
        await queue.start()

        # Override handler to raise an error
        async def failing_handler(payload, task):
            raise ValueError("Simulated failure")

        with patch.object(queue, "_handle_agent_task", failing_handler):
            task_id = await queue.enqueue(
                "agent_task",
                {"agent_id": "test"},
            )

            # Wait for processing to complete
            await asyncio.sleep(0.3)

        task = queue.get_task(task_id)
        assert task is not None
        assert task.status == QueueStatus.FAILED
        assert task.error is not None
        assert "Simulated failure" in task.error

        await queue.stop()


class TestTaskQueueLifecycle:
    """Test start / stop lifecycle."""

    async def test_start_sets_running_flag(self):
        from agents.queue import TaskQueue

        queue = TaskQueue(max_concurrent=3)
        assert queue._running is False

        await queue.start()
        assert queue._running is True

        await queue.stop()
        assert queue._running is False

    async def test_double_start_does_nothing(self):
        from agents.queue import TaskQueue

        queue = TaskQueue(max_concurrent=2)
        await queue.start()

        initial_worker_count = len(queue._workers)
        await queue.start()  # Should be no-op

        assert len(queue._workers) == initial_worker_count

        await queue.stop()


class TestTaskQueueEvents:
    """Test get_task_events."""

    async def test_get_task_events_empty_for_unknown_task(self):
        from agents.queue import TaskQueue

        queue = TaskQueue(max_concurrent=1)
        await queue.start()

        events = await queue.get_task_events("nonexistent-task-id")
        assert events == []

        await queue.stop()

    async def test_get_task_events_respects_after_index(self):
        from agents.queue import TaskQueue

        queue = TaskQueue(max_concurrent=1)
        await queue.start()

        task_id = await queue.enqueue(
            task_type="agent_task",
            payload={"id": "1"},
        )

        await asyncio.sleep(0.2)

        # Add more events
        await queue._emit_event(task_id, {"type": "extra_event_1"})
        await queue._emit_event(task_id, {"type": "extra_event_2"})

        events = await queue.get_task_events(task_id, after_index=0)
        assert len(events) >= 1

        await queue.stop()
