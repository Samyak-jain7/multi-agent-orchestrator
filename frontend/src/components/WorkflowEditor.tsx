'use client';

import { useCallback, useState } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Handle,
  Position,
  NodeTypes,
  Connection,
  Node,
  Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Bot, Search, FileCode, Zap, CheckCircle } from 'lucide-react';

// Agent node component
function AgentNode({ data }: { data: any }) {
  const iconMap: Record<string, any> = {
    researcher: Search,
    coder: FileCode,
    writer: FileCode,
    evaluator: CheckCircle,
    default: Bot,
  };
  const Icon = iconMap[data.type] || iconMap.default;

  return (
    <div className="agent-node">
      <Handle type="target" position={Position.Top} className="handle" />
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-4 h-4" style={{ color: 'var(--accent)' }} />
        <span className="font-medium text-sm" style={{ color: 'var(--text-primary)' }}>
          {data.label}
        </span>
      </div>
      <div className="flex flex-wrap gap-1 mt-2">
        {(data.tools || []).slice(0, 3).map((tool: string) => (
          <Badge key={tool} className="status-pending" style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
            {tool}
          </Badge>
        ))}
      </div>
      {data.tools?.length > 3 && (
        <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
          +{data.tools.length - 3} more
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="handle" />
    </div>
  );
}

const nodeTypes: NodeTypes = {
  agent: AgentNode,
};

// Supervisor node
function SupervisorNode({ data }: { data: any }) {
  return (
    <div className="supervisor-node">
      <Handle type="target" position={Position.Top} className="handle" />
      <div className="flex items-center gap-2">
        <Zap className="w-4 h-4" style={{ color: 'var(--warning)' }} />
        <span className="font-bold text-sm" style={{ color: 'var(--warning)' }}>
          SUPERVISOR
        </span>
      </div>
      <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
        Routes tasks to agents
      </div>
      <Handle type="source" position={Position.Bottom} className="handle" />
    </div>
  );
}

// Add to nodeTypes
const extendedNodeTypes = {
  ...nodeTypes,
  supervisor: SupervisorNode,
};

interface WorkflowEditorProps {
  workflowId?: string;
  initialNodes?: Node[];
  initialEdges?: Edge[];
  onSave?: (nodes: Node[], edges: Edge[]) => void;
}

export function WorkflowEditor({
  workflowId,
  initialNodes = [],
  initialEdges = [],
  onSave
}: WorkflowEditorProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
    [setEdges]
  );

  const addAgentNode = (type: string) => {
    const newNode: Node = {
      id: `${type}_${Date.now()}`,
      type,
      position: { x: Math.random() * 400, y: Math.random() * 300 },
      data: {
        label: `${type} Agent`,
        type,
        tools: [],
        agent_id: null,
      },
    };
    setNodes((nds) => [...nds, newNode]);
  };

  const handleSave = () => {
    if (onSave) {
      onSave(nodes, edges);
    }
  };

  return (
    <div className="workflow-editor" style={{ display: 'flex', gap: '16px', height: '600px' }}>
      {/* Node palette */}
      <div style={{ width: '220px', flexShrink: 0 }}>
        <Card>
          <CardHeader>
            <CardTitle>Agent Library</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => addAgentNode('agent')}
                className="justify-start"
              >
                <Bot className="w-4 h-4 mr-2" />
                Add Agent
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setNodes((nds) => [...nds, {
                    id: `supervisor_${Date.now()}`,
                    type: 'supervisor',
                    position: { x: 200, y: 50 },
                    data: { label: 'Supervisor' }
                  }]);
                }}
                className="justify-start"
              >
                <Zap className="w-4 h-4 mr-2" style={{ color: 'var(--warning)' }} />
                Add Supervisor
              </Button>
            </div>

            <div className="divider" style={{ margin: '16px 0' }} />

            <p className="text-sm mb-2" style={{ color: 'var(--text-secondary)' }}>
              Drag agents onto canvas
            </p>

            {/* Agent templates */}
            <div className="flex flex-col gap-1">
              {[
                { type: 'researcher', icon: Search, label: 'Research Agent', tools: ['google_search', 'web_fetch'] },
                { type: 'coder', icon: FileCode, label: 'Coder Agent', tools: ['bash_execute', 'file_write'] },
                { type: 'evaluator', icon: CheckCircle, label: 'Evaluator Agent', tools: ['code_review'] },
              ].map((template) => (
                <div
                  key={template.type}
                  className="agent-template"
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('application/reactflow', JSON.stringify({
                      type: 'agent',
                      data: { label: template.label, type: template.type, tools: template.tools }
                    }));
                  }}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                    cursor: 'grab',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '0.8rem',
                  }}
                >
                  <template.icon className="w-3 h-3" style={{ color: 'var(--accent)' }} />
                  <span>{template.label}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Canvas */}
      <div style={{ flex: 1, borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border)' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={(_, node) => setSelectedNode(node.id)}
          nodeTypes={extendedNodeTypes}
          fitView
          snapToGrid
          snapGrid={[16, 16]}
        >
          <Controls />
          <MiniMap
            nodeColor={(node) => node.type === 'supervisor' ? 'var(--warning)' : 'var(--accent)'}
            maskColor="rgba(0,0,0,0.8)"
          />
          <Background gap={16} color="var(--border)" />
        </ReactFlow>
      </div>

      {/* Properties panel */}
      {selectedNode && (
        <div style={{ width: '280px', flexShrink: 0 }}>
          <Card>
            <CardHeader>
              <CardTitle>Node Properties</CardTitle>
            </CardHeader>
            <CardContent>
              <NodePropertiesPanel
                node={nodes.find((n) => n.id === selectedNode)}
                onUpdate={(updated: Node) => {
                  setNodes((nds) => nds.map((n) => n.id === selectedNode ? updated : n));
                }}
                onClose={() => setSelectedNode(null)}
              />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// Node properties editor
function NodePropertiesPanel({ node, onUpdate, onClose }: any) {
  if (!node) return null;

  return (
    <div className="flex flex-col gap-3">
      <div className="form-group">
        <label className="form-label">Name</label>
        <input
          className="input"
          value={node.data.label || ''}
          onChange={(e) => onUpdate({ ...node, data: { ...node.data, label: e.target.value } })}
        />
      </div>

      {node.type === 'agent' && (
        <>
          <div className="form-group">
            <label className="form-label">Linked Agent ID</label>
            <input
              className="input"
              placeholder="agent_xxx or create new"
              value={node.data.agent_id || ''}
              onChange={(e) => onUpdate({ ...node, data: { ...node.data, agent_id: e.target.value } })}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Tools ({node.data.tools?.length || 0})</label>
            <div className="flex flex-wrap gap-1">
              {(node.data.tools || []).map((tool: string) => (
                <Badge key={tool} className="status-pending">
                  {tool}
                  <button
                    onClick={() => onUpdate({
                      ...node,
                      data: { ...node.data, tools: node.data.tools.filter((t: string) => t !== tool) }
                    })}
                    className="ml-1"
                  >
                    ×
                  </button>
                </Badge>
              ))}
            </div>
          </div>
        </>
      )}

      <Button variant="destructive" size="sm" onClick={onClose}>
        Done
      </Button>
    </div>
  );
}
