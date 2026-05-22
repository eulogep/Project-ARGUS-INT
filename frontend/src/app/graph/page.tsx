// ==============================================================================
// Project ARGUS-INT - Graph Explorer Page (Full Screen)
// ==============================================================================

'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { useAppStore } from '@/lib/store';
import { NodeInspector } from '@/components/graph/NodeInspector';
import { GraphControls } from '@/components/graph/GraphControls';
import { TemporalSlider } from '@/components/graph/TemporalSlider';
import { api } from '@/lib/api';

const HybridGraph = dynamic(() => import('@/components/graph/HybridGraph').then(mod => mod.HybridGraph), { ssr: false });

export default function GraphExplorerPage() {
  const { setGraph, getFilteredGraph, nodes } = useAppStore();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (nodes.length === 0) {
      setLoading(true);
      api.getGraph()
        .then((res) => {
          setGraph(res.nodes, res.edges);
        })
        .finally(() => setLoading(false));
    }
  }, [nodes.length, setGraph]);

  const { nodes: filteredNodes, edges: filteredEdges } = getFilteredGraph();

  return (
    <div style={{ position: 'relative', width: '100%', height: 'calc(100vh - var(--topbar-height) - 32px - 2 * var(--space-lg))', overflow: 'hidden', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)' }} className="animate-in">
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)' }}>
          <span>Extraction topologique de la base de données...</span>
        </div>
      ) : (
        <>
          <HybridGraph nodes={filteredNodes} edges={filteredEdges} />
          <GraphControls />
          <NodeInspector />
          <TemporalSlider />
        </>
      )}
    </div>
  );
}
