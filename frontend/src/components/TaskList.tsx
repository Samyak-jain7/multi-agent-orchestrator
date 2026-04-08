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
import { Plus, Trash2, RefreshCw, Loader2 } from 'lucide-react';
import { getStatusColor, formatRelativeTime, formatDate } from '@/lib/utils';
import type { Task, TaskStatus } from '@/types';

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
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Tasks</h2>
          <p className="text-muted-foreground">View and manage individual task executions</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Task
        </Button>
      </div>

      <div className="flex gap-4">
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
          className="w-48"
        />
      </div>

      {tasks && tasks.length > 0 ? (
        <div className="space-y-4">
          {tasks.map((task: Task) => (
            <Card key={task.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-base">{task.title}</CardTitle>
                    {task.description && (
                      <CardDescription className="mt-1 line-clamp-1">
                        {task.description}
                      </CardDescription>
                    )}
                  </div>
                  <Badge className={getStatusColor(task.status)}>{task.status}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Workflow:</span>
                    <p className="font-medium truncate">{getWorkflowName(task.workflow_id)}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Agent:</span>
                    <p className="font-medium truncate">{getAgentName(task.agent_id)}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Created:</span>
                    <p className="font-medium">{formatRelativeTime(task.created_at)}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Priority:</span>
                    <p className="font-medium">{task.priority}</p>
                  </div>
                </div>

                {task.status === 'failed' && task.error && (
                  <div className="mt-3 rounded-md bg-red-50 border border-red-200 p-3">
                    <p className="text-sm text-red-700">Error: {task.error}</p>
                  </div>
                )}

                {task.status === 'completed' && task.output && (
                  <div className="mt-3 rounded-md bg-green-50 border border-green-200 p-3">
                    <p className="text-sm text-green-700 font-medium">Completed successfully</p>
                  </div>
                )}
              </CardContent>
              <CardFooter className="gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedTask(task)}
                >
                  View Details
                </Button>
                {task.status === 'failed' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => retryMutation.mutate(task.id)}
                    disabled={retryMutation.isPending}
                  >
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Retry
                  </Button>
                )}
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteMutation.mutate(task.id)}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex h-64 items-center justify-center">
            <div className="text-center">
              <p className="text-lg font-medium">No tasks found</p>
              <p className="text-muted-foreground">
                {statusFilter ? 'Try a different filter' : 'Tasks will appear here when workflows are executed'}
              </p>
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
        <div>
          <label className="text-sm font-medium">Workflow</label>
          <Select
            value={formData.workflow_id}
            onChange={(e) => setFormData({ ...formData, workflow_id: e.target.value })}
            options={[
              { value: '', label: 'Select workflow' },
              ...workflows.map((w: any) => ({ value: w.id, label: w.name })),
            ]}
            className="mt-1"
            required
          />
        </div>

        <div>
          <label className="text-sm font-medium">Agent</label>
          <Select
            value={formData.agent_id}
            onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
            options={[
              { value: '', label: 'Select agent' },
              ...agents.map((a: any) => ({ value: a.id, label: a.name })),
            ]}
            className="mt-1"
            required
          />
        </div>

        <div>
          <label className="text-sm font-medium">Title</label>
          <Input
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            placeholder="Research market trends"
            required
            className="mt-1"
          />
        </div>

        <div>
          <label className="text-sm font-medium">Description</label>
          <Textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Analyze current market trends for AI products"
            className="mt-1"
          />
        </div>

        <div>
          <label className="text-sm font-medium">Input Data (JSON)</label>
          <Textarea
            value={formData.input_data}
            onChange={(e) => {
              setFormData({ ...formData, input_data: e.target.value });
              setError(null);
            }}
            placeholder='{"query": "AI trends"}'
            className="mt-1 font-mono"
          />
          {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
        </div>

        <div>
          <label className="text-sm font-medium">Priority</label>
          <Input
            type="number"
            value={formData.priority}
            onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
            min={0}
            className="mt-1"
          />
        </div>

        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
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
    <Modal isOpen={isOpen} onClose={onClose} title={task.title} className="max-w-2xl">
      <div className="space-y-4">
        <div className="flex items-center gap-4">
          <Badge className={getStatusColor(task.status)}>{task.status}</Badge>
          {task.retry_count > 0 && (
            <span className="text-sm text-muted-foreground">
              Retry count: {task.retry_count}
            </span>
          )}
        </div>

        {task.description && (
          <div>
            <label className="text-sm font-medium text-muted-foreground">Description</label>
            <p className="mt-1">{task.description}</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-muted-foreground">Workflow</label>
            <p className="mt-1">{workflowName}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Agent</label>
            <p className="mt-1">{agentName}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Priority</label>
            <p className="mt-1">{task.priority}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Dependencies</label>
            <p className="mt-1">
              {task.dependencies?.length > 0 ? task.dependencies.join(', ') : 'None'}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <label className="text-sm font-medium text-muted-foreground">Created</label>
            <p className="mt-1">{formatDate(task.created_at)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Started</label>
            <p className="mt-1">{formatDate(task.started_at)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Completed</label>
            <p className="mt-1">{formatDate(task.completed_at)}</p>
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-muted-foreground">Input Data</label>
          <pre className="mt-1 rounded-md bg-muted p-3 text-sm overflow-x-auto">
            {JSON.stringify(task.input_data, null, 2)}
          </pre>
        </div>

        {task.error && (
          <div>
            <label className="text-sm font-medium text-red-500">Error</label>
            <pre className="mt-1 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700 overflow-x-auto">
              {task.error}
            </pre>
          </div>
        )}

        {task.output && (
          <div>
            <label className="text-sm font-medium text-green-600">Output</label>
            <pre className="mt-1 rounded-md bg-green-50 border border-green-200 p-3 text-sm overflow-x-auto">
              {JSON.stringify(task.output, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </Modal>
  );
}
