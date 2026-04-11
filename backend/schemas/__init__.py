from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    MINIMAX = "minimax"


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    model_provider: LLMProvider = LLMProvider.MINIMAX
    model_name: str = "MiniMax-M2.7"
    system_prompt: str = Field(..., min_length=1)
    tools: List[ToolDefinition] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    model_provider: Optional[LLMProvider] = None
    model_name: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=1)
    tools: Optional[List[ToolDefinition]] = None
    config: Optional[Dict[str, Any]] = None


class AgentResponse(AgentBase):
    id: str
    status: AgentStatus = AgentStatus.IDLE
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0)
    dependencies: List[str] = Field(default_factory=list)


class TaskCreate(TaskBase):
    workflow_id: str
    agent_id: str


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    priority: Optional[int] = Field(None, ge=0)
    dependencies: Optional[List[str]] = None
    status: Optional[TaskStatus] = None


class TaskResponse(TaskBase):
    id: str
    workflow_id: str
    agent_id: str
    status: TaskStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkflowBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    agent_ids: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    agent_ids: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


class WorkflowResponse(WorkflowBase):
    id: str
    status: WorkflowStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkflowExecuteRequest(BaseModel):
    input_data: Dict[str, Any] = Field(default_factory=dict)
    task_overrides: Optional[List[Dict[str, Any]]] = None


class ExecutionEvent(BaseModel):
    event_type: str
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    message: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutionLogResponse(BaseModel):
    id: str
    workflow_id: str
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    event_type: str
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_agents: int
    total_workflows: int
    total_tasks: int
    active_workflows: int
    completed_tasks_today: int
    failed_tasks_today: int
    success_rate: float
