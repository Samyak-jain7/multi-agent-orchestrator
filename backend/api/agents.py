"""
Agent CRUD API endpoints.
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from core.database import get_db
from models.execution import AgentModel, UserModel
from schemas import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentStatus,
    LLMProvider,
    ToolDefinition,
)
from agents.composio_manager import ComposioToolManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

async def get_current_user(
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[UserModel]:
    """Get current user from API key (optional)."""
    if not x_api_key:
        return None
    
    import hashlib
    hashed = hashlib.sha256(x_api_key.encode()).hexdigest()
    stmt = select(UserModel).where(UserModel.hashed_api_key == hashed)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=500, description="Max records to return"),
    owner_id: Optional[str] = Query(default=None, description="Filter by owner"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """List all agents with pagination. Optionally filter by owner."""
    stmt = select(AgentModel)
    
    # Multi-tenant: filter by owner_id if provided or if user is authenticated
    if owner_id:
        stmt = stmt.where(AgentModel.owner_id == owner_id)
    elif current_user:
        stmt = stmt.where(AgentModel.owner_id == current_user.org_id)
    
    stmt = stmt.offset(skip).limit(limit).order_by(AgentModel.created_at.desc())
    result = await db.execute(stmt)
    agents = result.scalars().all()

    return [
        AgentResponse(
            id=a.id,
            name=a.name,
            description=a.description,
            model_provider=LLMProvider(a.model_provider),
            model_name=a.model_name,
            system_prompt=a.system_prompt,
            tools=[ToolDefinition(**t) for t in (a.tools or [])],
            config=a.config or {},
            status=AgentStatus.IDLE,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in agents
    ]


@router.get("/tools", response_model=List[dict])
async def list_available_tools(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    search: Optional[str] = Query(default=None, description="Search by name/description"),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """
    List all available Composio tools that can be attached to agents.
    """
    manager = ComposioToolManager()
    
    if category:
        tools = manager.get_tools_by_category(category)
    elif search:
        tools = manager.search_tools(search)
    else:
        tools = manager.list_available_tools()
    
    return tools


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """Get a single agent by ID."""
    stmt = select(AgentModel).where(AgentModel.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        logger.warning(f"Agent not found: {agent_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    # Multi-tenant check
    if current_user and agent.owner_id and agent.owner_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        model_provider=LLMProvider(agent.model_provider),
        model_name=agent.model_name,
        system_prompt=agent.system_prompt,
        tools=[ToolDefinition(**t) for t in (agent.tools or [])],
        config=agent.config or {},
        status=AgentStatus.IDLE,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """Create a new agent."""
    logger.info(f"Creating agent: name={agent_data.name!r}, provider={agent_data.model_provider.value}")
    
    # Determine owner_id
    owner_id = None
    if current_user:
        owner_id = current_user.org_id
    
    agent = AgentModel(
        name=agent_data.name,
        description=agent_data.description,
        model_provider=agent_data.model_provider.value,
        model_name=agent_data.model_name,
        system_prompt=agent_data.system_prompt,
        tools=[t.model_dump() for t in agent_data.tools],
        config=agent_data.config,
        # New fields (with defaults)
        tool_ids=[],
        memory_enabled=True,
        max_iterations=5,
        temperature=0.7,
        owner_id=owner_id,
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    logger.info(f"Agent created: id={agent.id}")

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        model_provider=LLMProvider(agent.model_provider),
        model_name=agent.model_name,
        system_prompt=agent.system_prompt,
        tools=[ToolDefinition(**t) for t in (agent.tools or [])],
        config=agent.config or {},
        status=AgentStatus.IDLE,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """Update an existing agent."""
    stmt = select(AgentModel).where(AgentModel.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        logger.warning(f"Update failed – agent not found: {agent_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    # Multi-tenant check
    if current_user and agent.owner_id and agent.owner_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    update_dict = agent_data.model_dump(exclude_unset=True)

    if "model_provider" in update_dict and update_dict["model_provider"]:
        update_dict["model_provider"] = update_dict["model_provider"].value
    if "tools" in update_dict and update_dict["tools"]:
        update_dict["tools"] = [
            t.model_dump() if hasattr(t, "model_dump") else t
            for t in update_dict["tools"]
        ]

    update_dict["updated_at"] = datetime.utcnow()

    for key, value in update_dict.items():
        setattr(agent, key, value)

    await db.commit()
    await db.refresh(agent)
    logger.info(f"Agent updated: id={agent.id}")

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        model_provider=LLMProvider(agent.model_provider),
        model_name=agent.model_name,
        system_prompt=agent.system_prompt,
        tools=[ToolDefinition(**t) for t in (agent.tools or [])],
        config=agent.config or {},
        status=AgentStatus.IDLE,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """Delete an agent."""
    stmt = select(AgentModel).where(AgentModel.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        logger.warning(f"Delete failed – agent not found: {agent_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    # Multi-tenant check
    if current_user and agent.owner_id and agent.owner_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    await db.execute(delete(AgentModel).where(AgentModel.id == agent_id))
    await db.commit()
    logger.info(f"Agent deleted: id={agent_id}")


@router.post("/{agent_id}/tools", response_model=AgentResponse)
async def attach_tools_to_agent(
    agent_id: str,
    tool_ids: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user),
):
    """
    Attach Composio tools to an agent.
    
    This replaces the existing tool_ids list for the agent.
    """
    stmt = select(AgentModel).where(AgentModel.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    # Multi-tenant check
    if current_user and agent.owner_id and agent.owner_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Validate tools
    manager = ComposioToolManager()
    validated = manager.validate_tools(tool_ids)
    invalid = [tid for tid, available in validated.items() if not available]
    
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tools: {invalid}",
        )

    # Update agent tools
    agent.tool_ids = tool_ids
    agent.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(agent)
    
    logger.info(f"Agent {agent_id} tools updated: {tool_ids}")
    
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        model_provider=LLMProvider(agent.model_provider),
        model_name=agent.model_name,
        system_prompt=agent.system_prompt,
        tools=[ToolDefinition(**t) for t in (agent.tools or [])],
        config=agent.config or {},
        status=AgentStatus.IDLE,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )
