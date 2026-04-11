'use client';

import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { Loader2, RefreshCw, Play, StopCircle, Activity } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';
import type { ExecutionEvent, Workflow } from '@/types';

function getEventColor(event: ExecutionEvent): string {
  switch (event.event_type || event.type) {
    case 'workflow_started':
    case 'task_started':
      return 'var(--accent)';
    case 'workflow_completed':
    case 'task_completed':
      return 'var(--success)';
    case 'task_failed':
      return 'var(--danger)';
    default:
      return 'var(--text-muted)';
  }
}

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
    const color = getEventColor(event);
    switch (event.event_type || event.type) {
      case 'workflow_started':
      case 'task_started':
        return <Play style={{ color, height: '16px', width: '16px' }} />;
      case 'workflow_completed':
      case 'task_completed':
        return <RefreshCw style={{ color, height: '16px', width: '16px' }} />;
      case 'task_failed':
        return <StopCircle style={{ color, height: '16px', width: '16px' }} />;
      case 'heartbeat':
        return <RefreshCw style={{ color: 'var(--text-muted)', height: '16px', width: '16px', animation: 'spin 1s linear infinite' }} />;
      default:
        return <Activity style={{ color: 'var(--text-muted)', height: '16px', width: '16px' }} />;
    }
  };

  return (
    <div className="space-y-6">
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <h2>Event Stream</h2>
          <p>Real-time execution monitoring</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
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
            style={{ width: '240px' }}
            disabled={isStreaming}
          />
          {!isStreaming ? (
            <Button onClick={startStreaming} disabled={!selectedWorkflowId}>
              <Play className="h-4 w-4" />
              Start Stream
            </Button>
          ) : (
            <Button variant="destructive" onClick={stopStreaming}>
              <StopCircle className="h-4 w-4" />
              Stop Stream
            </Button>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>Live Events</span>
            {isStreaming && (
              <div className="live-badge">
                <span className="live-dot" />
                Live
              </div>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {events.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '400px', overflowY: 'auto' }}>
              {events.map((event, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '12px',
                    padding: '12px',
                    borderRadius: 'var(--radius)',
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid var(--border)',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.04)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                >
                  <div style={{ marginTop: '2px', flexShrink: 0 }}>
                    {getEventIcon(event)}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 500, fontSize: '0.875rem', fontFamily: 'Chakra Petch, sans-serif' }}>
                        {event.event_type || event.type}
                      </span>
                      {event.task_id && (
                        <Badge variant="outline" style={{ fontSize: '0.7rem', fontFamily: 'JetBrains Mono, monospace' }}>
                          Task: {String(event.task_id).slice(0, 8)}...
                        </Badge>
                      )}
                    </div>
                    {event.message && (
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {event.message}
                      </p>
                    )}
                    <p className="mono-value" style={{ fontSize: '0.75rem', marginTop: '4px' }}>
                      {event.timestamp ? formatRelativeTime(event.timestamp) : 'Unknown time'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="loading-container" style={{ height: '200px' }}>
              <div style={{ textAlign: 'center' }}>
                {isStreaming ? (
                  <>
                    <div className="loading-spinner" style={{ margin: '0 auto' }} />
                    <p style={{ marginTop: '12px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                      Waiting for events...
                    </p>
                  </>
                ) : (
                  <div className="empty-state" style={{ padding: '24px' }}>
                    <Activity className="empty-state-icon" style={{ width: '36px', height: '36px' }} />
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                      {runningWorkflows.length > 0
                        ? 'Select a running workflow and start streaming'
                        : 'No workflows are currently running'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
