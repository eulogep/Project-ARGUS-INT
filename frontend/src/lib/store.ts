// ==============================================================================
// ARGUS-INT — Zustand Store with IndexedDB Persistence
// ==============================================================================

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { get as idbGet, set as idbSet, del as idbDel, clear as idbClear } from 'idb-keyval';
import type { GraphNode, GraphEdge, Investigation, WorkerInfo } from '@/lib/mock-data';

// ── IndexedDB Storage Adapter for Zustand ───────────────────────

const idbStorage = createJSONStorage(() => ({
  getItem: async (name: string): Promise<string | null> => {
    const val = await idbGet(name);
    return val ?? null;
  },
  setItem: async (name: string, value: string): Promise<void> => {
    await idbSet(name, value);
  },
  removeItem: async (name: string): Promise<void> => {
    await idbDel(name);
  },
}));

// ── Types ───────────────────────────────────────────────────────

interface GraphFilter {
  nodeTypes: string[];
  minConfidence: number;
  investigationId: string | null;
  timeRange: [number, number] | null; // Unix timestamps
}

interface AppState {
  // Graph
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: string | null;
  graphFilter: GraphFilter;

  // Investigations
  investigations: Investigation[];
  activeInvestigationId: string | null;

  // Workers
  workers: WorkerInfo[];

  // UI
  sidebarOpen: boolean;
  privacyBlur: boolean;
  dataDensity: 'comfortable' | 'dense';
  effectsEnabled: boolean;
  inspectorOpen: boolean;

  // Actions — Graph
  setGraph: (nodes: GraphNode[], edges: GraphEdge[]) => void;
  selectNode: (id: string | null) => void;
  setGraphFilter: (filter: Partial<GraphFilter>) => void;
  getFilteredGraph: () => { nodes: GraphNode[]; edges: GraphEdge[] };

  // Actions — Investigations
  setInvestigations: (investigations: Investigation[]) => void;
  setActiveInvestigation: (id: string | null) => void;
  addInvestigation: (inv: Investigation) => void;
  updateInvestigationStatus: (id: string, status: Investigation['status'], resultCount?: number) => void;

  // Actions — Workers
  setWorkers: (workers: WorkerInfo[]) => void;

  // Actions — UI
  toggleSidebar: () => void;
  togglePrivacyBlur: () => void;
  toggleDensity: () => void;
  toggleEffects: () => void;
  setInspectorOpen: (open: boolean) => void;

  // Actions — Panic
  wipeAllData: () => void;
}

// ── Store ────────────────────────────────────────────────────────

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Initial state
      nodes: [],
      edges: [],
      selectedNodeId: null,
      graphFilter: {
        nodeTypes: [],
        minConfidence: 0,
        investigationId: null,
        timeRange: null,
      },
      investigations: [],
      activeInvestigationId: null,
      workers: [],
      sidebarOpen: true,
      privacyBlur: false,
      dataDensity: 'comfortable',
      effectsEnabled: false,
      inspectorOpen: false,

      // Graph actions
      setGraph: (nodes, edges) => set({ nodes, edges }),

      selectNode: (id) => set({ selectedNodeId: id, inspectorOpen: id !== null }),

      setGraphFilter: (filter) =>
        set((s) => ({ graphFilter: { ...s.graphFilter, ...filter } })),

      getFilteredGraph: () => {
        const { nodes, edges, graphFilter } = get();
        let filteredNodes = nodes;
        let filteredEdges = edges;

        if (graphFilter.nodeTypes.length > 0) {
          filteredNodes = filteredNodes.filter((n) =>
            graphFilter.nodeTypes.includes(n.type)
          );
        }

        if (graphFilter.timeRange) {
          const [start, end] = graphFilter.timeRange;
          filteredNodes = filteredNodes.filter((n) => {
            if (!n.first_seen) return true;
            const t = new Date(n.first_seen).getTime();
            return t >= start && t <= end;
          });
          filteredEdges = filteredEdges.filter((e) => {
            if (!e.first_seen) return true;
            const t = new Date(e.first_seen).getTime();
            return t >= start && t <= end;
          });
        }

        if (graphFilter.minConfidence > 0) {
          filteredEdges = filteredEdges.filter(
            (e) => e.confidence >= graphFilter.minConfidence
          );
        }

        const nodeIds = new Set(filteredNodes.map((n) => n.id));
        filteredEdges = filteredEdges.filter(
          (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
        );

        return { nodes: filteredNodes, edges: filteredEdges };
      },

      // Investigation actions
      setInvestigations: (investigations) => set({ investigations }),
      setActiveInvestigation: (id) => set({ activeInvestigationId: id }),
      addInvestigation: (inv) =>
        set((s) => ({ investigations: [inv, ...s.investigations] })),
      updateInvestigationStatus: (id, status, resultCount) =>
        set((s) => ({
          investigations: s.investigations.map((inv) =>
            inv.id === id
              ? { ...inv, status, result_count: resultCount ?? inv.result_count }
              : inv
          ),
        })),

      // Worker actions
      setWorkers: (workers) => set({ workers }),

      // UI actions
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      togglePrivacyBlur: () => set((s) => ({ privacyBlur: !s.privacyBlur })),
      toggleDensity: () =>
        set((s) => ({
          dataDensity: s.dataDensity === 'comfortable' ? 'dense' : 'comfortable',
        })),
      toggleEffects: () => set((s) => ({ effectsEnabled: !s.effectsEnabled })),
      setInspectorOpen: (open) => set({ inspectorOpen: open }),

      // Panic mode
      wipeAllData: () => {
        idbClear();
        localStorage.clear();
        sessionStorage.clear();
        set({
          nodes: [],
          edges: [],
          selectedNodeId: null,
          investigations: [],
          activeInvestigationId: null,
          workers: [],
          inspectorOpen: false,
        });
      },
    }),
    {
      name: 'argus-int-store',
      storage: idbStorage,
      partialize: (state) => ({
        dataDensity: state.dataDensity,
        effectsEnabled: state.effectsEnabled,
        sidebarOpen: state.sidebarOpen,
      }),
    }
  )
);
