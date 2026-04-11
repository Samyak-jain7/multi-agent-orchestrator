import { clsx, type ClassValue } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return '-';
  return new Date(date).toLocaleString();
}

export function formatRelativeTime(date: string | null | undefined): string {
  if (!date) return '-';

  const now = new Date();
  const then = new Date(date);
  const diffMs = now.getTime() - then.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;

  return formatDate(date);
}

/* Status badge color classes — match CSS variable system */
export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    idle: 'status-idle',
    pending: 'status-pending',
    running: 'status-running',
    completed: 'status-completed',
    failed: 'status-failed',
    cancelled: 'status-cancelled',
    busy: 'status-busy',
    error: 'status-failed',
  };
  return colors[status] || 'status-idle';
}

export function getProviderLabel(provider: string): string {
  const labels: Record<string, string> = {
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    ollama: 'Ollama',
  };
  return labels[provider] || provider;
}
