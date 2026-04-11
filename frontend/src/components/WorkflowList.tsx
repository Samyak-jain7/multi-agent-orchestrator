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
import { Plus, Trash2, Play, Loader2, MoreVertical, Workflow as WorkflowIcon } from 'lucide-react';
import { getStatusColor, formatRelativeTime } from '@/lib/utils';
import type { Workflow as WorkflowType, Task as TaskType } from '@/types';

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <Card>
      <CardContent>
        <div className="empty-state">
          <WorkflowIcon className="empty-state-icon" style={{ width: '48px', height: '48px' }} />
          <h3>No workflows yet</h3>
          <p>Create your first workflow to orchestrate multiple agents together</p>
          <Button onClick={onCreate} style={{ marginTop: '8px' }}>
            <Plus className="h-4 w-4" />
            Create Workflow
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function LoadingSkeleton() {
  return (
    <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
      {[1, 2, 3].map((i) => (
        <div key={i} className="card" style={{ padding: '20px' }}>
          <div className="skeleton" style={{ height: '20px', width: '70%', marginBottom: '8px' }} />
          <div className="skeleton" style={{ height: '14px', width: '50%', marginBottom: '16px' }} />
          <div className="skeleton" style={{ height: '14px', width: '40%', marginBottom: '8px' }} />
          <div className="skeleton" style={{ height: '14px', width: '45%', marginBottom: '16px' }} />
          <div style={{ display: 'flex', gap: '8px' }}>
            <div className="skeleton" style={{ height: '32px', flex: 1 }} />
            <div className="skeleton" style={{ height: '32px', flex: 1 }} />
            <div className="skeleton" style={{ height: '32px', width: '32px' }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function WorkflowList() {
  const queryClient = useQueryClient();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowType | null>(null);
  const [executeModalData, setExecuteModalData] = useState<{ workflowId: string; inputJson: string } | null>(null);

  const { data: workflows, isLoading } = useQuery({
    queryKey: ['workflows'],
    queryFn: api.workflows.list,
  });

  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: api.agents.list,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.workflows.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });

  const executeMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => api.workflows.execute(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      setExecuteModalData(null);
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="page-header">
          <h2>Workflows</h2>
          <p>Orchestrate multiple agents to complete complex tasks</p>
        </div>
        <LoadingSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <h2>Workflows</h2>
          <p>Orchestrate multiple agents to complete complex tasks</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="h-4 w-4" />
          Create Workflow
        </Button>
      </div>

      {workflows && workflows.length > 0 ? (
        <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
          {workflows.map((workflow: WorkflowType, idx: number) => (
            <Card key={workflow.id} className="card-animate" style={{ animationDelay: `${idx * 60}ms` }}>
              <CardHeader>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                  <div style={{ flex: 1 }}>
                    <CardTitle style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {workflow.name}
                    </CardTitle>
                    {workflow.description && (
                      <CardDescription style={{ marginTop: '4px', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {workflow.description}
                      </CardDescription>
                    )}
                  </div>
                  <Badge className={getStatusColor(workflow.status)} style={{ marginLeft: '8px', flexShrink: 0 }}>
                    {workflow.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div className="data-row" style={{ padding: '4px 0' }}>
                    <span className="data-label">Agents</span>
                    <span className="data-value">{workflow.agent_ids?.length || 0}</span>
                  </div>
                  <div className="data-row" style={{ padding: '4px 0' }}>
                    <span className="data-label">Created</span>
                    <span className="data-value mono-value" style={{ fontSize: '0.8rem' }}>{formatRelativeTime(workflow.created_at)}</span>
                  </div>
                  {workflow.started_at && (
                    <div className="data-row" style={{ padding: '4px 0', borderBottom: 'none' }}>
                      <span className="data-label">Last Run</span>
                      <span className="data-value mono-value" style={{ fontSize: '0.8rem' }}>{formatRelativeTime(workflow.started_at)}</span>
                    </div>
                  )}
                </div>
              </CardContent>
              <CardFooter>
                <Button
                  variant="outline"
                  size="sm"
                  style={{ flex: 1 }}
                  onClick={() => setSelectedWorkflow(workflow)}
                >
                  <MoreVertical className="h-4 w-4" />
                  Details
                </Button>
                <Button
                  size="sm"
                  style={{ marginLeft: '8px' }}
                  onClick={() => setExecuteModalData({ workflowId: workflow.id, inputJson: '{}' })}
                  disabled={workflow.status === 'running'}
                >
                  <Play className="h-4 w-4" />
                  Run
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteMutation.mutate(workflow.id)}
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
        <EmptyState onCreate={() => setIsCreateModalOpen(true)} />
      )}

      <CreateWorkflowModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        agents={agents || []}
      />

      {selectedWorkflow && (
        <WorkflowDetailModal
          workflow={selectedWorkflow}
          isOpen={!!selectedWorkflow}
          onClose={() => setSelectedWorkflow(null)}
          onExecute={() => {
            setExecuteModalData({ workflowId: selectedWorkflow.id, inputJson: '{}' });
            setSelectedWorkflow(null);
          }}
        />
      )}

      {executeModalData && (
        <ExecuteWorkflowModal
          workflowId={executeModalData.workflowId}
          inputJson={executeModalData.inputJson}
          isOpen={!!executeModalData}
          onClose={() => setExecuteModalData(null)}
          onExecute={(inputData) => executeMutation.mutate({ id: executeModalData.workflowId, data: { input_data: inputData } })}
          isExecuting={executeMutation.isPending}
        />
      )}
    </div>
  );
}

function CreateWorkflowModal({
  isOpen,
  onClose,
  agents,
}: {
  isOpen: boolean;
  onClose: () => void;
  agents: any[];
}) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    agent_ids: [] as string[],
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.workflows.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      onClose();
      setFormData({ name: '', description: '', agent_ids: [] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  const toggleAgent = (agentId: string) => {
    setFormData((prev) => ({
      ...prev,
      agent_ids: prev.agent_ids.includes(agentId)
        ? prev.agent_ids.filter((id) => id !== agentId)
        : [...prev.agent_ids, agentId],
    }));
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Workflow">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="form-group">
          <label className="form-label">Name</label>
          <Input
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Market Research Pipeline"
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Description</label>
          <Textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Research market trends and generate report"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Select Agents</label>
          <div className="scrollable-list" style={{ marginTop: '8px' }}>
            {agents.length > 0 ? (
              agents.map((agent: any) => (
                <label key={agent.id} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.agent_ids.includes(agent.id)}
                    onChange={() => toggleAgent(agent.id)}
                  />
                  <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>{agent.name}</span>
                  <span className="mono-value" style={{ fontSize: '0.75rem' }}>({agent.model_name})</span>
                </label>
              ))
            ) : (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', padding: '8px 0' }}>
                No agents available. Create agents first.
              </p>
            )}
          </div>
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

function WorkflowDetailModal({
  workflow,
  isOpen,
  onClose,
  onExecute,
}: {
  workflow: WorkflowType;
  isOpen: boolean;
  onClose: () => void;
  onExecute: () => void;
}) {
  const { data: tasks, isLoading: tasksLoading } = useQuery({
    queryKey: ['workflow-tasks', workflow.id],
    queryFn: () => api.workflows.getTasks(workflow.id),
    enabled: isOpen,
  });

  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: api.agents.list,
  });

  const getAgentName = (agentId: string) => {
    const agent = agents?.find((a: any) => a.id === agentId);
    return agent?.name || agentId;
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={workflow.name} className="modal-wide">
      <div className="space-y-4">
        {workflow.description && (
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Description</label>
            <p style={{ fontSize: '0.9rem' }}>{workflow.description}</p>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Status</label>
            <div style={{ marginTop: '4px' }}>
              <Badge className={getStatusColor(workflow.status)}>{workflow.status}</Badge>
            </div>
          </div>
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Agents</label>
            <p style={{ fontSize: '0.9rem', marginTop: '4px' }}>{workflow.agent_ids?.length || 0} assigned</p>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Tasks</label>
          {tasksLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '16px 0' }}>
              <div className="loading-spinner" />
            </div>
          ) : tasks && tasks.length > 0 ? (
            <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {tasks.map((task: TaskType) => (
                <div key={task.id} style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                    <div>
                      <p style={{ fontWeight: 500, fontSize: '0.9rem' }}>{task.title}</p>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                        Agent: {getAgentName(task.agent_id)}
                      </p>
                    </div>
                    <Badge className={getStatusColor(task.status)} style={{ flexShrink: 0, marginLeft: '8px' }}>{task.status}</Badge>
                  </div>
                  {task.description && (
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '6px' }}>{task.description}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '8px' }}>No tasks in this workflow</p>
          )}
        </div>

        <hr className="divider" />
        <div className="form-actions" style={{ marginTop: 0 }}>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button onClick={onExecute} disabled={workflow.status === 'running'}>
            <Play className="h-4 w-4" />
            Execute Workflow
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function ExecuteWorkflowModal({
  workflowId,
  inputJson,
  isOpen,
  onClose,
  onExecute,
  isExecuting,
}: {
  workflowId: string;
  inputJson: string;
  isOpen: boolean;
  onClose: () => void;
  onExecute: (inputData: any) => void;
  isExecuting: boolean;
}) {
  const [input, setInput] = useState(inputJson);
  const [error, setError] = useState<string | null>(null);

  const handleExecute = () => {
    try {
      const parsed = JSON.parse(input);
      setError(null);
      onExecute(parsed);
    } catch {
      setError('Invalid JSON format');
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Execute Workflow">
      <div className="space-y-4">
        <div className="form-group">
          <label className="form-label">Input Data (JSON)</label>
          <Textarea
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              setError(null);
            }}
            placeholder='{"topic": "AI trends 2024"}'
            style={{ minHeight: '150px', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.8125rem' }}
          />
          {error && <p className="form-error">{error}</p>}
        </div>

        <div className="form-actions">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleExecute} disabled={isExecuting}>
            {isExecuting && <Loader2 className="h-4 w-4" style={{ marginRight: '6px' }} />}
            Execute
          </Button>
        </div>
      </div>
    </Modal>
  );
}
