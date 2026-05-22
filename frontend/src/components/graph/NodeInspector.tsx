// ==============================================================================
// Project ARGUS-INT - Node Inspector Panel
// Displays properties, relationships, and suggestions for pivoting.
// ==============================================================================

'use client';

import React, { useEffect, useState } from 'react';
import { useAppStore } from '@/lib/store';
import { api } from '@/lib/api';

export function NodeInspector() {
  const selectedNodeId = useAppStore((s) => s.selectedNodeId);
  const nodes = useAppStore((s) => s.nodes);
  const inspectorOpen = useAppStore((s) => s.inspectorOpen);
  const setInspectorOpen = useAppStore((s) => s.setInspectorOpen);

  const [pivots, setPivots] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  useEffect(() => {
    if (!selectedNode) return;
    setLoading(true);
    api.getPivotSuggestions(selectedNode.id)
      .then((res) => setPivots(res))
      .catch(() => setPivots([]))
      .finally(() => setLoading(false));
  }, [selectedNode]);

  if (!selectedNode) return null;

  return (
    <div className={`node-inspector ${inspectorOpen ? 'open' : ''}`}>
      <div className="node-inspector-header">
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--accent-secondary)' }}>
          INSPECTEUR D'ENTITÉ
        </h3>
        <button className="btn-icon" onClick={() => setInspectorOpen(false)}>
          <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" width="18" height="18">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div style={{ marginBottom: 'var(--space-lg)' }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '2px' }}>
          Type : {selectedNode.type}
        </div>
        <div className="mono" style={{ fontSize: '14px', fontWeight: 700, wordBreak: 'break-all', color: 'var(--accent-primary)' }}>
          {selectedNode.label}
        </div>
      </div>

      <div style={{ marginBottom: 'var(--space-lg)' }}>
        <h4 style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 'var(--space-sm)', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
          Propriétés
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {Object.entries(selectedNode.data || {}).map(([key, val]) => (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{key}</span>
              <span className="mono" style={{ color: 'var(--text-primary)' }}>{String(val)}</span>
            </div>
          ))}
          {selectedNode.first_seen && (
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span style={{ color: 'var(--text-secondary)' }}>First Seen</span>
              <span className="mono" style={{ color: 'var(--text-muted)' }}>
                {new Date(selectedNode.first_seen).toLocaleString()}
              </span>
            </div>
          )}
        </div>
      </div>

      <div>
        <h4 style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 'var(--space-sm)', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
          Pivots Suggérés (Auto-OSINT)
        </h4>

        {loading ? (
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Calcul des corrélations...</div>
        ) : pivots.length === 0 ? (
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Aucun pivot évident identifié</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
            {pivots.map((p, idx) => (
              <div key={idx} style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-subtle)',
                padding: 'var(--space-sm)',
                borderRadius: 'var(--radius-md)',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div>
                  <span className="mono" style={{ color: 'var(--accent-primary)', display: 'block', wordBreak: 'break-all' }}>
                    {p.properties.ip || p.properties.email || p.uid}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    Score: {p.pivot_score} | {p.entity_type}
                  </span>
                </div>
                <button className="btn-icon" title="Lancer une investigation sur cette cible" style={{ color: 'var(--accent-secondary)' }}>
                  <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" width="16" height="16">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12.75 15l3-3m0 0l-3-3m3 3h-7.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
export default NodeInspector;
