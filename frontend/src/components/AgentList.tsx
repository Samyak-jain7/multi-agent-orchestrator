'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Trash2, Loader2, Bot, Brain } from 'lucide-react';
import { getStatusColor, getProviderLabel, formatRelativeTime } from '@/lib/utils';
import type { Agent, LLMProvider } from '@/types';
import { AgentCreateModal } from './AgentCreateModal';

const PROVIDER_MODELS: Record<LLMProvider, { value: string; label: string }[]> = {
  openai: [
    { value: 'gpt-5.4', label: 'GPT-5.4 (flagship, 1M context)' },
    { value: 'gpt-5.4-pro', label: 'GPT-5.4 Pro (max capability)' },
    { value: 'gpt-5.4-mini', label: 'GPT-5.4 Mini (fast, cost-effective)' },
    { value: 'gpt-5.4-nano', label: 'GPT-5.4 Nano (lightweight)' },
  ],
  anthropic: [
    { value: 'claude-opus-4-6', label: 'Claude Opus 4.6 (max reasoning)' },
    { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6 (balanced)' },
    { value: 'claude-haiku-4', label: 'Claude Haiku 4 (fast)' },
  ],
  minimax: [
    { value: 'MiniMax-M2.7', label: 'MiniMax-M2.7 (latest, 204k context)' },
    { value: 'MiniMax-M2.7-highspeed', label: 'MiniMax-M2.7-highspeed (~100 tps)' },
    { value: 'MiniMax-M2.5', label: 'MiniMax-M2.5 (prev gen)' },
    { value: 'MiniMax-M2.5-highspeed', label: 'MiniMax-M2.5-highspeed' },
    { value: 'MiniMax-M2.1', label: 'MiniMax-M2.1' },
    { value: 'MiniMax-M2', label: 'MiniMax-M2 (agentic)' },
  ],
  ollama: [
    { value: 'llama3', label: 'Llama 3' },
    { value: 'llama3.1', label: 'Llama 3.1' },
    { value: 'mistral', label: 'Mistral' },
    { value: 'codellama', label: 'Code Llama' },
  ],
};

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <Card>
      <CardContent>
        <div className="empty-state">
          <Bot className="empty-state-icon" style={{ width: '48px', height: '48px' }} />
          <h3>No agents yet</h3>
          <p>Create your first agent to start orchestrating complex AI workflows</p>
          <Button onClick={onCreate} style={{ marginTop: '8px' }}>
            <Bot className="h-4 w-4" />
            Create Agent
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function LoadingSkeleton() {
  return (
    <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
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
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <h2>Agents</h2>
          <p>Configure and manage your AI agents</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Bot className="h-4 w-4" />
          Create Agent
        </Button>
      </div>

      {agents && agents.length > 0 ? (
        <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
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

                {/* Tool badges */}
                {agent.tools && agent.tools.length > 0 && (
                  <div style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {agent.tools.slice(0, 4).map((tool, i) => (
                      <Badge key={i} variant="outline" style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
                        {tool.name}
                      </Badge>
                    ))}
                    {agent.tools.length > 4 && (
                      <Badge variant="outline" style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
                        +{agent.tools.length - 4}
                      </Badge>
                    )}
                  </div>
                )}

                {/* Memory & Iterations info */}
                <div style={{ marginTop: '10px', display: 'flex', gap: '12px', alignItems: 'center' }}>
                  {(agent as any).memory_enabled && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <Brain className="w-3 h-3" style={{ color: 'var(--accent)' }} />
                      Memory
                    </span>
                  )}
                  {(agent as any).max_iterations && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Max { (agent as any).max_iterations } iters
                    </span>
                  )}
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

      <AgentCreateModal
        open={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={(data) => {
          api.agents.create(data).then(() => {
            queryClient.invalidateQueries({ queryKey: ['agents'] });
          });
        }}
      />

      {selectedAgent && (
        <AgentDetailModal
          agent={selectedAgent}
          open={!!selectedAgent}
          onClose={() => setSelectedAgent(null)}
        />
      )}
    </div>
  );
}

function AgentDetailModal({
  agent,
  open,
  onClose,
}: {
  agent: Agent;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <div className="modal-backdrop" style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', animation: 'fadeIn 0.15s ease' }}>
      <div className="modal-backdrop-overlay" style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }} onClick={onClose} />
      <div className="modal" style={{ position: 'relative', zIndex: 1, width: '100%', maxWidth: '540px', maxHeight: '90vh', overflowY: 'auto', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '10px', padding: '24px', boxShadow: '0 0 40px rgba(0,0,0,0.6), 0 0 20px var(--accent-dim)', animation: 'fadeUp 0.2s ease' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <h2 style={{ fontFamily: 'Chakra Petch, sans-serif', fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)' }}>{agent.name}</h2>
          <button onClick={onClose} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', background: 'transparent', border: 'none', borderRadius: '4px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            ✕
          </button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {agent.description && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label className="form-label" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500 }}>Description</label>
              <p style={{ fontSize: '0.9rem' }}>{agent.description}</p>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label className="form-label" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500 }}>Provider</label>
              <p className="mono-value">{getProviderLabel(agent.model_provider)}</p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label className="form-label" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500 }}>Model</label>
              <p className="mono-value">{agent.model_name}</p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label className="form-label" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500 }}>Status</label>
            <div style={{ marginTop: '4px' }}>
              <Badge className={getStatusColor(agent.status)}>{agent.status}</Badge>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label className="form-label" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500 }}>System Prompt</label>
            <div className="code-block" style={{ marginTop: '8px' }}>
              <pre style={{ whiteSpace: 'pre-wrap' }}>{agent.system_prompt}</pre>
            </div>
          </div>

          {agent.tools && agent.tools.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label className="form-label" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500 }}>Tools ({agent.tools.length})</label>
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
      </div>
    </div>
  );
}
