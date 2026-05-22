// ==============================================================================
// Project ARGUS-INT - Hybrid Graph Visualizer (WebGL / Canvas Engine)
// Draws high-density nodes, customized colors, and handles interactions.
// ==============================================================================

'use client';

import React, { useRef, useEffect, useState, useMemo } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { useAppStore } from '@/lib/store';
import type { GraphNode, GraphEdge } from '@/lib/mock-data';

interface HybridGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export function HybridGraph({ nodes, edges }: HybridGraphProps) {
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const selectNode = useAppStore((s) => s.selectedNodeId);
  const onSelectNode = useAppStore((s) => s.selectNode);

  // Auto-resize graph to container dimensions
  useEffect(() => {
    if (!containerRef.current) return;
    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // Format node colors according to design system tokens
  const nodeColors: Record<string, string> = {
    email: '#00d4ff',
    username: '#00ff41',
    ip: '#ff6b00',
    domain: '#ffd700',
    wallet: '#a855f7',
    person: '#ff69b4',
    service: '#888888',
    phone: '#20b2aa',
  };

  // Format data for react-force-graph
  const graphData = useMemo(() => {
    return {
      nodes: nodes.map((n) => ({
        id: n.id,
        label: n.label,
        type: n.type,
        val: n.type === 'person' ? 6 : 4,
      })),
      links: edges.map((e) => ({
        source: e.source,
        target: e.target,
        type: e.type,
        confidence: e.confidence,
      })),
    };
  }, [nodes, edges]);

  // Adjust rendering detail depending on density
  const isHighDensity = graphData.nodes.length > 500;

  // Custom node rendering for premium look and high-density performance
  const drawNode = (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const label = node.label || node.id;
    const fontSize = 11 / globalScale;
    const r = node.val || 4;
    const color = nodeColors[node.type] || '#fff';
    const isSelected = node.id === selectNode;

    // Node body
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
    ctx.fillStyle = color;
    ctx.fill();

    // Selected highlight / Glow ring
    if (isSelected) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 4, 0, 2 * Math.PI, false);
      ctx.strokeStyle = '#00ff41';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Render labels only when zoomed in or graph is not too dense to maintain FPS
    if (globalScale > 1.2 && !isHighDensity) {
      ctx.font = `${fontSize}px var(--font-mono)`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
      ctx.fillText(label, node.x, node.y + r + 2);
    }
  };

  // Custom edge/link drawing
  const drawLink = (link: any, ctx: CanvasRenderingContext2D) => {
    const start = link.source;
    const end = link.target;
    if (typeof start !== 'object' || typeof end !== 'object') return;

    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
    
    // Line color based on confidence score
    ctx.strokeStyle = `rgba(42, 42, 56, ${link.confidence || 0.5})`;
    ctx.lineWidth = (link.confidence || 0.5) * 2;
    ctx.stroke();
  };

  return (
    <div ref={containerRef} className="graph-container">
      <ForceGraph2D
        ref={fgRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        nodeCanvasObject={drawNode}
        linkCanvasObject={drawLink}
        nodePointerAreaPaint={(node: any, color, ctx) => {
          ctx.beginPath();
          ctx.arc(node.x, node.y, (node.val || 4) + 2, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
        onNodeClick={(node: any) => {
          onSelectNode(node.id);
        }}
        onBackgroundClick={() => {
          onSelectNode(null);
        }}
        cooldownTicks={100}
        d3AlphaDecay={0.03}
        d3VelocityDecay={0.08}
      />
    </div>
  );
}
export default HybridGraph;
