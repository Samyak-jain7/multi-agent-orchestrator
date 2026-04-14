import { useStore } from '@/lib/store';

describe('useStore', () => {
  it('has selectedAgent state', () => {
    const state = useStore.getState();
    expect(state.selectedAgent).toBeNull();
  });

  it('has selectedWorkflow state', () => {
    const state = useStore.getState();
    expect(state.selectedWorkflow).toBeNull();
  });

  it('has dashboardStats state', () => {
    const state = useStore.getState();
    expect(state.dashboardStats).toBeNull();
  });

  it('has recentEvents state as empty array', () => {
    const state = useStore.getState();
    expect(Array.isArray(state.recentEvents)).toBe(true);
    expect(state.recentEvents).toHaveLength(0);
  });

  it('has isExecuting state as false', () => {
    const state = useStore.getState();
    expect(state.isExecuting).toBe(false);
  });

  it('setSelectedAgent updates state', () => {
    const agent = { id: 'agent-1', name: 'Test Agent' } as any;
    useStore.getState().setSelectedAgent(agent);
    expect(useStore.getState().selectedAgent).toEqual(agent);
    useStore.getState().setSelectedAgent(null);
  });

  it('setSelectedWorkflow updates state', () => {
    const workflow = { id: 'wf-1', name: 'Test Workflow' } as any;
    useStore.getState().setSelectedWorkflow(workflow);
    expect(useStore.getState().selectedWorkflow).toEqual(workflow);
    useStore.getState().setSelectedWorkflow(null);
  });

  it('setDashboardStats updates state', () => {
    const stats = { total_tasks: 10, completed: 5 } as any;
    useStore.getState().setDashboardStats(stats);
    expect(useStore.getState().dashboardStats).toEqual(stats);
    useStore.getState().setDashboardStats(null);
  });
});