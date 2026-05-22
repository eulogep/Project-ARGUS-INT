// ==============================================================================
// Project ARGUS-INT - FinOps Clandestine Wallet & Operations Dashboard
// ==============================================================================

'use client';

import React from 'react';

export default function FinOpsPage() {
  const transactions = [
    { id: 'tx-001', target: 'Tor Proxy Node-01', asset: 'XMR', amount: '0.142', status: 'CONFIRMED', date: '2026-05-21 18:42:01' },
    { id: 'tx-002', target: 'Breached DB API Access', asset: 'LN (BTC)', amount: '0.000150', status: 'CONFIRMED', date: '2026-05-20 09:12:45' },
    { id: 'tx-003', target: 'Darknet Forum Intel Scraper', asset: 'XMR', amount: '0.089', status: 'CONFIRMED', date: '2026-05-19 22:15:30' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }} className="animate-in">
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: 700 }}>FinOps & Financement</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
          Suivi des coûts d'infrastructure clandestine via les réseaux décentralisés (Monero & Lightning Network).
        </p>
      </div>

      {/* Crypto Wallets status */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--space-md)' }}>
        {/* Monero wallet */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h4 style={{ fontWeight: 700 }}>Portefeuille Monero (XMR)</h4>
            <span className="badge badge-success badge-pulse">
              <span className="badge-dot" /> SYNCHRONISÉ
            </span>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>SOLDE DISPONIBLE</div>
            <div className="mono" style={{ fontSize: '24px', fontWeight: 700, color: 'var(--accent-primary)' }}>12.4820 XMR</div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>~ 2,142.30 USD</div>
          </div>
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-sm)' }}>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>ADRESSE DE DEPOT TOR (.onion)</span>
            <div className="mono" style={{ fontSize: '10px', overflowWrap: 'break-word', color: 'var(--text-primary)', background: 'var(--bg-elevated)', padding: '6px', borderRadius: '4px', marginTop: '2px' }}>
              47tKBx8eZ...8zGkQ9Wz...W9h8jP
            </div>
          </div>
        </div>

        {/* LND wallet */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h4 style={{ fontWeight: 700 }}>Lightning Network (LND)</h4>
            <span className="badge badge-success badge-pulse">
              <span className="badge-dot" /> CANAL OUVERT
            </span>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>SOLDE DU CANAL</div>
            <div className="mono" style={{ fontSize: '24px', fontWeight: 700, color: 'var(--accent-secondary)' }}>1,480,200 SAT</div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>~ 932.50 USD</div>
          </div>
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-sm)' }}>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>INFO PEER NODE</span>
            <div className="mono" style={{ fontSize: '10px', overflowWrap: 'break-word', color: 'var(--text-primary)', background: 'var(--bg-elevated)', padding: '6px', borderRadius: '4px', marginTop: '2px' }}>
              03f7e52a8c...90e1@argus-ln-exit.onion:9735
            </div>
          </div>
        </div>
      </div>

      {/* Transaction Log */}
      <div className="card">
        <h3 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>Derniers Paiements de Services</h3>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Identifiant</th>
                <th>Destination</th>
                <th>Actif</th>
                <th>Montant</th>
                <th>Statut</th>
                <th>Horodatage</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <tr key={tx.id}>
                  <td className="mono" style={{ color: 'var(--text-muted)' }}>{tx.id}</td>
                  <td style={{ fontWeight: 600 }}>{tx.target}</td>
                  <td className="mono">{tx.asset}</td>
                  <td className="mono" style={{ color: 'var(--accent-primary)' }}>{tx.amount}</td>
                  <td>
                    <span className="badge badge-success">
                      <span className="badge-dot" /> {tx.status}
                    </span>
                  </td>
                  <td className="mono" style={{ color: 'var(--text-muted)' }}>{tx.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
