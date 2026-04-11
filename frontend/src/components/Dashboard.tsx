'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Activity, Users, Workflow, CheckCircle, XCircle, TrendingUp } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

function SkeletonCard() {
  return (
    <div className="stat-card">
      <div className="skeleton" style={{ height: '14px', width: '80px', marginBottom: '12px' }} />
      <div className="skeleton" style={{ height: '32px', width: '60px' }} />
    </div>
  );
}

function EmptyState({ icon: Icon, heading, description }: { icon: React.ElementType; heading: string; description: string }) {
  return (
    <div className="empty-state">
      <Icon className="empty-state-icon" style={{ width: '40px', height: '40px' }} />
      <h3>{heading}</h3>
      <p>{description}</p>
    </div>
  );
}

export function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: api.execution.getStats,
    refetchInterval: 5000,
  });

  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: api.agents.list,
  });

  const { data: workflows } = useQuery({
    queryKey: ['workflows'],
    queryFn: api.workflows.list,
  });

  if (statsLoading) {
    return (
      <div className="loading-container" style={{ height: '256px' }}>
        <div className="loading-spinner" />
      </div>
    );
  }

  const statCards = [
    {
      title: 'Total Agents',
      value: stats?.total_agents ?? 0,
      icon: Users,
      accentColor: 'var(--accent)',
    },
    {
      title: 'Active Workflows',
      value: stats?.active_workflows ?? 0,
      icon: Activity,
      accentColor: 'var(--warning)',
    },
    {
      title: 'Completed Today',
      value: stats?.completed_tasks_today ?? 0,
      icon: CheckCircle,
      accentColor: 'var(--success)',
    },
    {
      title: 'Failed Today',
      value: stats?.failed_tasks_today ?? 0,
      icon: XCircle,
      accentColor: 'var(--danger)',
    },
    {
      title: 'Success Rate',
      value: `${((stats?.success_rate ?? 0) * 100).toFixed(1)}%`,
      icon: TrendingUp,
      accentColor: 'var(--accent)',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Overview of your multi-agent orchestration</p>
      </div>

      <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        {statCards.map((stat, idx) => (
          <div key={stat.title} className="stat-card card-animate" style={{ animationDelay: `${idx * 60}ms` }}>
            <CardContent style={{ padding: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span className="stat-label">{stat.title}</span>
                <stat.icon className="stat-icon" style={{ color: stat.accentColor, height: '18px', width: '18px' }} />
              </div>
              <p className="stat-value mono-value">{stat.value}</p>
            </CardContent>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))' }}>
        <Card className="card-animate">
          <CardHeader>
            <CardTitle>Recent Agents</CardTitle>
          </CardHeader>
          <CardContent>
            {agents && agents.length > 0 ? (
              <div>
                {agents.slice(0, 5).map((agent: any) => (
                  <div key={agent.id} className="data-row">
                    <div>
                      <p style={{ fontWeight: 500, fontSize: '0.9rem' }}>{agent.name}</p>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontFamily: 'JetBrains Mono, monospace' }}>
                        {agent.model_provider} / {agent.model_name}
                      </p>
                    </div>
                    <Badge className={agent.status === 'idle' ? 'status-completed' : 'status-running'}>
                      {agent.status}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={Users}
                heading="No agents yet"
                description="Create your first agent to get started"
              />
            )}
          </CardContent>
        </Card>

        <Card className="card-animate" style={{ animationDelay: '80ms' }}>
          <CardHeader>
            <CardTitle>Recent Workflows</CardTitle>
          </CardHeader>
          <CardContent>
            {workflows && workflows.length > 0 ? (
              <div>
                {workflows.slice(0, 5).map((workflow: any) => (
                  <div key={workflow.id} className="data-row">
                    <div>
                      <p style={{ fontWeight: 500, fontSize: '0.9rem' }}>{workflow.name}</p>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        {workflow.agent_ids?.length || 0} agents
                      </p>
                    </div>
                    <Badge className={
                      workflow.status === 'completed' ? 'status-completed' :
                      workflow.status === 'running' ? 'status-running' :
                      'status-idle'
                    }>
                      {workflow.status}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={Workflow}
                heading="No workflows yet"
                description="Create your first workflow to orchestrate agents"
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
