'use client';

import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { Loader2, RefreshCw, Play, StopCircle } from 'lucide-react';
import { getStatusColor, formatRelativeTime } from '@/lib/utils';
import type { ExecutionEvent, Workflow } from '@/types';

export function EventStream() {
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  const { data: workflows } = useQuery({
    queryKey: ['workflows'],
    queryFn: api.workflows.list,
  });

  const runningWorkflows = workflows?.filter(
    (w: Workflow) => w.status === 'running'
  ) || [];

  useEffect(() => {
    if (runningWorkflows.length > 0 && !selectedWorkflowId) {
      setSelectedWorkflowId(runningWorkflows[0].id);
    }
  }, [runningWorkflows, selectedWorkflowId]);

  const startStreaming = () => {
    if (!selectedWorkflowId) return;

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setIsStreaming(true);
    setEvents([]);

    const eventSource = new EventSource(
      api.execution.streamWorkflow(selectedWorkflowId)
    );

    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setEvents((prev) => [data, ...prev].slice(0, 100));
      } catch (e) {
        console.error('Failed to parse event:', e);
      }
    };

    eventSource.onerror = () => {
      setIsStreaming(false);
      eventSource.close();
    };
  };

  const stopStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsStreaming(false);
  };

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const getEventIcon = (event: ExecutionEvent) => {
    switch (event.event_type || event.type) {
      case 'workflow_started':
        return <Play className="h-4 w-4 text-blue-500" />;
      case 'workflow_completed':
        return <RefreshCw className="h-4 w-4 text-green-500" />;
      case 'task_started':
        return <Play className="h-4 w-4 text-blue-400" />;
      case 'task_completed':
        return <RefreshCw className="h-4 w-4 text-green-400" />;
      case 'task_failed':
        return <StopCircle className="h-4 w-4 text-red-400" />;
      case 'heartbeat':
        return <RefreshCw className="h-4 w-4 text-gray-400 animate-spin" />;
      default:
        return <RefreshCw className="h-4 w-4 text-gray-400" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Event Stream</h2>
          <p className="text-muted-foreground">Real-time execution monitoring</p>
        </div>
        <div className="flex items-center gap-4">
          <Select
            value={selectedWorkflowId}
            onChange={(e) => setSelectedWorkflowId(e.target.value)}
            options={[
              { value: '', label: 'Select workflow' },
              ...runningWorkflows.map((w: Workflow) => ({
                value: w.id,
                label: `${w.name} (running)`,
              })),
            ]}
            className="w-64"
            disabled={isStreaming}
          />
          {!isStreaming ? (
            <Button onClick={startStreaming} disabled={!selectedWorkflowId}>
              <Play className="mr-2 h-4 w-4" />
              Start Stream
            </Button>
          ) : (
            <Button variant="destructive" onClick={stopStreaming}>
              <StopCircle className="mr-2 h-4 w-4" />
              Stop Stream
            </Button>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Live Events</span>
            {isStreaming && (
              <Badge className="bg-green-100 text-green-700 animate-pulse">
                Live
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {events.length > 0 ? (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {events.map((event, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-3 rounded-md bg-muted/50 hover:bg-muted transition-colors"
                >
                  <div className="mt-0.5">{getEventIcon(event)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-sm">
                        {event.event_type || event.type}
                      </p>
                      {event.task_id && (
                        <Badge variant="outline" className="text-xs">
                          Task: {event.task_id.slice(0, 8)}...
                        </Badge>
                      )}
                    </div>
                    {event.message && (
                      <p className="text-sm text-muted-foreground mt-1">
                        {event.message}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground mt-1">
                      {event.timestamp
                        ? formatRelativeTime(event.timestamp)
                        : 'Unknown time'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex h-48 items-center justify-center">
              <div className="text-center">
                {isStreaming ? (
                  <>
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mx-auto" />
                    <p className="mt-2 text-muted-foreground">Waiting for events...</p>
                  </>
                ) : (
                  <>
                    <p className="text-muted-foreground">
                      {runningWorkflows.length > 0
                        ? 'Select a running workflow and start streaming'
                        : 'No workflows are currently running'}
                    </p>
                  </>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
