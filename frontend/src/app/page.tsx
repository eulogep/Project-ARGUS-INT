// ==============================================================================
// Project ARGUS-INT - Dashboard Page
// ==============================================================================

'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { useAppStore } from '@/lib/store';
import { mockNodes, mockEdges, mockInvestigations, mockWorkers } from '@/lib/mock-data';

export default function Dashboard() {
  const {
    nodes,
    edges,
    investigations,
    workers,
    setGraph,
    setInvestigations,
    setWorkers
  } = useAppStore();

  // Populate store with initial mock data if empty
  useEffect(() => {
    if (nodes.length === 0) setGraph(mockNodes, mockEdges);
    if (investigations.length === 0) setInvestigations(mockInvestigations);
    if (workers.length === 0) setWorkers(mockWorkers);
  }, [nodes, investigations, workers, setGraph, setInvestigations, setWorkers]);

  const activeInvestigations = investigations.filter((i) => i.status === 'RUNNING' || i.status === 'PENDING').length;
  const onlineWorkers = workers.filter((w) => w.status !== 'offline').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }} className="animate-in">
      
      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card" data-accent="green">
          <div className="stat-value">{activeInvestigations}</div>
          <div className="stat-label">Investigations Actives</div>
        </div>
        <div className="stat-card" data-accent="cyan">
          <div className="stat-value">{nodes.length}</div>
          <div className="stat-label">Entités dans le Graphe</div>
        </div>
        <div className="stat-card" data-accent="purple">
          <div className="stat-value">{edges.length}</div>
          <div className="stat-label">Corrélations Trouvées</div>
        </div>
        <div className="stat-card" data-accent="orange">
          <div className="stat-value">{onlineWorkers} / {workers.length}</div>
          <div className="stat-label">Workers en ligne</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 'var(--space-lg)' }}>
        {/* Left Side: Recent Investigations */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', minHeight: '320px' }}>
          <div className="card-header">
            <h3 className="card-title">Investigations Récentes</h3>
            <Link href="/investigations" className="btn" style={{ fontSize: '11px', padding: '4px 8px' }}>
              Voir Tout
            </Link>
          </div>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Cible</th>
                  <th>Type</th>
                  <th>Statut</th>
                  <th>Résultats</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {investigations.slice(0, 5).map((inv) => (
                  <tr key={inv.id}>
                    <td className="mono" style={{ fontWeight: 600 }}>
                      <Link href={`/investigations/${inv.id}`}>{inv.target}</Link>
                    </td>
                    <td className="mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                      {inv.target_type}
                    </td>
                    <td>
                      <span className={`badge ${
                        inv.status === 'DONE' ? 'badge-success' :
                        inv.status === 'RUNNING' ? 'badge-info badge-pulse' :
                        inv.status === 'PENDING' ? 'badge-warning' : 'badge-danger'
                      }`}>
                        <span className="badge-dot" /> {inv.status}
                      </span>
                    </td>
                    <td className="mono">{inv.result_count}</td>
                    <td className="mono" style={{ color: 'var(--text-muted)' }}>
                      {new Date(inv.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Side: Workers status */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          <div className="card-header">
            <h3 className="card-title">Flux de Fusion Celery</h3>
          </div>
          <div className="worker-grid" style={{ gridTemplateColumns: '1fr' }}>
            {workers.map((worker) => (
              <div key={worker.name} className="worker-card">
                <span className={`worker-indicator ${worker.status === 'online' ? 'online' : worker.status === 'busy' ? 'online badge-pulse' : 'offline'}`} />
                <div style={{ flex: 1 }}>
                  <div className="worker-name">{worker.name}</div>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                    Queue: {worker.queue} | Success: {worker.tasks_completed}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

    </div>
  );
}
