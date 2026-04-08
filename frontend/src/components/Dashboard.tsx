'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Activity, Users, Workflow, CheckCircle, XCircle, TrendingUp } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

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
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  const statCards = [
    {
      title: 'Total Agents',
      value: stats?.total_agents || 0,
      icon: Users,
      color: 'text-blue-600',
    },
    {
      title: 'Active Workflows',
      value: stats?.active_workflows || 0,
      icon: Activity,
      color: 'text-orange-600',
    },
    {
      title: 'Completed Today',
      value: stats?.completed_tasks_today || 0,
      icon: CheckCircle,
      color: 'text-green-600',
    },
    {
      title: 'Failed Today',
      value: stats?.failed_tasks_today || 0,
      icon: XCircle,
      color: 'text-red-600',
    },
    {
      title: 'Success Rate',
      value: `${((stats?.success_rate || 0) * 100).toFixed(1)}%`,
      icon: TrendingUp,
      color: 'text-purple-600',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">Overview of your multi-agent orchestration</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {statCards.map((stat) => (
          <Card key={stat.title}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-muted-foreground">{stat.title}</p>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </div>
              <p className="text-2xl font-bold">{stat.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Agents</CardTitle>
          </CardHeader>
          <CardContent>
            {agents && agents.length > 0 ? (
              <div className="space-y-4">
                {agents.slice(0, 5).map((agent: any) => (
                  <div key={agent.id} className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{agent.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {agent.model_provider} / {agent.model_name}
                      </p>
                    </div>
                    <Badge className={agent.status === 'idle' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}>
                      {agent.status}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No agents created yet</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Workflows</CardTitle>
          </CardHeader>
          <CardContent>
            {workflows && workflows.length > 0 ? (
              <div className="space-y-4">
                {workflows.slice(0, 5).map((workflow: any) => (
                  <div key={workflow.id} className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{workflow.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {workflow.agent_ids?.length || 0} agents
                      </p>
                    </div>
                    <Badge className={
                      workflow.status === 'completed' ? 'bg-green-100 text-green-700' :
                      workflow.status === 'running' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }>
                      {workflow.status}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No workflows created yet</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
