// ==============================================================================
// Project ARGUS-INT - Footer Component
// ==============================================================================

'use client';

import React, { useEffect, useState } from 'react';
import { useAppStore } from '@/lib/store';

export function Footer() {
  const { nodes, edges } = useAppStore();
  const [time, setTime] = useState<string>('');

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setTime(now.toISOString().replace('T', ' ').substr(0, 19) + ' UTC');
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <footer style={{
      height: '32px',
      background: 'var(--bg-surface)',
      borderTop: '1px solid var(--border-subtle)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 var(--space-lg)',
      fontSize: '11px',
      color: 'var(--text-secondary)',
      fontFamily: 'var(--font-mono)',
      zIndex: 50,
      flexShrink: 0
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
        <span>SYS: ONLINE</span>
        <span style={{ color: 'var(--border-strong)' }}>|</span>
        <span>NODES: {nodes.length}</span>
        <span>EDGES: {edges.length}</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
        <span>OPSEC THREAT LEVEL: MINIMAL</span>
        <span style={{ color: 'var(--border-strong)' }}>|</span>
        <span>{time}</span>
      </div>
    </footer>
  );
}
export default Footer;
