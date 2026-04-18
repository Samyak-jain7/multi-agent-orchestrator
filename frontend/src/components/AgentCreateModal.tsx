'use client';

import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Search, Bot, Wrench, Brain, Zap } from 'lucide-react';

const AVAILABLE_TOOLS = [
  // Search
  { id: 'google_search', name: 'Google Search', category: 'search', description: 'Search the web' },
  { id: 'wikipedia_search', name: 'Wikipedia', category: 'search', description: 'Search Wikipedia' },
  { id: 'ddg_search', name: 'DuckDuckGo', category: 'search', description: 'Privacy-respecting search' },
  // Code
  { id: 'bash_execute', name: 'Bash Execute', category: 'code', description: 'Run shell commands' },
  { id: 'python_execute', name: 'Python Execute', category: 'code', description: 'Run Python code' },
  { id: 'code_search', name: 'Code Search', category: 'code', description: 'Search code files' },
  // File
  { id: 'file_read', name: 'File Read', category: 'file', description: 'Read files' },
  { id: 'file_write', name: 'File Write', category: 'file', description: 'Write files' },
  // Web
  { id: 'web_fetch', name: 'Web Fetch', category: 'web', description: 'Fetch web pages' },
  { id: 'browser_navigate', name: 'Browser', category: 'web', description: 'Navigate browser' },
];

const TOOL_CATEGORIES = ['search', 'code', 'file', 'web'];

interface AgentCreateModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (agent: {
    name: string;
    description: string;
    model_provider: string;
    model_name: string;
    system_prompt: string;
    tool_ids: string[];
    memory_enabled: boolean;
    max_iterations: number;
  }) => void;
}

export function AgentCreateModal({ open, onClose, onSubmit }: AgentCreateModalProps) {
  const [step, setStep] = useState<'details' | 'tools'>('details');
  const [form, setForm] = useState({
    name: '',
    description: '',
    model_provider: 'minimax',
    model_name: 'MiniMax-M2.7',
    system_prompt: '',
    tool_ids: [] as string[],
    memory_enabled: true,
    max_iterations: 5,
  });
  const [search, setSearch] = useState('');

  const filteredTools = AVAILABLE_TOOLS.filter(
    (t) => t.name.toLowerCase().includes(search.toLowerCase()) ||
           t.category.toLowerCase().includes(search.toLowerCase())
  );

  const toggleTool = (toolId: string) => {
    setForm((f) => ({
      ...f,
      tool_ids: f.tool_ids.includes(toolId)
        ? f.tool_ids.filter((id) => id !== toolId)
        : [...f.tool_ids, toolId],
    }));
  };

  const handleSubmit = () => {
    onSubmit(form);
    onClose();
    setStep('details');
    setForm({ name: '', description: '', model_provider: 'minimax', model_name: 'MiniMax-M2.7', system_prompt: '', tool_ids: [], memory_enabled: true, max_iterations: 5 });
  };

  return (
    <Modal isOpen={open} onClose={onClose} title={step === 'details' ? 'Create Agent' : 'Select Tools'}>
      {step === 'details' ? (
        <div className="flex flex-col gap-4">
          <div className="form-group">
            <label className="form-label">Name</label>
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Research Agent"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <Input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="What this agent does"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label">Provider</label>
              <select
                className="select"
                value={form.model_provider}
                onChange={(e) => setForm({ ...form, model_provider: e.target.value })}
              >
                <option value="minimax">MiniMax</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Model</label>
              <select
                className="select"
                value={form.model_name}
                onChange={(e) => setForm({ ...form, model_name: e.target.value })}
              >
                {form.model_provider === 'minimax' && (
                  <>
                    <option value="MiniMax-M2.7">MiniMax-M2.7</option>
                    <option value="MiniMax-M2.5">MiniMax-M2.5</option>
                  </>
                )}
                {form.model_provider === 'openai' && (
                  <>
                    <option value="gpt-4o">GPT-4o</option>
                    <option value="gpt-4o-mini">GPT-4o Mini</option>
                  </>
                )}
                {form.model_provider === 'anthropic' && (
                  <>
                    <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
                    <option value="claude-3-opus-20240229">Claude 3 Opus</option>
                  </>
                )}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">System Prompt</label>
            <Textarea
              value={form.system_prompt}
              onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
              placeholder="You are a research agent. Use web search to find information..."
              style={{ minHeight: '100px' }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={form.memory_enabled}
                onChange={(e) => setForm({ ...form, memory_enabled: e.target.checked })}
              />
              <Brain className="w-4 h-4" style={{ color: 'var(--accent)' }} />
              <span className="text-sm">Enable Memory</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <Zap className="w-4 h-4" style={{ color: 'var(--warning)' }} />
              <span className="text-sm">Max Iterations:</span>
              <input
                type="number"
                className="input"
                style={{ width: '60px' }}
                value={form.max_iterations}
                onChange={(e) => setForm({ ...form, max_iterations: parseInt(e.target.value) || 5 })}
                min={1}
                max={20}
              />
            </label>
          </div>

          <div className="form-actions">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={() => setStep('tools')}>
              <Wrench className="w-4 h-4 mr-2" />
              Select Tools ({form.tool_ids.length})
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <div style={{ position: 'relative' }}>
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-muted)' }} />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search tools..."
              style={{ paddingLeft: '36px' }}
            />
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {TOOL_CATEGORIES.map((cat) => (
              <Badge
                key={cat}
                className="cursor-pointer capitalize"
                style={{
                  background: search === cat ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                  color: search === cat ? 'var(--accent)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                }}
                onClick={() => setSearch(search === cat ? '' : cat)}
              >
                {cat}
              </Badge>
            ))}
          </div>

          <div className="flex flex-col gap-2" style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {filteredTools.map((tool) => (
              <div
                key={tool.id}
                onClick={() => toggleTool(tool.id)}
                style={{
                  padding: '10px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border)',
                  background: form.tool_ids.includes(tool.id) ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                  borderColor: form.tool_ids.includes(tool.id) ? 'var(--accent)' : 'var(--border)',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <p className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>
                      {tool.name}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      {tool.description}
                    </p>
                  </div>
                  {form.tool_ids.includes(tool.id) && (
                    <Badge className="status-completed">Selected</Badge>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="form-actions">
            <Button variant="outline" onClick={() => setStep('details')}>Back</Button>
            <Button onClick={handleSubmit}>
              <Bot className="w-4 h-4 mr-2" />
              Create Agent
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
