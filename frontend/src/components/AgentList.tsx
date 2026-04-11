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
import { Plus, Trash2, Loader2, Bot } from 'lucide-react';
import { getStatusColor, getProviderLabel } from '@/lib/utils';
import type { Agent, LLMProvider } from '@/types';

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <Card>
      <CardContent>
        <div className="empty-state">
          <Bot className="empty-state-icon" style={{ width: '48px', height: '48px' }} />
          <h3>No agents yet</h3>
          <p>Create your first agent to start orchestrating complex AI workflows</p>
          <Button onClick={onCreate} style={{ marginTop: '8px' }}>
            <Plus className="h-4 w-4" />
            Create Agent
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
          <div className="skeleton" style={{ height: '20px', width: '60%', marginBottom: '12px' }} />
          <div className="skeleton" style={{ height: '14px', width: '40%', marginBottom: '8px' }} />
          <div className="skeleton" style={{ height: '14px', width: '50%', marginBottom: '16px' }} />
          <div style={{ display: 'flex', gap: '8px' }}>
            <div className="skeleton" style={{ height: '32px', flex: 1 }} />
            <div className="skeleton" style={{ height: '32px', width: '32px' }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function AgentList() {
  const queryClient = useQueryClient();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);

  const { data: agents, isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: api.agents.list,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.agents.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="page-header">
          <h2>Agents</h2>
          <p>Configure and manage your AI agents</p>
        </div>
        <LoadingSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <h2>Agents</h2>
          <p>Configure and manage your AI agents</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="h-4 w-4" />
          Create Agent
        </Button>
      </div>

      {agents && agents.length > 0 ? (
        <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
          {agents.map((agent: Agent, idx: number) => (
            <Card key={agent.id} className="card-animate" style={{ cursor: 'pointer', animationDelay: `${idx * 60}ms` }}>
              <CardHeader>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                  <div style={{ flex: 1 }}>
                    <CardTitle>{agent.name}</CardTitle>
                    {agent.description && (
                      <CardDescription style={{ marginTop: '6px' }}>{agent.description}</CardDescription>
                    )}
                  </div>
                  <Badge className={getStatusColor(agent.status)}>
                    {agent.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div>
                  <div className="data-row" style={{ padding: '6px 0' }}>
                    <span className="data-label">Provider</span>
                    <span className="data-value mono-value">{getProviderLabel(agent.model_provider)}</span>
                  </div>
                  <div className="data-row" style={{ padding: '6px 0' }}>
                    <span className="data-label">Model</span>
                    <span className="data-value mono-value" style={{ fontSize: '0.8rem' }}>{agent.model_name}</span>
                  </div>
                  <div className="data-row" style={{ padding: '6px 0', borderBottom: 'none' }}>
                    <span className="data-label">Tools</span>
                    <span className="data-value">{agent.tools?.length || 0}</span>
                  </div>
                </div>
              </CardContent>
              <CardFooter>
                <Button
                  variant="outline"
                  size="sm"
                  style={{ flex: 1 }}
                  onClick={() => setSelectedAgent(agent)}
                >
                  View
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteMutation.mutate(agent.id)}
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

      <CreateAgentModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
      />

      {selectedAgent && (
        <AgentDetailModal
          agent={selectedAgent}
          isOpen={!!selectedAgent}
          onClose={() => setSelectedAgent(null)}
        />
      )}
    </div>
  );
}

function CreateAgentModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    model_provider: 'openai' as LLMProvider,
    model_name: 'gpt-4o',
    system_prompt: '',
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.agents.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      onClose();
      setFormData({
        name: '',
        description: '',
        model_provider: 'openai',
        model_name: 'gpt-4o',
        system_prompt: '',
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Agent">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="form-group">
          <label className="form-label">Name</label>
          <Input
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Research Agent"
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Description</label>
          <Input
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Agents that research topics on the web"
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div className="form-group">
            <label className="form-label">Provider</label>
            <Select
              value={formData.model_provider}
              onChange={(e) => setFormData({ ...formData, model_provider: e.target.value as LLMProvider })}
              options={[
                { value: 'openai', label: 'OpenAI' },
                { value: 'anthropic', label: 'Anthropic' },
              ]}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Model</label>
            <Input
              value={formData.model_name}
              onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
              placeholder="gpt-4o"
            />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">System Prompt</label>
          <Textarea
            value={formData.system_prompt}
            onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
            placeholder="You are a helpful research assistant..."
            required
            style={{ minHeight: '120px' }}
          />
        </div>

        <div className="form-actions">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Create
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function AgentDetailModal({
  agent,
  isOpen,
  onClose,
}: {
  agent: Agent;
  isOpen: boolean;
  onClose: () => void;
}) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={agent.name} className="modal-wide">
      <div className="space-y-4">
        {agent.description && (
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Description</label>
            <p style={{ fontSize: '0.9rem' }}>{agent.description}</p>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Provider</label>
            <p className="mono-value">{getProviderLabel(agent.model_provider)}</p>
          </div>
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Model</label>
            <p className="mono-value">{agent.model_name}</p>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Status</label>
          <div style={{ marginTop: '4px' }}>
            <Badge className={getStatusColor(agent.status)}>{agent.status}</Badge>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label" style={{ color: 'var(--text-secondary)' }}>System Prompt</label>
          <div className="code-block" style={{ marginTop: '8px' }}>
            <pre style={{ whiteSpace: 'pre-wrap' }}>{agent.system_prompt}</pre>
          </div>
        </div>

        {agent.tools && agent.tools.length > 0 && (
          <div className="form-group">
            <label className="form-label" style={{ color: 'var(--text-secondary)' }}>Tools</label>
            <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {agent.tools.map((tool, idx) => (
                <div key={idx} style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '12px' }}>
                  <p style={{ fontWeight: 500, fontSize: '0.9rem' }}>{tool.name}</p>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>{tool.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
