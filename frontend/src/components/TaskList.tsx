'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Select } from '@/components/ui/Select';
import { Modal } from '@/components/ui/Modal';
import { Plus, Trash2, RefreshCw, Loader2, ListTodo } from 'lucide-react';
import { getStatusColor, formatRelativeTime, formatDate } from '@/lib/utils';
import type { Task } from '@/types';

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <Card>
      <CardContent>
        <div className="empty-state">
          <ListTodo className="empty-state-icon" style={{ width: '48px', height: '48px' }} />
          <h3>No tasks found</h3>
          <p>Tasks will appear here when workflows are executed</p>
          <Button onClick={onCreate} style={{ marginTop: '8px' }}>
            <Plus className="h-4 w-4" />
            Create Task
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function LoadingSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {[1, 2, 3].map((i) => (
        <div key={i} className="card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <div>
              <div className="skeleton" style={{ height: '18px', width: '200px', marginBottom: '6px' }} />
              <div className="skeleton" style={{ height: '14px', width: '300px' }} />
            </div>
            <div className="skeleton" style={{ height: '22px', width: '80px' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
            {[1, 2, 3, 4].map((j) => (
              <div key={j}>
                <div className="skeleton" style={{ height: '12px', width: '60px', marginBottom: '4px' }} />
                <div className="skeleton" style={{ height: '14px', width: '80px' }} />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function TaskList() {
  const queryClient = useQueryClient();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks', statusFilter],
    queryFn: () => api.tasks.list(statusFilter ? { status_filter: statusFilter } : undefined),
  });

  const { data: workflows } = useQuery({
    queryKey: ['workflows'],
    queryFn: api.workflows.list,
  });

  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: api.agents.list,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.tasks.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const retryMutation = useMutation({
    mutationFn: (id: string) => api.tasks.retry(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const getAgentName = (agentId: string) => {
    const agent = agents?.find((a: any) => a.id === agentId);
    return agent?.name || agentId;
  };

  const getWorkflowName = (workflowId: string) => {
    const workflow = workflows?.find((w: any) => w.id === workflowId);
    return workflow?.name || workflowId;
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="page-header">
          <h2>Tasks</h2>
          <p>View and manage individual task executions</p>
        </div>
        <LoadingSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <h2>Tasks</h2>
          <p>View and manage individual task executions</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="h-4 w-4" />
          Create Task
        </Button>
      </div>

      <div style={{ display: 'flex', gap: '12px' }}>
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          options={[
            { value: '', label: 'All Statuses' },
            { value: 'pending', label: 'Pending' },
            { value: 'running', label: 'Running' },
            { value: 'completed', label: 'Completed' },
            { value: 'failed', label: 'Failed' },
            { value: 'cancelled', label: 'Cancelled' },
          ]}
          style={{ width: '180px' }}
        />
      </div>

      {tasks && tasks.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {tasks.map((task: Task, idx: number) => (
            <Card key={task.id} className="card-animate" style={{ animationDelay: `${idx * 50}ms` }}>
              <CardHeader>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                  <div style={{ flex: 1 }}>
                    <CardTitle style={{ fontSize: '0.95rem' }}>{task.title}</CardTitle>
                    {task.description && (
                      <CardDescription style={{ marginTop: '4px', display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {task.description}
                      </CardDescription>
                    )}
                  </div>
                  <Badge className={getStatusColor(task.status)} style={{ marginLeft: '12px', flexShrink: 0 }}>
                    {task.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '16px' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Workflow</span>
                    <p style={{ fontWeight: 500, fontSize: '0.875rem', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {getWorkflowName(task.workflow_id)}
                    </p>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Agent</span>
                    <p style={{ fontWeight: 500, fontSize: '0.875rem', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {getAgentName(task.agent_id)}
                    </p>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Created</span>
                    <p className="mono-value" style={{ fontSize: '0.8rem', marginTop: '2px' }}>{formatRelativeTime(task.created_at)}</p>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Priority</span>
                    <p style={{ fontWeight: 500, fontSize: '0.875rem', marginTop: '2px' }}>{task.priority}</p>
                  </div>
                </div>

                {task.status === 'failed' && task.error && (
                  <div className="alert-error" style={{ marginTop: '12px' }}>
                    <p style={{ fontSize: '0.8rem', fontFamily: 'JetBrains Mono, monospace' }}>Error: {task.error}</p>
                  </div>
                )}

                {task.status === 'completed' && task.output && (
                  <div className="alert-success" style={{ marginTop: '12px' }}>
                    <p style={{ fontSize: '0.8rem', fontWeight: 500, marginBottom: '4px' }}>Output:</p>
                    <pre style={{ fontSize: '0.75rem', fontFamily: 'JetBrains Mono, monospace', overflow: 'hidden', maxHeight: '80px' }}>
                      {JSON.stringify(task.output, null, 2).slice(0, 300)}
                      {JSON.stringify(task.output).length > 300 ? '...' : ''}
                    </pre>
                  </div>
                )}
              </CardContent>
              <CardFooter>
                <Button variant="outline" size="sm" onClick={() => setSelectedTask(task)}>
                  View Details
                </Button>
                {task.status === 'failed' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => retryMutation.mutate(task.id)}
                    disabled={retryMutation.isPending}
                    style={{ marginLeft: '8px' }}
                  >
                    <RefreshCw className="h-4 w-4" />
                    Retry
                  </Button>
                )}
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteMutation.mutate(task.id)}
                  disabled={deleteMutation.isPending}
                  style={{ marginLeft: '8px' }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent>
            <div className="empty-state">
              <ListTodo className="empty-state-icon" style={{ width: '48px', height: '48px' }} />
              <h3>No tasks found</h3>
              <p>{statusFilter ? 'Try a different filter' : 'Tasks will appear here when workflows are executed'}</p>
            </div>
          </CardContent>
        </Card>
      )}

      <CreateTaskModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        workflows={workflows || []}
        agents={agents || []}
      />

      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          isOpen={!!selectedTask}
          onClose={() => setSelectedTask(null)}
          agentName={getAgentName(selectedTask.agent_id)}
          workflowName={getWorkflowName(selectedTask.workflow_id)}
        />
      )}
    </div>
  );
}

function CreateTaskModal({
  isOpen,
  onClose,
  workflows,
  agents,
}: {
  isOpen: boolean;
  onClose: () => void;
  workflows: any[];
  agents: any[];
}) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    workflow_id: '',
    agent_id: '',
    title: '',
    description: '',
    input_data: '{}',
    priority: 0,
  });
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (data: any) => api.tasks.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      onClose();
      setFormData({
        workflow_id: '',
        agent_id: '',
        title: '',
        description: '',
        input_data: '{}',
        priority: 0,
      });
      setError(null);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const parsedInput = JSON.parse(formData.input_data);
      createMutation.mutate({
        ...formData,
        input_data: parsedInput,
      });
    } catch {
      setError('Invalid JSON format for input data');
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Task">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div className="form-group">
            <label className="form-label">Workflow</label>
            <Select
              value={formData.workflow_id}
              onChange={(e) => setFormData({ ...formData, workflow_id: e.target.value })}
              options={[
                { value: '', label: 'Select workflow' },
                ...workflows.map((w: any) => ({ value: w.id, label: w.name })),
              ]}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Agent</label>
            <Select
              value={formData.agent_id}
              onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
              options={[
                { value: '', label: 'Select agent' },
                ...agents.map((a: any) => ({ value: a.id, label: a.name })),
              ]}
              required
            />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Title</label>
          <Input
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            placeholder="Research market trends"
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Description</label>
          <Textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Analyze current market trends for AI products"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Input Data (JSON)</label>
          <Textarea
            value={formData.input_data}
            onChange={(e) => {
              setFormData({ ...formData, input_data: e.target.value });
              setError(null);
            }}
            placeholder='{"query": "AI trends"}'
            style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.8125rem' }}
          />
          {error && <p className="form-error">{error}</p>}
        </div>

        <div className="form-group">
          <label className="form-label">Priority</label>
          <Input
            type="number"
            value={formData.priority}
            onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
            min={0}
          />
        </div>

        <div className="form-actions">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending && <Loader2 className="h-4 w-4" style={{ marginRight: '6px' }} />}
            Create
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function TaskDetailModal({
  task,
  isOpen,
  onClose,
  agentName,
  workflowName,
}: {
  task: Task;
  isOpen: boolean;
  onClose: () => void;
  agentName: string;
  workflowName: string;
}) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={task.title} className="modal-wide">
      <div className="space-y-4">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Badge className={getStatusColor(task.status)}>{task.status}</Badge>
          {task.retry_count > 0 && (
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Retry count: {task.retry_count}
            </span>
          )}
        </div>

        {task.description && (
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Description</label>
            <p style={{ fontSize: '0.9rem' }}>{task.description}</p>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Workflow</label>
            <p style={{ fontSize: '0.9rem' }}>{workflowName}</p>
          </div>
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Agent</label>
            <p style={{ fontSize: '0.9rem' }}>{agentName}</p>
          </div>
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Priority</label>
            <p style={{ fontSize: '0.9rem' }}>{task.priority}</p>
          </div>
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Dependencies</label>
            <p style={{ fontSize: '0.9rem' }}>
              {task.dependencies?.length > 0 ? task.dependencies.join(', ') : 'None'}
            </p>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Created</label>
            <p className="mono-value" style={{ fontSize: '0.8rem' }}>{formatDate(task.created_at)}</p>
          </div>
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Started</label>
            <p className="mono-value" style={{ fontSize: '0.8rem' }}>{formatDate(task.started_at)}</p>
          </div>
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Completed</label>
            <p className="mono-value" style={{ fontSize: '0.8rem' }}>{formatDate(task.completed_at)}</p>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Input Data</label>
          <pre className="code-block" style={{ marginTop: '6px' }}>
            {JSON.stringify(task.input_data, null, 2)}
          </pre>
        </div>

        {task.error && (
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--danger)' }}>Error</label>
            <pre className="code-block" style={{ marginTop: '6px', borderColor: 'rgba(248, 81, 73, 0.3)', color: 'var(--danger)' }}>
              {task.error}
            </pre>
          </div>
        )}

        {task.output && (
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--success)' }}>Output</label>
            <pre className="code-block" style={{ marginTop: '6px', borderColor: 'rgba(63, 185, 80, 0.3)', color: 'var(--success)' }}>
              {JSON.stringify(task.output, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </Modal>
  );
}
