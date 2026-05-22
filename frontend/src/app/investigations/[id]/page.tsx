// ==============================================================================
// Project ARGUS-INT - Investigation Detail View
// ==============================================================================

'use client';

import React, { use, useEffect, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useAppStore } from '@/lib/store';
import { api } from '@/lib/api';
import { NodeInspector } from '@/components/graph/NodeInspector';
import { GraphControls } from '@/components/graph/GraphControls';

const HybridGraph = dynamic(() => import('@/components/graph/HybridGraph').then(mod => mod.HybridGraph), { ssr: false });

interface Params {
  id: string;
}

export default function InvestigationDetailPage({ params }: { params: Promise<Params> }) {
  const resolvedParams = use(params);
  const { investigations } = useAppStore();
  const [localNodes, setLocalNodes] = useState<any[]>([]);
  const [localEdges, setLocalEdges] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const inv = investigations.find((i) => i.id === resolvedParams.id);

  useEffect(() => {
    setLoading(true);
    api.getGraph(resolvedParams.id)
      .then((res) => {
        // Filter elements associated to this mock investigation
        setLocalNodes(res.nodes);
        setLocalEdges(res.edges);
      })
      .finally(() => setLoading(false));
  }, [resolvedParams.id]);

  if (!inv) {
    return (
      <div className="animate-in" style={{ padding: 'var(--space-xl)', textAlign: 'center' }}>
        <h3>Investigation {resolvedParams.id} introuvable</h3>
        <Link href="/investigations" className="btn" style={{ marginTop: 'var(--space-md)' }}>
          Retour aux investigations
        </Link>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr', height: '100%', gap: 'var(--space-md)' }} className="animate-in">
      
      {/* Detail Header */}
      <div className="card" style={{ padding: 'var(--space-md) var(--space-lg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>CIBLE: {inv.target_type.toUpperCase()}</div>
            <h2 className="mono" style={{ fontSize: '18px', fontWeight: 700, color: 'var(--accent-primary)' }}>{inv.target}</h2>
          </div>
          <span className={`badge ${
            inv.status === 'DONE' ? 'badge-success' :
            inv.status === 'RUNNING' ? 'badge-info badge-pulse' :
            inv.status === 'PENDING' ? 'badge-warning' : 'badge-danger'
          }`}>
            <span className="badge-dot" /> {inv.status}
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 'var(--space-md)', minHeight: 0 }}>
        {/* Sidebar execution timeline */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
          <h3 className="card-title">Chronologie d'Exécution</h3>
          
          <div className="timeline">
            <div className="timeline-item">
              <div className="timeline-dot completed" />
              <div className="timeline-content">
                <h4>Normalisation & Typage</h4>
                <p>Cible détectée et préparée pour l'analyse.</p>
                <span className="timeline-time">14:32:00 UTC</span>
              </div>
            </div>

            <div className="timeline-item">
              <div className={`timeline-dot ${inv.status !== 'PENDING' ? 'completed' : 'active'}`} />
              <div className="timeline-content">
                <h4>Collecte des sources (Sherlock/Breach)</h4>
                <p>Interrogation des leaks et identités.</p>
                <span className="timeline-time">14:32:15 UTC</span>
              </div>
            </div>

            <div className="timeline-item">
              <div className={`timeline-dot ${inv.status === 'DONE' ? 'completed' : inv.status === 'RUNNING' ? 'active' : ''}`} />
              <div className="timeline-content">
                <h4>Corrélation de graphe</h4>
                <p>Génération topologique dans Neo4j.</p>
                <span className="timeline-time">14:33:00 UTC</span>
              </div>
            </div>

            <div className="timeline-item">
              <div className={`timeline-dot ${inv.status === 'DONE' ? 'completed' : ''}`} />
              <div className="timeline-content">
                <h4>Archivage & Preuve IPFS</h4>
                <p>Hashage et finalisation du rapport.</p>
                {inv.status === 'DONE' && <span className="timeline-time">14:38:22 UTC</span>}
              </div>
            </div>
          </div>
        </div>

        {/* Embedded Graphe View */}
        <div style={{ position: 'relative', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <span>Chargement du sous-graphe...</span>
            </div>
          ) : (
            <>
              <HybridGraph nodes={localNodes} edges={localEdges} />
              <GraphControls />
              <NodeInspector />
            </>
          )}
        </div>
      </div>

    </div>
  );
}
