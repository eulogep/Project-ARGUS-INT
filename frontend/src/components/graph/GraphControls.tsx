// ==============================================================================
// Project ARGUS-INT - Graph Controls & Exporters
// ==============================================================================

'use client';

import React, { useState } from 'react';
import { useAppStore } from '@/lib/store';

export function GraphControls() {
  const { graphFilter, setGraphFilter, nodes, edges } = useAppStore();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const filterTypes = [
    { type: 'email', label: 'Emails', color: '#00d4ff' },
    { type: 'username', label: 'Usernames', color: '#00ff41' },
    { type: 'ip', label: 'IP Addresses', color: '#ff6b00' },
    { type: 'domain', label: 'Domains', color: '#ffd700' },
    { type: 'wallet', label: 'Wallets', color: '#a855f7' },
    { type: 'person', label: 'Persons', color: '#ff69b4' },
  ];

  const handleTypeToggle = (type: string) => {
    const activeTypes = [...graphFilter.nodeTypes];
    if (activeTypes.includes(type)) {
      setGraphFilter({ nodeTypes: activeTypes.filter((t) => t !== type) });
    } else {
      setGraphFilter({ nodeTypes: [...activeTypes, type] });
    }
  };

  const handleConfidenceChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setGraphFilter({ minConfidence: Number(e.target.value) });
  };

  const triggerExport = (format: 'gexf' | 'graphml' | 'stix') => {
    let output = '';
    let filename = `argus-export-${Date.now()}`;

    if (format === 'gexf') {
      filename += '.gexf';
      output = `<?xml version="1.0" encoding="UTF-8"?>
<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">
  <graph mode="static" defaultedgetype="directed">
    <nodes>
      ${nodes.map((n) => `<node id="${n.id}" label="${n.label}" />`).join('\n      ')}
    </nodes>
    <edges>
      ${edges.map((e, idx) => `<edge id="${idx}" source="${e.source}" target="${e.target}" label="${e.type}" />`).join('\n      ')}
    </edges>
  </graph>
</gexf>`;
    } else if (format === 'graphml') {
      filename += '.graphml';
      output = `<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <graph id="G" edgedefault="directed">
    ${nodes.map((n) => `<node id="${n.id}" />`).join('\n    ')}
    ${edges.map((e, idx) => `<edge id="e${idx}" source="${e.source}" target="${e.target}" />`).join('\n    ')}
  </graph>
</graphml>`;
    } else if (format === 'stix') {
      filename += '.json';
      const stixObjects = nodes.map((n) => ({
        type: 'observed-data',
        id: `observed-data--${n.id}`,
        spec_version: '2.1',
        objects: {
          '0': {
            type: n.type === 'ip' ? 'ipv4-addr' : n.type === 'domain' ? 'domain-name' : 'email-addr',
            value: n.label,
          },
        },
      }));
      output = JSON.stringify({ type: 'bundle', id: 'bundle--1', objects: stixObjects }, null, 2);
    }

    const blob = new Blob([output], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    setDropdownOpen(false);
  };

  return (
    <div className="graph-controls">
      {/* Entity Filters Card */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        padding: 'var(--space-md)',
        borderRadius: 'var(--radius-lg)',
        width: '240px',
        boxShadow: 'var(--glow-secondary)'
      }}>
        <h4 style={{ fontSize: '11px', textTransform: 'uppercase', marginBottom: 'var(--space-sm)', color: 'var(--text-secondary)' }}>
          Filtres D'Affichage
        </h4>
        
        {/* Node type switches */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: 'var(--space-md)' }}>
          {filterTypes.map((item) => {
            const isActive = graphFilter.nodeTypes.length === 0 || graphFilter.nodeTypes.includes(item.type);
            return (
              <label key={item.type} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '12px' }}>
                <input
                  type="checkbox"
                  checked={graphFilter.nodeTypes.includes(item.type)}
                  onChange={() => handleTypeToggle(item.type)}
                  style={{ accentColor: item.color }}
                />
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: item.color }} />
                <span style={{ color: isActive ? 'var(--text-primary)' : 'var(--text-muted)' }}>{item.label}</span>
              </label>
            );
          })}
        </div>

        {/* Confidence slider */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
            <span>Confiance Min</span>
            <span className="mono" style={{ color: 'var(--accent-primary)' }}>{graphFilter.minConfidence * 100}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={graphFilter.minConfidence}
            onChange={handleConfidenceChange}
            style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
          />
        </div>
      </div>

      {/* Export Button & Dropdown */}
      <div style={{ position: 'relative', marginTop: '4px' }}>
        <button
          className="btn btn-primary"
          style={{ width: '100%', justifyContent: 'center', fontSize: '12px', padding: '6px 12px' }}
          onClick={() => setDropdownOpen(!dropdownOpen)}
        >
          📤 EXPORTER LE GRAPHE
        </button>

        {dropdownOpen && (
          <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-md)',
            marginTop: '4px',
            display: 'flex',
            flexDirection: 'column',
            zIndex: 100
          }}>
            <button
              onClick={() => triggerExport('gexf')}
              style={{ background: 'none', border: 'none', color: '#fff', padding: '8px', textAlign: 'left', cursor: 'pointer', fontSize: '11px', fontFamily: 'var(--font-mono)' }}
            >
              GEXF (Gephi)
            </button>
            <button
              onClick={() => triggerExport('graphml')}
              style={{ background: 'none', border: 'none', color: '#fff', padding: '8px', textAlign: 'left', cursor: 'pointer', fontSize: '11px', fontFamily: 'var(--font-mono)' }}
            >
              GraphML (Maltego)
            </button>
            <button
              onClick={() => triggerExport('stix')}
              style={{ background: 'none', border: 'none', color: '#fff', padding: '8px', textAlign: 'left', cursor: 'pointer', fontSize: '11px', fontFamily: 'var(--font-mono)' }}
            >
              STIX 2.1 JSON (CTI)
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
export default GraphControls;
