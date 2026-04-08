const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  if (response.status === 204) {
    return null as T;
  }

  return response.json();
}

export const api = {
  agents: {
    list: () => fetchApi<any[]>('/agents'),
    get: (id: string) => fetchApi<any>(`/agents/${id}`),
    create: (data: any) => fetchApi<any>('/agents', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: any) => fetchApi<any>(`/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: string) => fetchApi<void>(`/agents/${id}`, { method: 'DELETE' }),
  },

  workflows: {
    list: () => fetchApi<any[]>('/workflows'),
    get: (id: string) => fetchApi<any>(`/workflows/${id}`),
    create: (data: any) => fetchApi<any>('/workflows', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: any) => fetchApi<any>(`/workflows/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: string) => fetchApi<void>(`/workflows/${id}`, { method: 'DELETE' }),
    execute: (id: string, data: any) => fetchApi<any>(`/workflows/${id}/execute`, { method: 'POST', body: JSON.stringify(data) }),
    getTasks: (id: string) => fetchApi<any[]>(`/workflows/${id}/tasks`),
  },

  tasks: {
    list: (params?: { workflow_id?: string; status_filter?: string }) => {
      const query = new URLSearchParams();
      if (params?.workflow_id) query.set('workflow_id', params.workflow_id);
      if (params?.status_filter) query.set('status_filter', params.status_filter);
      const qs = query.toString();
      return fetchApi<any[]>(`/tasks${qs ? `?${qs}` : ''}`);
    },
    get: (id: string) => fetchApi<any>(`/tasks/${id}`),
    create: (data: any) => fetchApi<any>('/tasks', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: any) => fetchApi<any>(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: string) => fetchApi<void>(`/tasks/${id}`, { method: 'DELETE' }),
    retry: (id: string) => fetchApi<any>(`/tasks/${id}/retry`, { method: 'POST' }),
  },

  execution: {
    getStats: () => fetchApi<any>('/execution/stats'),
    getTaskStatus: (taskId: string) => fetchApi<any>(`/execution/task/${taskId}/status`),
    getTaskEvents: (taskId: string, afterIndex?: number) => {
      const qs = afterIndex ? `?after_index=${afterIndex}` : '';
      return fetchApi<any>(`/execution/task/${taskId}/events${qs}`);
    },
    getLogs: (workflowId: string) => fetchApi<any[]>(`/execution/logs/${workflowId}`),
    streamTask: (taskId: string) => `${API_BASE}/execution/stream/${taskId}`,
    streamWorkflow: (workflowId: string) => `${API_BASE}/execution/stream/workflow/${workflowId}`,
  },
};
