'use client';

import { useState } from 'react';
import { Dashboard } from '@/components/Dashboard';
import { AgentList } from '@/components/AgentList';
import { WorkflowList } from '@/components/WorkflowList';
import { TaskList } from '@/components/TaskList';
import { EventStream } from '@/components/EventStream';
import { Bot, Workflow, ListTodo, Activity, LayoutDashboard } from 'lucide-react';

type TabType = 'dashboard' | 'agents' | 'workflows' | 'tasks' | 'events';

const tabs: { id: TabType; label: string; icon: React.ElementType }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'agents', label: 'Agents', icon: Bot },
  { id: 'workflows', label: 'Workflows', icon: Workflow },
  { id: 'tasks', label: 'Tasks', icon: ListTodo },
  { id: 'events', label: 'Events', icon: Activity },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'agents':
        return <AgentList />;
      case 'workflows':
        return <WorkflowList />;
      case 'tasks':
        return <TaskList />;
      case 'events':
        return <EventStream />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b" style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
        <div className="container" style={{ display: 'flex', height: '60px', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginRight: '32px' }}>
            <Bot className="h-6 w-6" style={{ color: 'var(--accent)' }} />
            <span style={{ fontFamily: 'Chakra Petch, sans-serif', fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-primary)' }}>
              Agent Orchestrator
            </span>
          </div>

          <nav className="nav-tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="container" style={{ paddingTop: '24px', paddingBottom: '24px' }}>
        {renderContent()}
      </main>
    </div>
  );
}
