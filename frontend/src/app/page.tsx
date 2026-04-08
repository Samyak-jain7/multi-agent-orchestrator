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
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center">
          <div className="flex items-center gap-2 mr-8">
            <Bot className="h-6 w-6" />
            <span className="font-bold text-lg">Agent Orchestrator</span>
          </div>

          <nav className="flex items-center gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  activeTab === tab.id
                    ? 'bg-muted text-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="container py-6">
        {renderContent()}
      </main>
    </div>
  );
}
