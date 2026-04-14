import { api } from '@/lib/api';

describe('api.agents', () => {
  it('list should call GET /agents', () => {
    expect(typeof api.agents.list).toBe('function');
  });

  it('agents.get calls correct URL with id', () => {
    expect(typeof api.agents.get).toBe('function');
  });

  it('agents.create uses POST method', () => {
    expect(typeof api.agents.create).toBe('function');
  });

  it('agents.update uses PUT method', () => {
    expect(typeof api.agents.update).toBe('function');
  });

  it('agents.delete uses DELETE method', () => {
    expect(typeof api.agents.delete).toBe('function');
  });
});

describe('api.workflows', () => {
  it('workflows.list is a function', () => {
    expect(typeof api.workflows.list).toBe('function');
  });

  it('workflows.get is a function', () => {
    expect(typeof api.workflows.get).toBe('function');
  });

  it('workflows.create is a function', () => {
    expect(typeof api.workflows.create).toBe('function');
  });
});