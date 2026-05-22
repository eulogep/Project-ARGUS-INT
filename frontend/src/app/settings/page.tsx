// ==============================================================================
// Project ARGUS-INT - Settings / OPSEC Configuration Page
// ==============================================================================

'use client';

import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';

export default function SettingsPage() {
  const [apiMode, setApiMode] = useState<'live' | 'mock'>('mock');
  const [torProxy, setTorProxy] = useState('socks5h://127.0.0.1:9050');
  const [ipfsGate, setIpfsGate] = useState('http://localhost:5001');

  useEffect(() => {
    setApiMode(api.isMockMode() ? 'mock' : 'live');
  }, []);

  const handleApiChange = (mode: 'live' | 'mock') => {
    api.setApiMode(mode);
    setApiMode(mode);
    // Reload to re-initialize client wrappers
    window.location.reload();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }} className="animate-in">
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Configuration Système & OPSEC</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
          Gérer la sécurité de transport, les enclaves IPFS et le couplage avec le backend FastAPI.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-lg)' }}>
        {/* Core Config */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          <h3 className="card-title">Paramètres Généraux</h3>
          
          <div>
            <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Mode de Connexion API
            </label>
            <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
              <button
                className={`btn ${apiMode === 'live' ? 'btn-primary' : ''}`}
                onClick={() => handleApiChange('live')}
                style={{ flex: 1, justifyContent: 'center' }}
              >
                📡 LIVE (FastAPI backend)
              </button>
              <button
                className={`btn ${apiMode === 'mock' ? 'btn-primary' : ''}`}
                onClick={() => handleApiChange('mock')}
                style={{ flex: 1, justifyContent: 'center' }}
              >
                💾 SIMULÉ (Offline/Mock)
              </button>
            </div>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'block', marginTop: '4px' }}>
              Basculez sur LIVE pour vous connecter au serveur FastAPI local (port 8000).
            </span>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Relais Proxy Tor
            </label>
            <input
              type="text"
              className="input mono"
              value={torProxy}
              onChange={(e) => setTorProxy(e.target.value)}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Passerelle d'ancrage IPFS
            </label>
            <input
              type="text"
              className="input mono"
              value={ipfsGate}
              onChange={(e) => setIpfsGate(e.target.value)}
            />
          </div>
        </div>

        {/* OPSEC Shield Guidelines */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          <h3 className="card-title">Directive d'Autoprotection</h3>
          <div style={{ background: 'rgba(0, 255, 65, 0.03)', border: '1px solid rgba(0, 255, 65, 0.1)', padding: 'var(--space-md)', borderRadius: 'var(--radius-lg)', fontSize: '12px' }}>
            <strong style={{ color: 'var(--accent-primary)', display: 'block', marginBottom: 'var(--space-xs)' }}>
              Raccourci Clavier COLD WIPE (Panic Mode)
            </strong>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-sm)' }}>
              En cas d'interception physique ou de tentative de piratage, appuyez <strong>3 fois rapidement sur la touche ECHAP (Escape)</strong>.
            </p>
            <ul style={{ listStyleType: 'square', paddingLeft: 'var(--space-md)', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <li>Efface instantanément l'IndexedDB locale (historique de graphes).</li>
              <li>Détruit les tokens de session dans le stockage volatile.</li>
              <li>Ferme les canaux WebSockets de monitoring.</li>
              <li>Redirige immédiatement la page vers un écran vide neutre.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
