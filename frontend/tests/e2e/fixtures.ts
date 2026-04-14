import { test as base, expect } from '@playwright/test';

export async function createTestAgent(
  request: any,
  options: {
    name?: string;
    provider?: string;
    model?: string;
    systemPrompt?: string;
  } = {}
) {
  const { name = `Test Agent ${Date.now()}`, provider = 'minimax', model = 'MiniMax-M2.7', systemPrompt = 'You are a test agent.' } = options;

  const response = await request.post('http://localhost:8000/api/v1/agents', {
    data: {
      name,
      model_provider: provider,
      model_name: model,
      system_prompt: systemPrompt,
    },
  });

  if (!response.ok()) {
    throw new Error(`Failed to create agent: ${response.status()} ${await response.text()}`);
  }

  return response.json();
}

export async function createTestWorkflow(
  request: any,
  agentId?: string
) {
  const response = await request.post('http://localhost:8000/api/v1/workflows', {
    data: {
      name: `Test Workflow ${Date.now()}`,
      description: 'Test workflow created by E2E tests',
      agent_ids: agentId ? [agentId] : [],
    },
  });

  if (!response.ok()) {
    throw new Error(`Failed to create workflow: ${response.status()} ${await response.text()}`);
  }

  return response.json();
}

export async function cleanupTestData(request: any) {
  try {
    const agentsResponse = await request.get('http://localhost:8000/api/v1/agents');
    if (agentsResponse.ok()) {
      const agents = await agentsResponse.json();
      for (const agent of agents) {
        if (agent.name?.startsWith('Test Agent') || agent.name?.startsWith('e2e-')) {
          await request.delete(`http://localhost:8000/api/v1/agents/${agent.id}`).catch(() => {});
        }
      }
    }
  } catch {}

  try {
    const workflowsResponse = await request.get('http://localhost:8000/api/v1/workflows');
    if (workflowsResponse.ok()) {
      const workflows = await workflowsResponse.json();
      for (const workflow of workflows) {
        if (workflow.name?.startsWith('Test Workflow') || workflow.name?.startsWith('e2e-')) {
          await request.delete(`http://localhost:8000/api/v1/workflows/${workflow.id}`).catch(() => {});
        }
      }
    }
  } catch {}

  try {
    const tasksResponse = await request.get('http://localhost:8000/api/v1/tasks');
    if (tasksResponse.ok()) {
      const tasks = await tasksResponse.json();
      for (const task of tasks) {
        if (task.title?.startsWith('Test Task') || task.title?.startsWith('e2e-')) {
          await request.delete(`http://localhost:8000/api/v1/tasks/${task.id}`).catch(() => {});
        }
      }
    }
  } catch {}
}

type TestFixtures = {
  createTestAgent: typeof createTestAgent;
  createTestWorkflow: typeof createTestWorkflow;
  cleanupTestData: typeof cleanupTestData;
};

export const test = base.extend<TestFixtures>({
  createTestAgent: async ({ request }, use) => {
    await use(createTestAgent);
  },
  createTestWorkflow: async ({ request }, use) => {
    await use(createTestWorkflow);
  },
  cleanupTestData: async ({ request }, use) => {
    await use(cleanupTestData);
  },
});

export { expect } from '@playwright/test';