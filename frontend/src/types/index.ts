export type LLMProvider = 'openai' | 'anthropic' | 'ollama';

export type AgentStatus = 'idle' | 'busy' | 'error';

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export type WorkflowStatus = 'idle' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  model_provider: LLMProvider;
  model_name: string;
  system_prompt: string;
  tools: ToolDefinition[];
  config: Record<string, unknown>;
  status: AgentStatus;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  workflow_id: string;
  agent_id: string;
  title: string;
  description: string | null;
  input_data: Record<string, unknown>;
  priority: number;
  dependencies: string[];
  status: TaskStatus;
  output: Record<string, unknown> | null;
  error: string | null;
  retry_count: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface Workflow {
  id: string;
  name: string;
  description: string | null;
  agent_ids: string[];
  config: Record<string, unknown>;
  status: WorkflowStatus;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface DashboardStats {
  total_agents: number;
  total_workflows: number;
  total_tasks: number;
  active_workflows: number;
  completed_tasks_today: number;
  failed_tasks_today: number;
  success_rate: number;
}

export interface ExecutionEvent {
  type: string;
  event_type?: string;
  workflow_id?: string;
  task_id?: string;
  agent_id?: string;
  message?: string;
  meta_data?: Record<string, unknown>;
  timestamp: string;
  status?: string;
  result?: unknown;
  error?: string;
}

export interface ExecutionLog {
  id: string;
  workflow_id: string;
  task_id: string | null;
  agent_id: string | null;
  event_type: string;
  message: string | null;
  meta_data: Record<string, unknown> | null;
  timestamp: string;
}

export interface CreateAgentRequest {
  name: string;
  description?: string;
  model_provider: LLMProvider;
  model_name: string;
  system_prompt: string;
  tools?: ToolDefinition[];
  config?: Record<string, unknown>;
}

export interface CreateWorkflowRequest {
  name: string;
  description?: string;
  agent_ids?: string[];
  config?: Record<string, unknown>;
}

export interface CreateTaskRequest {
  workflow_id: string;
  agent_id: string;
  title: string;
  description?: string;
  input_data?: Record<string, unknown>;
  priority?: number;
  dependencies?: string[];
}

export interface ExecuteWorkflowRequest {
  input_data: Record<string, unknown>;
}
