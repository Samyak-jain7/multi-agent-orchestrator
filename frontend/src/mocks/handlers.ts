import { http, HttpResponse } from 'msw';

const now = new Date().toISOString();

export const handlers = [
  // Agents
  http.get('/api/v1/agents', () =>
    HttpResponse.json([
      {
        id: 'agent-1',
        name: 'Test Agent',
        description: 'A test agent',
        model_provider: 'minimax',
        model_name: 'MiniMax-M2.7',
        system_prompt: 'You are a test agent',
        status: 'active',
        tools: [],
        created_at: now,
        updated_at: now,
      },
    ])
  ),
  http.post('/api/v1/agents', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({
      id: 'agent-new',
      name: body.name,
      description: body.description || '',
      model_provider: body.model_provider,
      model_name: body.model_name,
      system_prompt: body.system_prompt,
      status: 'active',
      tools: [],
      created_at: now,
      updated_at: now,
    }, { status: 201 });
  }),
  http.get('/api/v1/agents/:id', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      name: 'Test Agent',
      description: 'A test agent',
      model_provider: 'minimax',
      model_name: 'MiniMax-M2.7',
      system_prompt: 'You are a test agent',
      status: 'active',
      tools: [],
      created_at: now,
      updated_at: now,
    })
  ),
  http.put('/api/v1/agents/:id', async ({ request, params }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({
      id: params.id,
      name: body.name || 'Updated Agent',
      model_provider: body.model_provider || 'minimax',
      model_name: body.model_name || 'MiniMax-M2.7',
      system_prompt: body.system_prompt || 'You are a test agent',
      status: 'active',
      tools: [],
      created_at: now,
      updated_at: now,
    });
  }),
  http.delete('/api/v1/agents/:id', () => HttpResponse.json(null, { status: 204 })),

  // Workflows
  http.get('/api/v1/workflows', () => HttpResponse.json([])),
  http.post('/api/v1/workflows', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({
      id: 'workflow-new',
      name: body.name,
      description: body.description || '',
      agent_ids: body.agent_ids || [],
      created_at: now,
      updated_at: now,
    }, { status: 201 });
  }),
  http.get('/api/v1/workflows/:id', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      name: 'Test Workflow',
      description: 'A test workflow',
      agent_ids: ['agent-1'],
      created_at: now,
      updated_at: now,
    })
  ),
  http.put('/api/v1/workflows/:id', async ({ request, params }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({
      id: params.id,
      name: body.name || 'Updated Workflow',
      description: body.description || '',
      agent_ids: body.agent_ids || [],
      created_at: now,
      updated_at: now,
    });
  }),
  http.delete('/api/v1/workflows/:id', () => HttpResponse.json(null, { status: 204 })),
  http.post('/api/v1/workflows/:id/execute', ({ params }) =>
    HttpResponse.json({ task_id: `task-${params.id}-1` })
  ),
  http.get('/api/v1/workflows/:id/tasks', () => HttpResponse.json([])),

  // Tasks
  http.get('/api/v1/tasks', ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get('status_filter');
    const tasks = [
      { id: 'task-1', workflow_id: 'wf-1', status: 'pending', input_data: {}, created_at: now },
      { id: 'task-2', workflow_id: 'wf-1', status: 'failed', input_data: {}, created_at: now },
    ];
    if (status) return HttpResponse.json(tasks.filter(t => t.status === status));
    return HttpResponse.json(tasks);
  }),
  http.post('/api/v1/tasks', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({
      id: 'task-new',
      workflow_id: body.workflow_id,
      status: 'pending',
      input_data: body.input_data || {},
      created_at: now,
      updated_at: now,
    }, { status: 201 });
  }),
  http.get('/api/v1/tasks/:id', ({ params }) =>
    HttpResponse.json({
      id: params.id,
      workflow_id: 'wf-1',
      status: 'pending',
      input_data: {},
      output: null,
      created_at: now,
      updated_at: now,
    })
  ),
  http.put('/api/v1/tasks/:id', async ({ request, params }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({
      id: params.id,
      status: body.status || 'pending',
      input_data: {},
      updated_at: now,
    });
  }),
  http.delete('/api/v1/tasks/:id', () => HttpResponse.json(null, { status: 204 })),
  http.post('/api/v1/tasks/:id/retry', ({ params }) =>
    HttpResponse.json({ id: params.id, status: 'pending' })
  ),

  // Execution
  http.get('/api/v1/execution/stats', () =>
    HttpResponse.json({
      total_tasks: 5,
      completed: 3,
      failed: 1,
      running: 1,
      pending: 0,
      success_rate: 75,
      total_agents: 2,
      active_workflows: 3,
      completed_tasks_today: 10,
      failed_tasks_today: 2,
    })
  ),
  http.get('/api/v1/execution/task/:id/status', ({ params }) =>
    HttpResponse.json({ id: params.id, status: 'pending' })
  ),
  http.get('/api/v1/execution/task/:id/events', () =>
    HttpResponse.json([
      { type: 'task_started', data: {}, index: 0 },
    ])
  ),
  http.get('/api/v1/execution/logs/:workflowId', () => HttpResponse.json([])),
  http.post('/api/v1/execution/log', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({ id: 'log-1', ...body }, { status: 201 });
  }),
];
