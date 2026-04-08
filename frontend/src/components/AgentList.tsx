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
import { Plus, Trash2, Loader2 } from 'lucide-react';
import { getStatusColor, getProviderLabel } from '@/lib/utils';
import type { Agent, LLMProvider } from '@/types';

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
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Agents</h2>
          <p className="text-muted-foreground">Configure and manage your AI agents</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Agent
        </Button>
      </div>

      {agents && agents.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent: Agent) => (
            <Card key={agent.id} className="cursor-pointer hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle>{agent.name}</CardTitle>
                    {agent.description && (
                      <CardDescription className="mt-1">{agent.description}</CardDescription>
                    )}
                  </div>
                  <Badge className={getStatusColor(agent.status)}>
                    {agent.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Provider:</span>
                    <span className="font-medium">{getProviderLabel(agent.model_provider)}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Model:</span>
                    <span className="font-medium">{agent.model_name}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Tools:</span>
                    <span className="font-medium">{agent.tools?.length || 0}</span>
                  </div>
                </div>
              </CardContent>
              <CardFooter className="gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => setSelectedAgent(agent)}
                >
                  View
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteMutation.mutate(agent.id)}
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
              <p className="text-lg font-medium">No agents yet</p>
              <p className="text-muted-foreground">Create your first agent to get started</p>
            </div>
          </CardContent>
        </Card>
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
        <div>
          <label className="text-sm font-medium">Name</label>
          <Input
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Research Agent"
            required
            className="mt-1"
          />
        </div>

        <div>
          <label className="text-sm font-medium">Description</label>
          <Input
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Agents that research topics on the web"
            className="mt-1"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium">Provider</label>
            <Select
              value={formData.model_provider}
              onChange={(e) => setFormData({ ...formData, model_provider: e.target.value as LLMProvider })}
              options={[
                { value: 'openai', label: 'OpenAI' },
                { value: 'anthropic', label: 'Anthropic' },
              ]}
              className="mt-1"
            />
          </div>

          <div>
            <label className="text-sm font-medium">Model</label>
            <Input
              value={formData.model_name}
              onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
              placeholder="gpt-4o"
              className="mt-1"
            />
          </div>
        </div>

        <div>
          <label className="text-sm font-medium">System Prompt</label>
          <Textarea
            value={formData.system_prompt}
            onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
            placeholder="You are a helpful research assistant..."
            className="mt-1 min-h-[120px]"
            required
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
    <Modal isOpen={isOpen} onClose={onClose} title={agent.name} className="max-w-2xl">
      <div className="space-y-4">
        {agent.description && (
          <div>
            <label className="text-sm font-medium text-muted-foreground">Description</label>
            <p className="mt-1">{agent.description}</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-muted-foreground">Provider</label>
            <p className="mt-1">{getProviderLabel(agent.model_provider)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-muted-foreground">Model</label>
            <p className="mt-1">{agent.model_name}</p>
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-muted-foreground">Status</label>
          <div className="mt-1">
            <Badge className={getStatusColor(agent.status)}>{agent.status}</Badge>
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-muted-foreground">System Prompt</label>
          <div className="mt-1 rounded-md bg-muted p-3">
            <pre className="text-sm whitespace-pre-wrap">{agent.system_prompt}</pre>
          </div>
        </div>

        {agent.tools && agent.tools.length > 0 && (
          <div>
            <label className="text-sm font-medium text-muted-foreground">Tools</label>
            <div className="mt-2 space-y-2">
              {agent.tools.map((tool, idx) => (
                <div key={idx} className="rounded-md border p-3">
                  <p className="font-medium">{tool.name}</p>
                  <p className="text-sm text-muted-foreground">{tool.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
