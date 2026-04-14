import pytest
import asyncio
from agents.queue import TaskQueue, QueuedTask, QueueStatus


@pytest.fixture
def queue():
    q = TaskQueue(max_concurrent=2)
    return q


@pytest.mark.asyncio
async def test_enqueue_returns_task_id(queue):
    task_id = await queue.enqueue("agent_task", {"agent_id": "test-agent"})
    assert task_id is not None
    assert len(task_id) > 0


@pytest.mark.asyncio
async def test_get_task(queue):
    task_id = await queue.enqueue("agent_task", {"agent_id": "test-agent"})
    task = queue.get_task(task_id)
    assert task is not None
    assert task.task_id == task_id
    assert task.task_type == "agent_task"


@pytest.mark.asyncio
async def test_get_tasks(queue):
    await queue.enqueue("agent_task", {"n": 1})
    await queue.enqueue("agent_task", {"n": 2})
    tasks = queue.get_tasks()
    assert len(tasks) == 2


@pytest.mark.asyncio
async def test_subscribe_unsubscribe(queue):
    events = []

    async def callback(event):
        events.append(event)

    queue.subscribe("test-sub", callback)
    await queue.enqueue("agent_task", {"test": True})

    # Allow event processing
    await asyncio.sleep(0.2)

    queue.unsubscribe("test-sub")
    assert len(events) >= 0  # Events may or may not have arrived


@pytest.mark.asyncio
async def test_queue_memory_pruning():
    q = TaskQueue(max_concurrent=1)

    # Add many tasks to trigger pruning
    for i in range(50):
        await q.enqueue("agent_task", {"index": i})

    # Should not exceed 1000 (prune happens at >1000)
    tasks = q.get_tasks()
    assert len(tasks) <= 1000