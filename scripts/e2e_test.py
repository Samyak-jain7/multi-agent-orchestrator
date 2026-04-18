#!/usr/bin/env python3
"""E2E tests for multi-agent orchestrator"""
import asyncio
import httpx

API_BASE = "http://localhost:8000/api/v1"
FRONTEND = "http://localhost:3000"
API_KEY = "your-secure-app-api-key-here"
HEADERS = {"X-API-Key": API_KEY}

async def run():
    async with httpx.AsyncClient(timeout=30) as client:
        print("=== BACKEND API TESTS ===\n")

        r = await client.get(f"{API_BASE}/health")
        print(f"1. Health: {r.status_code} — {r.json()}")

        r = await client.post(
            f"{API_BASE}/auth/register",
            json={"email": "e2e@test.com", "password": "testpass123", "org_name": "E2E Org"}
        )
        print(f"2. Register: {r.status_code}")

        r = await client.post(
            f"{API_BASE}/auth/login",
            json={"email": "e2e@test.com", "password": "testpass123"}
        )
        print(f"3. Login: {r.status_code}")
        if r.status_code == 200:
            token = r.json().get("api_key")
            if token:
                HEADERS["X-API-Key"] = token

        r = await client.get(f"{API_BASE}/agents", headers=HEADERS)
        print(f"4. List agents: {r.status_code} — {len(r.json())} agents")

        r = await client.post(
            f"{API_BASE}/agents",
            headers=HEADERS,
            json={
                "name": "Research Agent",
                "description": "Web research agent",
                "model_provider": "openai",
                "model_name": "gpt-4o",
                "system_prompt": "You are a research agent.",
                "tool_ids": ["ddg_search"],
                "memory_enabled": True,
                "max_iterations": 5
            }
        )
        print(f"5. Create agent: {r.status_code}")
        agent_id = r.json().get("id") if r.status_code in (200,201) else None
        if agent_id:
            print(f"   agent_id: {agent_id}")

        r = await client.get(f"{API_BASE}/agents/tools", headers=HEADERS)
        tools = r.json()
        print(f"6. List tools: {r.status_code} — {len(tools)} tools")

        r = await client.post(
            f"{API_BASE}/workflows",
            headers=HEADERS,
            json={
                "name": "Research Pipeline",
                "description": "Research → Evaluate → Refine",
                "workflow_definition": {
                    "nodes": [
                        {"id": "supervisor", "type": "supervisor"},
                        {"id": "researcher", "type": "agent", "agent_id": agent_id, "tools": ["ddg_search"]},
                        {"id": "evaluator", "type": "agent", "agent_id": None, "tools": []}
                    ],
                    "edges": [
                        {"from": "supervisor", "to": "researcher"},
                        {"from": "researcher", "to": "evaluator"},
                        {"from": "evaluator", "to": "supervisor"}
                    ]
                },
                "memory_enabled": True
            }
        )
        print(f"7. Create workflow: {r.status_code}")
        workflow_id = r.json().get("id") if r.status_code in (200,201) else None
        if workflow_id:
            print(f"   workflow_id: {workflow_id}")

        if workflow_id:
            r = await client.get(f"{API_BASE}/workflows/{workflow_id}/memory", headers=HEADERS)
            print(f"8. Workflow memory: {r.status_code} — {r.json()}")

        r = await client.get(f"{API_BASE}/workflows", headers=HEADERS)
        print(f"9. List workflows: {r.status_code} — {len(r.json())} workflows")

        r = await client.get(f"{API_BASE}/tasks", headers=HEADERS)
        print(f"10. List tasks: {r.status_code}")

        print("\n=== FRONTEND TESTS ===\n")
        r = await client.get(FRONTEND)
        print(f"11. Frontend loads: {r.status_code}")
        r = await client.get(f"{FRONTEND}/api/v1/agents", timeout=10)
        print(f"12. Frontend /api proxy: {r.status_code}")

        print("\n✅ All E2E tests complete")

asyncio.run(run())
