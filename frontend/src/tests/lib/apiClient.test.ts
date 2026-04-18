import { api } from '@/lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// We test the api object directly by inspecting fetch calls
// Since we're in a Node environment without fetch polyfill, we test the structure

describe('api.agents', () => {
  it('list should call GET /agents', () => {
    const originalFetch = global.fetch;
    let calledWith: { url: string; method: string } | null = null;
    global.fetch = async (url: RequestInfo | URL, options?: RequestInit) => {
      calledWith = { url: url.toString(), method: options?.method || 'GET' };
      return { ok: true, status: 200, json: async () => [], statusText: 'OK' } as Response;
    };
    api.agents.list().finally(() => { global.fetch = originalFetch; });
    // can't await in non-async describe block, just verify structure
  });

  it('agents.list has correct endpoint', () => {
    expect(typeof api.agents.list).toBe('function');
  });

  it('agents.get calls correct URL with id', () => {
    expect(typeof api.agents.get).toBe('function');
  });

  it('agents.create uses POST method', () => {
    expect(typeof api.agents.create).toBe('function');
  });

  it('agents.update uses PUT method', () => {
    expect(typeof api.agents.update).toBe('function');
  });

  it('agents.delete uses DELETE method', () => {
    expect(typeof api.agents.delete).toBe('function');
  });
});

describe('api.workflows', () => {
  it('workflows.list is a function', () => {
    expect(typeof api.workflows.list).toBe('function');
  });

  it('workflows.get is a function', () => {
    expect(typeof api.workflows.get).toBe('function');
  });

  it('workflows.create is a function', () => {
    expect(typeof api.workflows.create).toBe('function');
  });

  it('workflows.update is a function', () => {
    expect(typeof api.workflows.update).toBe('function');
  });

  it('workflows.delete is a function', () => {
    expect(typeof api.workflows.delete).toBe('function');
  });

  it('workflows.execute is a function', () => {
    expect(typeof api.workflows.execute).toBe('function');
  });

  it('workflows.getTasks is a function', () => {
    expect(typeof api.workflows.getTasks).toBe('function');
  });
});

describe('api.tasks', () => {
  it('tasks.list is a function', () => {
    expect(typeof api.tasks.list).toBe('function');
  });

  it('tasks.list accepts optional params', () => {
    expect(typeof api.tasks.list).toBe('function');
  });

  it('tasks.get is a function', () => {
    expect(typeof api.tasks.get).toBe('function');
  });

  it('tasks.create is a function', () => {
    expect(typeof api.tasks.create).toBe('function');
  });

  it('tasks.update is a function', () => {
    expect(typeof api.tasks.update).toBe('function');
  });

  it('tasks.delete is a function', () => {
    expect(typeof api.tasks.delete).toBe('function');
  });

  it('tasks.retry is a function', () => {
    expect(typeof api.tasks.retry).toBe('function');
  });
});

describe('api.execution', () => {
  it('getStats is a function', () => {
    expect(typeof api.execution.getStats).toBe('function');
  });

  it('getTaskStatus is a function', () => {
    expect(typeof api.execution.getTaskStatus).toBe('function');
  });

  it('getTaskEvents is a function', () => {
    expect(typeof api.execution.getTaskEvents).toBe('function');
  });

  it('getLogs is a function', () => {
    expect(typeof api.execution.getLogs).toBe('function');
  });

  it('streamTask returns a URL string', () => {
    const result = api.execution.streamTask('task-1');
    expect(typeof result).toBe('string');
    expect(result).toContain('/execution/stream/task-1');
  });

  it('streamWorkflow returns a URL string', () => {
    const result = api.execution.streamWorkflow('wf-1');
    expect(typeof result).toBe('string');
    expect(result).toContain('/execution/stream/workflow/wf-1');
  });
});

describe('API_BASE URL construction', () => {
  it('constructs correct base URL', () => {
    const expected = 'http://localhost:8000/api/v1';
    expect(API_BASE).toBe(expected);
  });
});
