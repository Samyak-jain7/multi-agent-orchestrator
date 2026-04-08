from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from datetime import datetime

from core.database import get_db
from models.execution import AgentModel
from schemas import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentStatus,
    LLMProvider,
    ToolDefinition
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AgentModel).offset(skip).limit(limit).order_by(AgentModel.created_at.desc())
    result = await db.execute(stmt)
    agents = result.scalars().all()

    return [
        AgentResponse(
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
            updated_at=agent.updated_at
        )
        for agent in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AgentModel).where(AgentModel.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
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
        updated_at=agent.updated_at
    )


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(agent_data: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent = AgentModel(
        name=agent_data.name,
        description=agent_data.description,
        model_provider=agent_data.model_provider.value,
        model_name=agent_data.model_name,
        system_prompt=agent_data.system_prompt,
        tools=[t.model_dump() for t in agent_data.tools],
        config=agent_data.config
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)

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
        updated_at=agent.updated_at
    )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AgentModel).where(AgentModel.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    update_dict = agent_data.model_dump(exclude_unset=True)

    if "model_provider" in update_dict and update_dict["model_provider"]:
        update_dict["model_provider"] = update_dict["model_provider"].value
    if "tools" in update_dict and update_dict["tools"]:
        update_dict["tools"] = [t.model_dump() if hasattr(t, 'model_dump') else t for t in update_dict["tools"]]

    update_dict["updated_at"] = datetime.utcnow()

    for key, value in update_dict.items():
        setattr(agent, key, value)

    await db.commit()
    await db.refresh(agent)

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
        updated_at=agent.updated_at
    )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AgentModel).where(AgentModel.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    await db.execute(delete(AgentModel).where(AgentModel.id == agent_id))
    await db.commit()
