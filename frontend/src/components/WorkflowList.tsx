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
import { Plus, Trash2, Play, Loader2, MoreVertical } from 'lucide-react';
import { getStatusColor, formatRelativeTime } from '@/lib/utils';
import type { Workflow, Task } from '@/types';

export function WorkflowList() {
  const queryClient = useQueryClient();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
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
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Workflows</h2>
          <p className="text-muted-foreground">Orchestrate multiple agents to complete complex tasks</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Workflow
        </Button>
      </div>

      {workflows && workflows.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {workflows.map((workflow: Workflow) => (
            <Card key={workflow.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="truncate">{workflow.name}</CardTitle>
                    {workflow.description && (
                      <CardDescription className="mt-1 line-clamp-2">
                        {workflow.description}
                      </CardDescription>
                    )}
                  </div>
                  <Badge className={getStatusColor(workflow.status)}>
                    {workflow.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Agents:</span>
                    <span className="font-medium">{workflow.agent_ids?.length || 0}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Created:</span>
                    <span className="font-medium">{formatRelativeTime(workflow.created_at)}</span>
                  </div>
                  {workflow.started_at && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Last Run:</span>
                      <span className="font-medium">{formatRelativeTime(workflow.started_at)}</span>
                    </div>
                  )}
                </div>
              </CardContent>
              <CardFooter className="gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => setSelectedWorkflow(workflow)}
                >
                  <MoreVertical className="mr-2 h-4 w-4" />
                  Details
                </Button>
                <Button
                  size="sm"
                  onClick={() => setExecuteModalData({ workflowId: workflow.id, inputJson: '{}' })}
                  disabled={workflow.status === 'running'}
                >
                  <Play className="mr-2 h-4 w-4" />
                  Run
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteMutation.mutate(workflow.id)}
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
              <p className="text-lg font-medium">No workflows yet</p>
              <p className="text-muted-foreground">Create your first workflow to orchestrate agents</p>
            </div>
          </CardContent>
        </Card>
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
        <div>
          <label className="text-sm font-medium">Name</label>
          <Input
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Market Research Pipeline"
            required
            className="mt-1"
          />
        </div>

        <div>
          <label className="text-sm font-medium">Description</label>
          <Textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Research market trends and generate report"
            className="mt-1"
          />
        </div>

        <div>
          <label className="text-sm font-medium">Select Agents</label>
          <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
            {agents.length > 0 ? (
              agents.map((agent: any) => (
                <label
                  key={agent.id}
                  className="flex items-center gap-2 rounded-md border p-2 cursor-pointer hover:bg-muted"
                >
                  <input
                    type="checkbox"
                    checked={formData.agent_ids.includes(agent.id)}
                    onChange={() => toggleAgent(agent.id)}
                    className="rounded"
                  />
                  <span className="font-medium">{agent.name}</span>
                  <span className="text-sm text-muted-foreground">({agent.model_name})</span>
                </label>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No agents available. Create agents first.</p>
            )}
          </div>
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

function WorkflowDetailModal({
  workflow,
  isOpen,
  onClose,
  onExecute,
}: {
  workflow: Workflow;
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
    <Modal isOpen={isOpen} onClose={onClose} title={workflow.name} className="max-w-2xl">
      <div className="space-y-4">
        {workflow.description && (
          <div>
            <label className="text-sm font-medium text-muted-foreground">Description</label>
            <p className="mt-1">{workflow.description}</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-muted-foreground">Status</label>
            <div className="mt-1">
              <Badge className={getStatusColor(workflow.status)}>{workflow.status}</Badge>
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Agents</label>
            <p className="mt-1">{workflow.agent_ids?.length || 0} assigned</p>
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-muted-foreground">Tasks</label>
          {tasksLoading ? (
            <div className="mt-2 flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : tasks && tasks.length > 0 ? (
            <div className="mt-2 space-y-2">
              {tasks.map((task: Task) => (
                <div key={task.id} className="rounded-md border p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{task.title}</p>
                      <p className="text-sm text-muted-foreground">
                        Agent: {getAgentName(task.agent_id)}
                      </p>
                    </div>
                    <Badge className={getStatusColor(task.status)}>{task.status}</Badge>
                  </div>
                  {task.description && (
                    <p className="mt-1 text-sm text-muted-foreground">{task.description}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-1 text-sm text-muted-foreground">No tasks in this workflow</p>
          )}
        </div>

        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button onClick={onExecute} disabled={workflow.status === 'running'}>
            <Play className="mr-2 h-4 w-4" />
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
        <div>
          <label className="text-sm font-medium">Input Data (JSON)</label>
          <Textarea
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              setError(null);
            }}
            placeholder='{"topic": "AI trends 2024"}'
            className="mt-1 font-mono min-h-[150px]"
          />
          {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleExecute} disabled={isExecuting}>
            {isExecuting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Execute
          </Button>
        </div>
      </div>
    </Modal>
  );
}
