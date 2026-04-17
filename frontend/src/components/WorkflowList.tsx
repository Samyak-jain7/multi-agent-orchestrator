'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Modal } from '@/components/ui/Modal';
import { Plus, Trash2, Play, Loader2, Workflow as WorkflowIcon, GitBranch, MoreVertical, Edit2 } from 'lucide-react';
import { getStatusColor, formatRelativeTime } from '@/lib/utils';
import type { Workflow as WorkflowType, Task as TaskType } from '@/types';
import { WorkflowEditor } from './WorkflowEditor';
import { Node, Edge } from '@xyflow/react';

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
    <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))' }}>
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

// Mini DAG preview for workflow cards
function MiniDagPreview({ nodeCount, edgeCount }: { nodeCount: number; edgeCount: number }) {
  return (
    <div style={{
      width: '100%',
      height: '60px',
      background: 'var(--bg-base)',
      border: '1px solid var(--border)',
      borderRadius: '6px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '12px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Simple DAG visualization */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--accent-dim)', border: '1px solid var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: '0.6rem', color: 'var(--accent)' }}>S</span>
        </div>
        {edgeCount > 0 && (
          <div style={{ width: '16px', height: '2px', background: 'var(--text-muted)' }} />
        )}
        {nodeCount > 1 && (
          <div style={{ display: 'flex', gap: '4px' }}>
            {Array.from({ length: Math.min(nodeCount - 1, 3) }).map((_, i) => (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                <div style={{ width: '16px', height: '16px', borderRadius: '4px', background: 'var(--bg-elevated)', border: '1px solid var(--border)' }} />
                {i < nodeCount - 2 && <div style={{ width: '2px', height: '8px', background: 'var(--text-muted)' }} />}
              </div>
            ))}
          </div>
        )}
        {edgeCount > 0 && (
          <div style={{ width: '16px', height: '2px', background: 'var(--text-muted)' }} />
        )}
        <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--success-dim)', border: '1px solid var(--success)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: '0.6rem', color: 'var(--success)' }}>E</span>
        </div>
      </div>
    </div>
  );
}

