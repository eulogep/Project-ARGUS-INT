// ==============================================================================
// Project ARGUS-INT - Secure C2 API Client
// ==============================================================================

import { mockInvestigations, mockNodes, mockEdges, mockWorkers } from './mock-data';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private useMock: boolean = true;
  private token: string | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      const mode = localStorage.getItem('argus-api-mode');
      this.useMock = mode !== 'live';
      this.token = localStorage.getItem('argus-jwt-token');
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

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('argus-jwt-token', token);
      } else {
        localStorage.removeItem('argus-jwt-token');
      }
    }
  }

  getToken() {
    return this.token;
  }

  /**
   * Helper method to perform requests with automatic retries, backoff, and header injection.
   */
  private async request(path: string, options: RequestInit = {}, retries = 3, delay = 1000): Promise<any> {
    const headers = new Headers(options.headers || {});
    
    // Inject JWT token if available (Zero Trust)
    if (this.token) {
      headers.set('Authorization', `Bearer ${this.token}`);
    }
    
    headers.set('Content-Type', 'application/json');
    headers.set('Accept', 'application/json');

    const url = `${API_BASE_URL}${path}`;

    try {
      const res = await fetch(url, { ...options, headers });
      
      if (res.status === 401) {
        // Handle token expiration / rotation logic or trigger logout redirect
        console.warn('[API] Token expired or invalid authorization.');
      }

      if (!res.ok) {
        throw new Error(`HTTP Error ${res.status}: ${res.statusText}`);
      }
      
      return await res.json();
    } catch (error) {
      if (retries > 0) {
        console.warn(`[API] Fetch failed. Retrying in ${delay}ms... (${retries} attempts left). Error:`, error);
        await new Promise(resolve => setTimeout(resolve, delay));
        return this.request(path, options, retries - 1, delay * 2);
      }
      throw error;
    }
  }

  async getInvestigations(): Promise<any[]> {
    if (this.useMock) {
      return Promise.resolve(mockInvestigations);
    }
    try {
      return await this.request('/api/v1/investigations');
    } catch (e) {
      console.warn('[API] Backend connection failed, falling back to mock data.', e);
      return mockInvestigations;
    }
  }

  async createInvestigation(target: string, targetType: string, depth: number): Promise<any> {
    const newInv = {
      investigation_id: `inv-${Math.random().toString(36).substr(2, 6)}`,
      target,
      target_type: targetType,
      depth,
      status: 'PENDING' as const,
      created_at: new Date().toISOString(),
      result_count: 0,
      message: `Target: ${target}`
    };

    if (this.useMock) {
      mockInvestigations.unshift(newInv as any);
      return Promise.resolve(newInv);
    }

    try {
      return await this.request('/api/v1/investigations', {
        method: 'POST',
        body: JSON.stringify({ target, target_type: targetType, depth }),
      });
    } catch (e) {
      console.warn('[API] Backend creation failed, falling back to mock simulator.', e);
      mockInvestigations.unshift(newInv as any);
      return newInv;
    }
  }

  async getGraph(investigationId?: string): Promise<{ nodes: any[]; edges: any[] }> {
    if (this.useMock) {
      return Promise.resolve({ nodes: mockNodes, edges: mockEdges });
    }
    try {
      const path = investigationId 
        ? `/api/v1/graph/export?investigation_id=${investigationId}`
        : '/api/v1/graph/export';
      const data = await this.request(path);
      // Map properties from Neo4j structure if necessary to nodes/edges
      const nodes = (data.nodes || []).map((n: any) => ({
        id: n.id,
        label: n.label,
        ...n.data
      }));
      const edges = (data.edges || []).map((e: any) => ({
        source: e.source,
        target: e.target,
        type: e.type,
        ...e.data
      }));
      return { nodes, edges };
    } catch (e) {
      console.warn('[API] Backend graph fetch failed, falling back to mock.', e);
      return { nodes: mockNodes, edges: mockEdges };
    }
  }

  async getPivotSuggestions(nodeUid: string): Promise<any[]> {
    if (this.useMock) {
      return Promise.resolve([
        { uid: 'pivot-' + Math.random().toString(36).substr(2, 5), entity_type: 'ip', pivot_score: 4.8, properties: { ip: '185.220.101.50', country: 'DE' } },
        { uid: 'pivot-' + Math.random().toString(36).substr(2, 5), entity_type: 'email', pivot_score: 3.5, properties: { email: 'leak-admin@onion.net' } },
      ]);
    }
    try {
      return await this.request(`/api/v1/graph/pivots?uid=${nodeUid}`);
    } catch (e) {
      console.error('[API] Failed to retrieve pivot suggestions:', e);
      return [];
    }
  }

  async getWorkers(): Promise<any[]> {
    if (this.useMock) {
      return Promise.resolve(mockWorkers);
    }
    try {
      return await this.request('/api/v1/modules/workers');
    } catch (e) {
      console.warn('[API] Failed to fetch active workers from backend.', e);
      return mockWorkers;
    }
  }
}

export const api = new ApiClient();
