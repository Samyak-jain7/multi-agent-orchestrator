from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, Float, Boolean, Enum as SAEnum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid
import enum

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Multi-tenant Models (User & Organization)
# ---------------------------------------------------------------------------


class OrganizationModel(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    plan = Column(String, nullable=False, default="free")  # free, pro, enterprise
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, nullable=False, unique=True)
    hashed_api_key = Column(String, nullable=False)
    org_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False, default="member")  # admin, member
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Enhanced Agent Model
# ---------------------------------------------------------------------------


class AgentModel(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    model_provider = Column(String, nullable=False, default="minimax")
    model_name = Column(String, nullable=False, default="MiniMax-M2.7")
    system_prompt = Column(Text, nullable=False)
    # Enhanced fields for proper agent architecture
    tool_ids = Column(JSON, nullable=True, default=list)  # Composio tool names
    memory_enabled = Column(Boolean, nullable=False, default=True)
    max_iterations = Column(Integer, nullable=False, default=5)
    temperature = Column(Float, nullable=False, default=0.7)
    # Legacy fields (kept for backward compatibility)
    tools = Column(JSON, nullable=True, default=list)
    config = Column(JSON, nullable=True, default=dict)
    # Multi-tenant ownership
    owner_id = Column(String, nullable=True, index=True)  # user/org that owns this agent
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Task Model (unchanged)
# ---------------------------------------------------------------------------


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    input_data = Column(JSON, nullable=True, default=dict)
    status = Column(String, nullable=False, default="pending")
    priority = Column(Integer, nullable=False, default=0)
    dependencies = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    output = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)


# ---------------------------------------------------------------------------
# Enhanced Workflow Model
# ---------------------------------------------------------------------------


class WorkflowStatus(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowModel(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="idle")
    # DAG definition as JSON — replaces simple agent_ids list
    workflow_definition = Column(JSON, nullable=True, default=dict)
    # {
    #   "nodes": [
    #     {"id": "supervisor", "type": "supervisor", "config": {...}},
    #     {"id": "agent_1", "type": "agent", "agent_id": "...", "tools": ["google_search"]},
    #   ],
    #   "edges": [
    #     {"from": "supervisor", "to": "agent_1", "condition": null},
    #     {"from": "agent_1", "to": "supervisor", "condition": "needs_research"},
    #   ]
    # }
    agent_ids = Column(JSON, nullable=False, default=list)  # Legacy compatibility
    config = Column(JSON, nullable=True, default=dict)
    memory_enabled = Column(Boolean, nullable=False, default=True)
    max_iterations = Column(Integer, nullable=False, default=10)
    # Multi-tenant ownership
    owner_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    output = Column(JSON, nullable=True)


class ExecutionLogModel(Base):
    __tablename__ = "execution_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, nullable=False, index=True)
    task_id = Column(String, nullable=True, index=True)
    agent_id = Column(String, nullable=True)
    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    meta_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