export function WorkflowList() {
  const queryClient = useQueryClient();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowType | null>(null);
  const [executeModalData, setExecuteModalData] = useState<{ workflowId: string; inputJson: string } | null>(null);
  const [editingWorkflow, setEditingWorkflow] = useState<WorkflowType | null>(null);

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

  // Build editor initial nodes/edges from workflow definition
  const getEditorData = (workflow: WorkflowType) => {
    const def = (workflow as any).workflow_definition;
    if (def?.nodes) {
      const nodes: Node[] = def.nodes.map((n: any) => ({
        id: n.id,
        type: n.type,
        position: n.position || { x: 100, y: 100 },
        data: { label: n.agent_id || n.id, type: n.type, tools: n.tools || [], agent_id: n.agent_id },
      }));
      const edges: Edge[] = def.edges.map((e: any) => ({
        id: `${e.from}-${e.to}`,
        source: e.from,
        target: e.to,
        animated: true,
      }));
      return { nodes, edges };
    }
    return { nodes: [] as Node[], edges: [] as Edge[] };
  };

  // Editing mode — show WorkflowEditor full screen
  if (editingWorkflow) {
    const { nodes, edges } = getEditorData(editingWorkflow);
    return (
      <div className="space-y-6">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="page-header" style={{ marginBottom: 0 }}>
            <h2>Edit: {editingWorkflow.name}</h2>
            <p>Design the workflow DAG — connect agents and supervisors</p>
          </div>
          <Button variant="outline" onClick={() => setEditingWorkflow(null)}>
            ← Back to Workflows
          </Button>
        </div>
        <WorkflowEditor
          workflowId={editingWorkflow.id}
          initialNodes={nodes}
          initialEdges={edges}
          onSave={(newNodes, newEdges) => {
            // Convert back to workflow definition format and save
            const definition = {
              nodes: newNodes.map((n) => ({
                id: n.id,
                type: n.type,
                agent_id: (n.data as any).agent_id,
                tools: (n.data as any).tools,
                position: n.position,
              })),
              edges: newEdges.map((e) => ({
                from: e.source,
                to: e.target,
                condition: (e.data as any)?.condition,
              })),
              max_iterations: 10,
            };
            api.workflows.update(editingWorkflow.id, {
              workflow_definition: definition,
            }).then(() => {
              queryClient.invalidateQueries({ queryKey: ['workflows'] });
              setEditingWorkflow(null);
            });
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
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
        <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))' }}>
          {workflows.map((workflow: WorkflowType, idx: number) => {
            const def = (workflow as any).workflow_definition;
            const nodeCount = def?.nodes?.length || 0;
            const edgeCount = def?.edges?.length || 0;
            return (
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
                  {/* DAG preview */}
                  <MiniDagPreview nodeCount={nodeCount || workflow.agent_ids?.length || 1} edgeCount={edgeCount} />

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '10px' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <GitBranch className="w-3 h-3" style={{ color: 'var(--accent)' }} />
                      {nodeCount || workflow.agent_ids?.length || 0} nodes
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {edgeCount} edges
                    </span>
                  </div>

                  <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
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
                    onClick={() => setEditingWorkflow(workflow)}
                  >
                    <Edit2 className="h-4 w-4" />
                    Edit
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
            );
          })}
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
          open={!!selectedWorkflow}
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
          open={!!executeModalData}
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
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
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
  open,
  onClose,
  onExecute,
}: {
  workflow: WorkflowType;
  open: boolean;
  onClose: () => void;
  onExecute: () => void;
}) {
  const { data: tasks, isLoading: tasksLoading } = useQuery({
    queryKey: ['workflow-tasks', workflow.id],
    queryFn: () => api.workflows.getTasks(workflow.id),
    enabled: open,
  });

  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: api.agents.list,
  });

  const getAgentName = (agentId: string) => {
    const agent = agents?.find((a: any) => a.id === agentId);
    return agent?.name || agentId;
  };

  if (!open) return null;

  return (
    <div className="modal-backdrop" style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', animation: 'fadeIn 0.15s ease' }}>
      <div className="modal-backdrop-overlay" style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }} onClick={onClose} />
      <div style={{ position: 'relative', zIndex: 1, width: '100%', maxWidth: '560px', maxHeight: '90vh', overflowY: 'auto', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '10px', padding: '24px', boxShadow: '0 0 40px rgba(0,0,0,0.6), 0 0 20px var(--accent-dim)', animation: 'fadeUp 0.2s ease' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <h2 style={{ fontFamily: 'Chakra Petch, sans-serif', fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)' }}>{workflow.name}</h2>
          <button onClick={onClose} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', background: 'transparent', border: 'none', borderRadius: '4px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            ✕
          </button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {workflow.description && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label className="form-label" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500 }}>Description</label>
              <p style={{ fontSize: '0.9rem' }}>{workflow.description}</p>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label className="form-label" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500 }}>Status</label>
              <div style={{ marginTop: '4px' }}>
                <Badge className={getStatusColor(workflow.status)}>{workflow.status}</Badge>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label className="form-label" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500 }}>Agents</label>
              <p style={{ fontSize: '0.9rem', marginTop: '4px' }}>{workflow.agent_ids?.length || 0} assigned</p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label className="form-label" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500 }}>Tasks</label>
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
      </div>
    </div>
  );
}

function ExecuteWorkflowModal({
  workflowId,
  inputJson,
  open,
  onClose,
  onExecute,
  isExecuting,
}: {
  workflowId: string;
  inputJson: string;
  open: boolean;
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

  if (!open) return null;

  return (
    <Modal isOpen={open} onClose={onClose} title="Execute Workflow">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
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
