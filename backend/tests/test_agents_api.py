"""
Tests for /api/v1/agents endpoints.
"""
import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# POST /api/v1/agents
# ---------------------------------------------------------------------------

async def test_create_agent_happy_path(client: AsyncClient, sample_agent_data):
    response = await client.post("/api/v1/agents", json=sample_agent_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_agent_data["name"]
    assert data["description"] == sample_agent_data["description"]
    assert data["model_provider"] == sample_agent_data["model_provider"]
    assert data["model_name"] == sample_agent_data["model_name"]
    assert data["system_prompt"] == sample_agent_data["system_prompt"]
    assert data["status"] == "idle"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


async def test_create_agent_minimal(client: AsyncClient):
    """Create agent with only required fields."""
    response = await client.post(
        "/api/v1/agents",
        json={
            "name": "Minimal Agent",
            "system_prompt": "Be helpful.",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Agent"
    assert data["model_provider"] == "minimax"  # default
    assert data["model_name"] == "MiniMax-M2.7"  # default


async def test_create_agent_missing_name(client: AsyncClient):
    response = await client.post(
        "/api/v1/agents",
        json={"system_prompt": "Be helpful."},
    )
    assert response.status_code == 422


async def test_create_agent_missing_system_prompt(client: AsyncClient):
    response = await client.post(
        "/api/v1/agents",
        json={"name": "No Prompt Agent"},
    )
    assert response.status_code == 422


async def test_create_agent_empty_name(client: AsyncClient):
    response = await client.post(
        "/api/v1/agents",
        json={"name": "", "system_prompt": "Be helpful."},
    )
    assert response.status_code == 422


async def test_create_agent_unsupported_provider(client: AsyncClient, sample_agent_data):
    sample_agent_data["model_provider"] = "unsupported_provider"
    response = await client.post("/api/v1/agents", json=sample_agent_data)
    assert response.status_code == 422


async def test_create_agent_all_providers_valid(client: AsyncClient):
    """Verify each supported LLMProvider enum value is accepted."""
    for provider in ["openai", "anthropic", "ollama", "minimax"]:
        response = await client.post(
            "/api/v1/agents",
            json={
                "name": f"Agent-{provider}",
                "system_prompt": "Test",
                "model_provider": provider,
            },
        )
        assert response.status_code == 201, f"Provider {provider} should be valid"


async def test_create_agent_with_tools(client: AsyncClient, sample_agent_data):
    sample_agent_data["tools"] = [
        {"name": "web_search", "description": "Search the web", "parameters": {"type": "object"}},
        {"name": "calculator", "description": "Do math", "parameters": {}},
    ]
    response = await client.post("/api/v1/agents", json=sample_agent_data)
    assert response.status_code == 201
    data = response.json()
    assert len(data["tools"]) == 2
    assert data["tools"][0]["name"] == "web_search"


# ---------------------------------------------------------------------------
# GET /api/v1/agents
# ---------------------------------------------------------------------------

async def test_list_agents_empty(client: AsyncClient):
    response = await client.get("/api/v1/agents")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_agents_with_items(client: AsyncClient, sample_agent_data):
    # Create two agents
    await client.post("/api/v1/agents", json=sample_agent_data)
    await client.post(
        "/api/v1/agents",
        json={**sample_agent_data, "name": "Second Agent"},
    )
    response = await client.get("/api/v1/agents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


async def test_list_agents_pagination(client: AsyncClient, sample_agent_data):
    # Create 5 agents
    for i in range(5):
        await client.post(
            "/api/v1/agents",
            json={**sample_agent_data, "name": f"Agent-{i}"},
        )

    # Skip 2, limit 2
    response = await client.get("/api/v1/agents?skip=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Check total via headers or just verify IDs are distinct
    ids = [a["id"] for a in data]
    assert len(set(ids)) == 2


async def test_list_agents_pagination_skip_only(client: AsyncClient, sample_agent_data):
    # Create 3 agents
    for i in range(3):
        await client.post(
            "/api/v1/agents",
            json={**sample_agent_data, "name": f"Agent-{i}"},
        )
    response = await client.get("/api/v1/agents?skip=1")
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_agents_pagination_limit_only(client: AsyncClient, sample_agent_data):
    for i in range(3):
        await client.post(
            "/api/v1/agents",
            json={**sample_agent_data, "name": f"Agent-{i}"},
        )
    response = await client.get("/api/v1/agents?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_agents_pagination_limit_max(client: AsyncClient):
    """limit > 500 should be rejected."""
    response = await client.get("/api/v1/agents?limit=501")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/agents/{id}
# ---------------------------------------------------------------------------

async def test_get_agent_found(client: AsyncClient, sample_agent_data):
    create_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/agents/{agent_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == agent_id
    assert data["name"] == sample_agent_data["name"]


async def test_get_agent_not_found(client: AsyncClient):
    response = await client.get("/api/v1/agents/nonexistent-id-abc123")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# PUT /api/v1/agents/{id}
# ---------------------------------------------------------------------------

async def test_update_agent_partial(client: AsyncClient, sample_agent_data):
    create_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/agents/{agent_id}",
        json={"name": "Updated Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    # Other fields unchanged
    assert data["system_prompt"] == sample_agent_data["system_prompt"]


async def test_update_agent_full(client: AsyncClient, sample_agent_data):
    create_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = create_resp.json()["id"]

    updated_data = {
        "name": "Fully Updated Agent",
        "description": "New description",
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "system_prompt": "Updated prompt.",
        "config": {"temperature": 0.9},
    }
    response = await client.put(f"/api/v1/agents/{agent_id}", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Fully Updated Agent"
    assert data["model_provider"] == "openai"


async def test_update_agent_not_found(client: AsyncClient):
    response = await client.put(
        "/api/v1/agents/nonexistent-id-xyz",
        json={"name": "Updated"},
    )
    assert response.status_code == 404


async def test_update_agent_invalid_provider(client: AsyncClient, sample_agent_data):
    create_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/agents/{agent_id}",
        json={"model_provider": "invalid_provider"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/agents/{id}
# ---------------------------------------------------------------------------

async def test_delete_agent_success(client: AsyncClient, sample_agent_data):
    create_resp = await client.post("/api/v1/agents", json=sample_agent_data)
    agent_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/agents/{agent_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/api/v1/agents/{agent_id}")
    assert get_resp.status_code == 404


async def test_delete_agent_not_found(client: AsyncClient):
    response = await client.delete("/api/v1/agents/nonexistent-id-xyz")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

async def test_auth_missing_api_key(unauthenticated_client: AsyncClient):
    """Requests without X-API-Key header should be rejected when APP_API_KEY is set."""
    response = await unauthenticated_client.get("/api/v1/agents")
    assert response.status_code == 403


async def test_auth_wrong_api_key(wrong_auth_client: AsyncClient):
    """Requests with wrong X-API-Key should be rejected."""
    response = await wrong_auth_client.get("/api/v1/agents")
    assert response.status_code == 403


async def test_auth_correct_api_key(client: AsyncClient):
    """Requests with correct X-API-Key should succeed."""
    response = await client.get("/api/v1/agents")
    assert response.status_code == 200
