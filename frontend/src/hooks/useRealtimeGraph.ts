// ==============================================================================
// Project ARGUS-INT - Real-Time Graph Hook (WebSocket Stream)
// ==============================================================================

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { useWebSocket } from './useWebSocket';

interface GraphData {
  nodes: any[];
  edges: any[];
}

export function useRealtimeGraph(investigationId: string) {
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // 1. Initial Load of Graph Data
  useEffect(() => {
    let active = true;
    setLoading(true);
    
    api.getGraph(investigationId)
      .then((data) => {
        if (active) {
          setNodes(data.nodes);
          setEdges(data.edges);
        }
      })
      .catch((err) => console.error('[useRealtimeGraph] Failed to load graph:', err))
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [investigationId]);

  // 2. Real-Time Streaming Updates via WebSocket
  const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/ws/graph/${investigationId}`;
  
  const { status: wsStatus } = useWebSocket({
    url: wsUrl,
    enabled: !!investigationId && !api.isMockMode(),
    onMessage: (message: any) => {
      // Process updates (e.g. node_added, edge_added, status_changed)
      if (message && typeof message === 'object') {
        if (message.type === 'node_added') {
          setNodes((prev) => {
            if (prev.some((n) => n.id === message.node.id)) return prev;
            return [...prev, message.node];
          });
        } else if (message.type === 'edge_added') {
          setEdges((prev) => {
            if (prev.some((e) => e.source === message.edge.source && e.target === message.edge.target)) return prev;
            return [...prev, message.edge];
          });
        } else if (message.type === 'bulk_update') {
          if (message.nodes) {
            setNodes((prev) => {
              const prevMap = new Map(prev.map(n => [n.id, n]));
              message.nodes.forEach((n: any) => prevMap.set(n.id, n));
              return Array.from(prevMap.values());
            });
          }
          if (message.edges) {
            setEdges((prev) => {
              const existingKeys = new Set(prev.map(e => `${e.source}->${e.target}`));
              const newEdges = message.edges.filter((e: any) => !existingKeys.has(`${e.source}->${e.target}`));
              return [...prev, ...newEdges];
            });
          }
        }
      }
    }
  });

  return { nodes, edges, loading, wsStatus };
}
