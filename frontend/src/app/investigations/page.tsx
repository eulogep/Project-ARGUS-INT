// ==============================================================================
// Project ARGUS-INT - Investigations Dashboard
// ==============================================================================

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAppStore } from '@/lib/store';
import { api } from '@/lib/api';

export default function InvestigationsPage() {
  const { investigations, addInvestigation } = useAppStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [target, setTarget] = useState('');
  const [targetType, setTargetType] = useState('email');
  const [depth, setDepth] = useState(2);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!target) return;
    setLoading(true);

    try {
      const newInv = await api.createInvestigation(target, targetType, depth);
      addInvestigation(newInv);
      setModalOpen(false);
      setTarget('');
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }} className="animate-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Investigations</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
            Lancer et superviser les tâches de scraping et de corrélation de cibles.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
          ⚡ NOUVELLE INVESTIGATION
        </button>
      </div>

      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Identifiant</th>
                <th>Cible</th>
                <th>Type</th>
                <th>Profondeur</th>
                <th>Statut</th>
                <th>Résultats</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {investigations.map((inv) => (
                <tr key={inv.id}>
                  <td className="mono" style={{ color: 'var(--text-muted)' }}>{inv.id}</td>
                  <td className="mono" style={{ fontWeight: 600 }}>{inv.target}</td>
                  <td className="mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{inv.target_type}</td>
                  <td className="mono">{inv.depth}</td>
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
                  <td>
                    <Link href={`/investigations/${inv.id}`} className="btn" style={{ padding: '4px 8px', fontSize: '11px' }}>
                      Inspecter
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {modalOpen && (
        <div className="modal-overlay">
          <div className="modal animate-in">
            <h2>Lancer une nouvelle investigation</h2>
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  Cible d'investigation
                </label>
                <input
                  type="text"
                  className="input mono"
                  placeholder="ex: target@proton.me, shadow_op, 185.220.101.42"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    Type de cible
                  </label>
                  <select
                    className="input"
                    value={targetType}
                    onChange={(e) => setTargetType(e.target.value)}
                  >
                    <option value="email">Email</option>
                    <option value="username">Pseudonyme</option>
                    <option value="ip">Adresse IP</option>
                    <option value="domain">Nom de Domaine</option>
                    <option value="wallet">Wallet Crypto</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    Profondeur (1-3)
                  </label>
                  <input
                    type="number"
                    className="input"
                    min="1"
                    max="3"
                    value={depth}
                    onChange={(e) => setDepth(Number(e.target.value))}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: 'var(--space-sm)', marginTop: 'var(--space-md)', justifyContent: 'flex-end' }}>
                <button type="button" className="btn" onClick={() => setModalOpen(false)} disabled={loading}>
                  Annuler
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? 'Lancement...' : 'DÉMARRER'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
