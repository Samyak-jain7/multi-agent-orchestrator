import { Page, APIRequestContext } from '@playwright/test';

const API_BASE = 'http://localhost:8000/api/v1';

export async function createTestAgent(
  request: APIRequestContext,
  options: {
    name?: string;
    provider?: string;
    model?: string;
    systemPrompt?: string;
    description?: string;
  } = {}
) {
  const {
    name = `e2e-agent-${Date.now()}`,
    provider = 'minimax',
    model = 'MiniMax-M2.7',
    systemPrompt = 'You are a test agent for E2E testing.',
    description = 'Created by E2E test suite',
  } = options;

  const response = await request.post(`${API_BASE}/agents`, {
    data: {
      name,
      description,
      model_provider: provider,
      model_name: model,
      system_prompt: systemPrompt,
    },
    headers: getAuthHeaders(),
  });

  if (!response.ok()) {
    throw new Error(`Failed to create agent: ${response.status()} ${await response.text()}`);
  }

  return response.json();
}

export async function createTestWorkflow(
  request: APIRequestContext,
  agentIds: string[] = []
) {
  const response = await request.post(`${API_BASE}/workflows`, {
    data: {
      name: `e2e-workflow-${Date.now()}`,
      description: 'Created by E2E test suite',
      agent_ids: agentIds,
    },
    headers: getAuthHeaders(),
  });

  if (!response.ok()) {
    throw new Error(`Failed to create workflow: ${response.status()} ${await response.text()}`);
  }

  return response.json();
}

export async function createTestTask(
  request: APIRequestContext,
  options: {
    workflowId: string;
    agentId: string;
    title?: string;
    inputData?: Record<string, unknown>;
    priority?: number;
  }
) {
  const { workflowId, agentId, title = `e2e-task-${Date.now()}`, inputData = {}, priority = 0 } = options;

  const response = await request.post(`${API_BASE}/tasks`, {
    data: {
      workflow_id: workflowId,
      agent_id: agentId,
      title,
      description: 'Created by E2E test suite',
      input_data: inputData,
      priority,
    },
    headers: getAuthHeaders(),
  });

  if (!response.ok()) {
    throw new Error(`Failed to create task: ${response.status()} ${await response.text()}`);
  }

  return response.json();
}

export async function cleanupTestData(request: APIRequestContext) {
  const headers = getAuthHeaders();

  // Clean up in parallel
  await Promise.all([
    // Clean up agents
    (async () => {
      try {
        const response = await request.get(`${API_BASE}/agents`, { headers });
        if (response.ok()) {
          const agents = await response.json();
          await Promise.all(
            agents
              .filter((a: any) => a.name?.startsWith('e2e-'))
              .map((a: any) =>
                request.delete(`${API_BASE}/agents/${a.id}`, { headers }).catch(() => {})
              )
          );
        }
      } catch {}
    })(),

    // Clean up workflows
    (async () => {
      try {
        const response = await request.get(`${API_BASE}/workflows`, { headers });
        if (response.ok()) {
          const workflows = await response.json();
          await Promise.all(
            workflows
              .filter((w: any) => w.name?.startsWith('e2e-'))
              .map((w: any) =>
                request.delete(`${API_BASE}/workflows/${w.id}`, { headers }).catch(() => {})
              )
          );
        }
      } catch {}
    })(),

    // Clean up tasks
    (async () => {
      try {
        const response = await request.get(`${API_BASE}/tasks`, { headers });
        if (response.ok()) {
          const tasks = await response.json();
          await Promise.all(
            tasks
              .filter((t: any) => t.title?.startsWith('e2e-'))
              .map((t: any) =>
                request.delete(`${API_BASE}/tasks/${t.id}`, { headers }).catch(() => {})
              )
          );
        }
      } catch {}
    })(),
  ]);
}

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (process.env.APP_API_KEY) {
    headers['X-API-Key'] = process.env.APP_API_KEY;
  }

  return headers;
}