// ==============================================================================
// Project ARGUS-INT - API Client
// ==============================================================================

import { mockInvestigations, mockNodes, mockEdges, mockWorkers } from './mock-data';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private useMock: boolean = true;

  constructor() {
    // Determine if we should attempt to talk to a real backend.
    // In local development or standalone deployments, this can be configured.
    if (typeof window !== 'undefined') {
      const mode = localStorage.getItem('argus-api-mode');
      this.useMock = mode !== 'live';
    }
  }

  setApiMode(mode: 'live' | 'mock') {
    this.useMock = mode === 'mock';
    if (typeof window !== 'undefined') {
      localStorage.setItem('argus-api-mode', mode);
    }
  }

  isMockMode() {
    return this.useMock;
  }

  async getInvestigations(): Promise<any[]> {
    if (this.useMock) {
      return Promise.resolve(mockInvestigations);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/investigations`);
      if (!res.ok) throw new Error('API Error');
      return await res.json();
    } catch (e) {
      console.warn('Backend API connection failed, falling back to mock data.', e);
      return mockInvestigations;
    }
  }

  async createInvestigation(target: string, targetType: string, depth: number): Promise<any> {
    const newInv = {
      id: `inv-${Math.random().toString(36).substr(2, 6)}`,
      target,
      target_type: targetType,
      depth,
      status: 'PENDING' as const,
      created_at: new Date().toISOString(),
      result_count: 0,
      modules_used: targetType === 'email' ? ['identity', 'breach'] : ['techrecon'],
    };

    if (this.useMock) {
      // Simulate backend behavior in memory
      mockInvestigations.unshift(newInv);
      return Promise.resolve(newInv);
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/investigations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target, target_type: targetType, depth }),
      });
      if (!res.ok) throw new Error('API Error');
      return await res.json();
    } catch (e) {
      console.warn('Backend API connection failed, simulated locally.', e);
      mockInvestigations.unshift(newInv);
      return newInv;
    }
  }

  async getGraph(investigationId?: string): Promise<{ nodes: any[]; edges: any[] }> {
    if (this.useMock) {
      return Promise.resolve({ nodes: mockNodes, edges: mockEdges });
    }
    try {
      const url = investigationId 
        ? `${API_BASE_URL}/api/v1/graph/export?investigation_id=${investigationId}`
        : `${API_BASE_URL}/api/v1/graph/export`;
      const res = await fetch(url);
      if (!res.ok) throw new Error('API Error');
      return await res.json();
    } catch (e) {
      console.warn('Backend API connection failed, falling back to mock graph.', e);
      return { nodes: mockNodes, edges: mockEdges };
    }
  }

  async getPivotSuggestions(nodeUid: string): Promise<any[]> {
    if (this.useMock) {
      // Return dummy pivots based on type
      return Promise.resolve([
        { uid: 'pivot-' + Math.random().toString(36).substr(2, 5), entity_type: 'ip', pivot_score: 4.8, properties: { ip: '185.220.101.50', country: 'DE' } },
        { uid: 'pivot-' + Math.random().toString(36).substr(2, 5), entity_type: 'email', pivot_score: 3.5, properties: { email: 'leak-admin@onion.net' } },
      ]);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/graph/pivots?uid=${nodeUid}`);
      if (!res.ok) throw new Error('API Error');
      return await res.json();
    } catch (e) {
      return [];
    }
  }

  async getWorkers(): Promise<any[]> {
    if (this.useMock) {
      return Promise.resolve(mockWorkers);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/modules/workers`);
      if (!res.ok) throw new Error('API Error');
      return await res.json();
    } catch (e) {
      return mockWorkers;
    }
  }
}

export const api = new ApiClient();
