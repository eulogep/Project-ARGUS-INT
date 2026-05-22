// ==============================================================================
// Project ARGUS-INT - Modules & Workers Status Dashboard
// ==============================================================================

'use client';

import React, { useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { api } from '@/lib/api';

export default function ModulesPage() {
  const { workers, setWorkers } = useAppStore();

  useEffect(() => {
    api.getWorkers().then((res) => setWorkers(res));
  }, [setWorkers]);

  const modules = [
    { name: 'Identity Resolver', desc: 'Détection de profils sur 1000+ plateformes via Sherlock/Holehe.', status: 'Active', queue: 'identity' },
    { name: 'Breach Analyzer', desc: 'Indexation de dumps et bases de données de fuite de mots de passe.', status: 'Active', queue: 'breach' },
    { name: 'Dark Web Scraper', desc: 'Crawlers Tor/I2P asynchrones avec rotation de circuits.', status: 'Active', queue: 'darkweb' },
    { name: 'Astro-GEOINT', desc: 'Calcul de coordonnées, ombres solaires et reconnaissance faciale.', status: 'Active', queue: 'geoint' },
    { name: 'Technical Recon', desc: 'Découverte de sous-domaines, ports et configurations DNS.', status: 'Active', queue: 'techrecon' },
    { name: 'Crypto & FinOps', desc: 'Tracer on-chain Bitcoin/Ethereum/Monero et règlements Lightning.', status: 'Active', queue: 'finops' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }} className="animate-in">
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Modules de Fusion OSINT</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
          Gérer les moteurs de collecte et observer la charge de traitement.
        </p>
      </div>

      {/* Grid of Collector Modules */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-md)' }}>
        {modules.map((m) => {
          const associatedWorker = workers.find((w) => w.queue === m.queue);
          const isOnline = associatedWorker && associatedWorker.status !== 'offline';

          return (
            <div key={m.name} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-sm)' }}>
                  <h4 style={{ fontWeight: 700, fontSize: '14px' }}>{m.name}</h4>
                  <span className={`badge ${isOnline ? 'badge-success' : 'badge-danger'}`}>
                    <span className="badge-dot" /> {isOnline ? 'ONLINE' : 'OFFLINE'}
                  </span>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: 'var(--space-md)' }}>
                  {m.desc}
                </p>
              </div>

              {associatedWorker && (
                <div style={{ background: 'var(--bg-elevated)', padding: 'var(--space-sm)', borderRadius: 'var(--radius-md)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                    <span>Queue</span>
                    <span>{m.queue}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                    <span>Tâches Traitées</span>
                    <span>{associatedWorker.tasks_completed}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Temps Moyen</span>
                    <span>{(associatedWorker.avg_time_ms / 1000).toFixed(2)}s</span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
