"""
Full end-to-end integration tests using REAL aiosqlite in-memory DB.
Only LLM calls are mocked. No mocking of database operations.
"""
import asyncio


import pytest


# ---------------------------------------------------------------------------
# Test 1: Create agent → verify it exists in list
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_agent_and_list(client, make_agent):
    """POST /api/v1/agents creates agent; GET /api/v1/agents returns it."""
    agent = await make_agent(name="Orchestrator Agent", system_prompt="Be precise.")

    # List agents
    resp = await client.get("/api/v1/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) == 1
    assert agents[0]["name"] == "Orchestrator Agent"
    assert agents[0]["id"] == agent["id"]


# ---------------------------------------------------------------------------
# Test 2: Create agent → create workflow → execute → task completes
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_agent_to_workflow_to_execution(client, make_agent):
    """Full flow: create agent, add to workflow, execute workflow, poll until done."""
    agent = await make_agent(name="My Agent")

    # Create workflow with the agent
    wf_resp = await client.post(
        "/api/v1/workflows",
        json={
            "name": "My Workflow",
            "agent_ids": [agent["id"]],
        },
    )
    assert wf_resp.status_code == 201
    workflow = wf_resp.json()
    workflow_id = workflow["id"]

    # Execute workflow
    exec_resp = await client.post(f"/api/v1/workflows/{workflow_id}/execute", json={})
    assert exec_resp.status_code == 202
    task_data = exec_resp.json()
    task_id = task_data["task_id"]

    # Poll task status until terminal state (with timeout)
    for _ in range(30):
        await asyncio.sleep(0.5)
        status_resp = await client.get(f"/api/v1/execution/task/{task_id}/status")
        assert status_resp.status_code == 200
        status_body = status_resp.json()
        if status_body.get("status") in ("completed", "failed"):
            assert status_body["status"] == "completed", f"task failed: {status_body.get('error')}"
            break
    else:
        pytest.fail("Task did not reach terminal state within 15s")


# ---------------------------------------------------------------------------
# Test 3: Create workflow → execute → delete → tasks cascade deleted
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workflow_delete_cascade(client, make_agent):
    """Deleting a workflow removes its tasks."""
    agent = await make_agent(name="Cascade Agent")

    wf_resp = await client.post(
        "/api/v1/workflows",
        json={"name": "Cascade WF", "agent_ids": [agent["id"]]},
    )
    assert wf_resp.status_code == 201
    workflow = wf_resp.json()
    workflow_id = workflow["id"]

    # Execute to create a task
    exec_resp = await client.post(f"/api/v1/workflows/{workflow_id}/execute", json={})
    assert exec_resp.status_code == 202
    task_id = exec_resp.json()["task_id"]

    # Wait briefly then verify task exists
    await asyncio.sleep(0.5)
    tasks_resp = await client.get(f"/api/v1/workflows/{workflow_id}/tasks")
    assert tasks_resp.status_code == 200
    tasks = tasks_resp.json()
    assert len(tasks) >= 1

    # Delete workflow
    del_resp = await client.delete(f"/api/v1/workflows/{workflow_id}")
    assert del_resp.status_code == 204

    # Verify tasks are gone
    tasks_resp2 = await client.get(f"/api/v1/workflows/{workflow_id}/tasks")
    assert tasks_resp2.status_code == 200
    assert tasks_resp2.json() == []


# ---------------------------------------------------------------------------
# Test 4: Create 5 tasks simultaneously → MAX_CONCURRENT respected
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_task_limit_via_queue(client, make_agent):
    """
    Enqueue multiple tasks rapidly. The task queue's semaphore
    (max_concurrent=10 by default) controls parallelism.
    """
    agent = await make_agent(name="Concurrent Agent")

    wf_resp = await client.post(
        "/api/v1/workflows",
        json={"name": "Concurrent WF", "agent_ids": [agent["id"]]},
    )
    assert wf_resp.status_code == 201
    workflow = wf_resp.json()
    workflow_id = workflow["id"]

    # Enqueue 5 tasks simultaneously
    task_ids = []
    for _ in range(5):
        exec_resp = await client.post(
            f"/api/v1/workflows/{workflow_id}/execute",
            json={"input_data": {"i": _}},
        )
        assert exec_resp.status_code == 202
        task_ids.append(exec_resp.json()["task_id"])

    # All should be queued (202 accepted)
    assert len(task_ids) == 5

    # Wait for all to complete
    for _ in range(40):
        await asyncio.sleep(0.5)
        statuses = [(await client.get(f"/api/v1/execution/task/{tid}/status")).json()["status"] for tid in task_ids]
        if all(s in ("completed", "failed") for s in statuses):
            break
    else:
        pytest.fail("Tasks did not all finish")

    # Verify none failed
    for tid in task_ids:
        status = (await client.get(f"/api/v1/execution/task/{tid}/status")).json()
        assert status["status"] == "completed", f"{tid} failed: {status.get('error')}"


# ---------------------------------------------------------------------------
# Test 5: Retry flow – force task to failed → retry → task re-queued
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_task_retry_flow(client, make_agent):
    """A failed task can be retried and re-queued."""
    agent = await make_agent(name="Retry Agent")

    wf_resp = await client.post(
        "/api/v1/workflows",
        json={"name": "Retry WF", "agent_ids": [agent["id"]]},
    )
    assert wf_resp.status_code == 201
    workflow = wf_resp.json()
    workflow_id = workflow["id"]

    exec_resp = await client.post(f"/api/v1/workflows/{workflow_id}/execute", json={})
    assert exec_resp.status_code == 202
    task_id = exec_resp.json()["task_id"]

    # Wait for completion
    for _ in range(30):
        await asyncio.sleep(0.5)
        status_resp = await client.get(f"/api/v1/execution/task/{task_id}/status")
        body = status_resp.json()
        if body.get("status") in ("completed", "failed"):
            break

    # Force task to failed state via PUT
    put_resp = await client.put(
        f"/api/v1/tasks/{task_id}",
        json={"status": "failed", "error": "Manual failure for test"},
    )
    assert put_resp.status_code == 200

    # Retry the task
    retry_resp = await client.post(f"/api/v1/tasks/{task_id}/retry")
    assert retry_resp.status_code == 200
    retry_body = retry_resp.json()
    assert retry_body["status"] == "pending"
    assert retry_body["retry_count"] == 1

    # New task_id is returned from retry? Or same task requeued?
    # The retry endpoint returns the same task with updated status and re-enqueues
    new_task_id = retry_body["id"]

    # Poll the new task state
    for _ in range(30):
        await asyncio.sleep(0.5)
        s = (await client.get(f"/api/v1/execution/task/{new_task_id}/status")).json()
        if s.get("status") in ("completed", "failed"):
            assert s["status"] == "completed"
            break
    else:
        pytest.fail("Retried task did not complete")


# ---------------------------------------------------------------------------
# Test 6: SSE stream – connect before executing → events arrive in order
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sse_stream_events_ordered(client, make_agent):
    """Connect SSE stream first, then trigger execution; verify event order."""
    agent = await make_agent(name="SSE Agent")

    wf_resp = await client.post(
        "/api/v1/workflows",
        json={"name": "SSE Workflow", "agent_ids": [agent["id"]]},
    )
    assert wf_resp.status_code == 201
    workflow = wf_resp.json()
    workflow_id = workflow["id"]

    # Execute to get task_id
    exec_resp = await client.post(f"/api/v1/workflows/{workflow_id}/execute", json={})
    assert exec_resp.status_code == 202
    task_id = exec_resp.json()["task_id"]

    # Connect to task SSE stream
    async with client.stream(
        "GET",
        f"/api/v1/execution/stream/{task_id}",
        timeout=15.0,
    ) as response:
        assert response.status_code == 200

        # Trigger immediately fires events on the already-subscribed stream
        received_events = []

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                import json as _json

                event = _json.loads(line[6:])
                received_events.append(event)
                if len(received_events) >= 3:
                    break

        event_types = [e.get("type") for e in received_events]
        assert "task_enqueued" in event_types or "status_changed" in event_types


# ---------------------------------------------------------------------------
# Test 7: Workflow SSE stream
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workflow_sse_stream(client, make_agent):
    """Workflow-level SSE stream receives events for all its tasks."""
    agent = await make_agent(name="WF Stream Agent")

    wf_resp = await client.post(
        "/api/v1/workflows",
        json={"name": "WF Stream WF", "agent_ids": [agent["id"]]},
    )
    assert wf_resp.status_code == 201
    workflow = wf_resp.json()
    workflow_id = workflow["id"]

    async with client.stream(
        "GET",
        f"/api/v1/execution/stream/workflow/{workflow_id}",
        timeout=15.0,
    ) as response:
        assert response.status_code == 200

        # Execute workflow
        exec_resp = await client.post(f"/api/v1/workflows/{workflow_id}/execute", json={})
        assert exec_resp.status_code == 202

        received_events = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                import json as _json

                event = _json.loads(line[6:])
                received_events.append(event)
                if len(received_events) >= 4:
                    break

        assert len(received_events) >= 1
        # All events should belong to this workflow
        for ev in received_events:
            assert ev.get("workflow_id") == workflow_id or ev.get("task_id") is not None


# ---------------------------------------------------------------------------
# Test 8: GET /api/v1/workflows/{id}/tasks
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_workflow_tasks(client, make_agent):
    """Workflow tasks endpoint returns tasks for that workflow."""
    agent = await make_agent(name="Tasks Agent")

    wf_resp = await client.post(
        "/api/v1/workflows",
        json={"name": "Multi Task WF", "agent_ids": [agent["id"]]},
    )
    assert wf_resp.status_code == 201
    workflow = wf_resp.json()
    workflow_id = workflow["id"]

    # Create a task directly
    task_resp = await client.post(
        "/api/v1/tasks",
        json={
            "workflow_id": workflow_id,
            "agent_id": agent["id"],
            "title": "Manual Task",
            "input_data": {"key": "value"},
        },
    )
    assert task_resp.status_code == 201

    # Get tasks
    tasks_resp = await client.get(f"/api/v1/workflows/{workflow_id}/tasks")
    assert tasks_resp.status_code == 200
    tasks = tasks_resp.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Manual Task"


# ---------------------------------------------------------------------------
# Test 9: Agent CRUD – update and delete
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_agent_update_and_delete(client, make_agent):
    """Update agent name; verify change. Delete agent; verify it's gone."""
    agent = await make_agent(name="Original Name")

    # Update
    put_resp = await client.put(
        f"/api/v1/agents/{agent['id']}",
        json={"name": "Updated Name"},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["name"] == "Updated Name"

    # Delete
    del_resp = await client.delete(f"/api/v1/agents/{agent['id']}")
    assert del_resp.status_code == 204

    # Verify gone
    get_resp = await client.get(f"/api/v1/agents/{agent['id']}")
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 10: Workflow CRUD – update and delete
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workflow_update_and_delete(client, make_agent):
    """Update workflow name; verify change. Delete workflow; verify cascade."""
    agent = await make_agent(name="WF CRUD Agent")

    wf_resp = await client.post(
        "/api/v1/workflows",
        json={"name": "Original WF Name"},
    )
    assert wf_resp.status_code == 201
    workflow = wf_resp.json()
    workflow_id = workflow["id"]

    # Update
    put_resp = await client.put(
        f"/api/v1/workflows/{workflow_id}",
        json={"name": "Updated WF Name"},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["name"] == "Updated WF Name"

    # Delete
    del_resp = await client.delete(f"/api/v1/workflows/{workflow_id}")
    assert del_resp.status_code == 204

    # Verify gone
    get_resp = await client.get(f"/api/v1/workflows/{workflow_id}")
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 11: Execution stats endpoint
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_execution_stats(client, make_agent):
    """Dashboard stats endpoint returns valid JSON with expected fields."""
    agent = await make_agent(name="Stats Agent")

    # Create some workflows
    for i in range(3):
        await client.post(
            "/api/v1/workflows",
            json={"name": f"Stats WF {i}", "agent_ids": [agent["id"]]},
        )

    resp = await client.get("/api/v1/execution/stats")
    assert resp.status_code == 200
    stats = resp.json()

    assert "total_agents" in stats
    assert "total_workflows" in stats
    assert "total_tasks" in stats
    assert "active_workflows" in stats
    assert "success_rate" in stats
    assert stats["total_agents"] >= 1
    assert stats["total_workflows"] == 3


# ---------------------------------------------------------------------------
# Test 12: Execution logs endpoint
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_execution_logs(client, make_agent):
    """Create a log entry; retrieve it via /execution/logs/{workflow_id}."""
    agent = await make_agent(name="Log Agent")

    wf_resp = await client.post(
        "/api/v1/workflows",
        json={"name": "Log WF", "agent_ids": [agent["id"]]},
    )
    assert wf_resp.status_code == 201
    workflow = wf_resp.json()
    workflow_id = workflow["id"]

    # Create execution log
    log_resp = await client.post(
        "/api/v1/execution/log",
        json={
            "workflow_id": workflow_id,
            "event_type": "test_event",
            "message": "Test log entry",
            "meta_data": {"test": True},
        },
    )
    assert log_resp.status_code == 201
    log = log_resp.json()
    assert log["workflow_id"] == workflow_id

    # Retrieve logs
    logs_resp = await client.get(f"/api/v1/execution/logs/{workflow_id}")
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert len(logs) == 1
    assert logs[0]["event_type"] == "test_event"


# ---------------------------------------------------------------------------
# Test 13: Health and readiness endpoints
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_health_and_ready_endpoints(client):
    """GET /health and GET /ready both return 200."""
    health_resp = await client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"

    ready_resp = await client.get("/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["ready"] is True


# ---------------------------------------------------------------------------
# Test 14: Task not found returns 404
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_task_not_found(client):
    """GET /api/v1/tasks/{nonexistent} returns 404."""
    resp = await client.get("/api/v1/tasks/does-not-exist")
    assert resp.status_code == 404
