import { create } from 'zustand';
import type { Agent, Workflow, Task, DashboardStats, ExecutionEvent } from '@/types';

interface AppState {
  selectedAgent: Agent | null;
  selectedWorkflow: Workflow | null;
  dashboardStats: DashboardStats | null;
  recentEvents: ExecutionEvent[];
  isExecuting: boolean;

  setSelectedAgent: (agent: Agent | null) => void;
  setSelectedWorkflow: (workflow: Workflow | null) => void;
  setDashboardStats: (stats: DashboardStats | null) => void;
  addExecutionEvent: (event: ExecutionEvent) => void;
  clearRecentEvents: () => void;
  setIsExecuting: (isExecuting: boolean) => void;
}

export const useStore = create<AppState>((set) => ({
  selectedAgent: null,
  selectedWorkflow: null,
  dashboardStats: null,
  recentEvents: [],
  isExecuting: false,

  setSelectedAgent: (agent) => set({ selectedAgent: agent }),
  setSelectedWorkflow: (workflow) => set({ selectedWorkflow: workflow }),
  setDashboardStats: (stats) => set({ dashboardStats: stats }),
  addExecutionEvent: (event) =>
    set((state) => ({
      recentEvents: [event, ...state.recentEvents].slice(0, 100),
    })),
  clearRecentEvents: () => set({ recentEvents: [] }),
  setIsExecuting: (isExecuting) => set({ isExecuting }),
}));
