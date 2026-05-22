// ==============================================================================
// Project ARGUS-INT - TopBar Component
// ==============================================================================

'use client';

import React from 'react';
import { useAppStore } from '@/lib/store';
import { api } from '@/lib/api';

const EyeIcon = () => (
  <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" width="20" height="20">
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const EyeSlashIcon = () => (
  <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" width="20" height="20">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
  </svg>
);

const TerminalIcon = () => (
  <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" width="20" height="20">
    <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
  </svg>
);

export function TopBar() {
  const {
    toggleSidebar,
    privacyBlur,
    togglePrivacyBlur,
    dataDensity,
    toggleDensity,
    effectsEnabled,
    toggleEffects,
    wipeAllData,
  } = useAppStore();

  const handlePanicClick = () => {
    if (confirm('🚨 COLD WIPE INITIATION. Effacer toutes les données de session et couper les accès ?')) {
      wipeAllData();
      window.location.replace('about:blank');
    }
  };

  const isMock = api.isMockMode();

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button className="btn-icon" onClick={toggleSidebar} title="Basculer la Sidebar">
          <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" width="20" height="20">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>
        <span className="topbar-title">OPERATIONAL INTERFACE</span>
        {isMock ? (
          <span className="badge badge-warning" style={{ fontSize: '10px' }}>
            <span className="badge-dot" /> SIMULÉ (MOCK)
          </span>
        ) : (
          <span className="badge badge-success badge-pulse" style={{ fontSize: '10px' }}>
            <span className="badge-dot" /> LIVE CONNECTION
          </span>
        )}
      </div>

      <div className="topbar-right">
        {/* Screen Shield / Privacy Blur */}
        <button
          className={`btn-icon ${privacyBlur ? 'active' : ''}`}
          onClick={togglePrivacyBlur}
          title={privacyBlur ? 'Désactiver le floutage' : 'Flouter les données sensibles (Lieu Public)'}
          style={{ color: privacyBlur ? 'var(--accent-warning)' : 'inherit' }}
        >
          {privacyBlur ? <EyeSlashIcon /> : <EyeIcon />}
        </button>

        {/* Data Density Toggle */}
        <button
          className="btn-icon"
          onClick={toggleDensity}
          title={`Densité : ${dataDensity === 'comfortable' ? 'Confortable' : 'Compacte'}`}
        >
          <TerminalIcon />
        </button>

        {/* Tactical Glitch Effects */}
        <button
          className={`btn-icon ${effectsEnabled ? 'active' : ''}`}
          onClick={toggleEffects}
          title={effectsEnabled ? 'Vue épurée' : 'Activer effets de balayage tactique'}
          style={{ color: effectsEnabled ? 'var(--accent-primary)' : 'inherit' }}
        >
          <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" width="20" height="20">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
          </svg>
        </button>

        <span style={{ borderLeft: '1px solid var(--border-subtle)', height: '20px', margin: '0 8px' }} />

        {/* Kill Switch */}
        <button
          className="btn btn-danger"
          onClick={handlePanicClick}
          style={{ padding: '4px 12px', fontSize: '12px' }}
          title="Cold wipe immédiat et fermeture de l'onglet"
        >
          ⚠️ COLD WIPE
        </button>
      </div>
    </header>
  );
}
export default TopBar;
