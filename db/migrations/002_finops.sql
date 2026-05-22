-- PHYNX — Extension FinOps du schéma PostgreSQL
-- db/migrations/002_finops.sql
-- À appliquer après init.sql

-- ─────────────────────────────────────────────────────────
--  WALLETS DE L'OUTIL (clés chiffrées AES-256-GCM)
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS finops_wallets (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_type         VARCHAR(20) NOT NULL,   -- "monero" | "lightning" | "bitcoin"
    label               VARCHAR(200),
    address_enc         TEXT NOT NULL,           -- Adresse publique chiffrée
    -- Les clés privées NE SONT JAMAIS stockées en DB
    -- Elles résident uniquement dans les volumes chiffrés des containers
    balance_cache       NUMERIC(20, 8) DEFAULT 0,
    balance_unit        VARCHAR(10) DEFAULT 'XMR',
    last_balance_check  TIMESTAMPTZ,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────
--  DÉPENSES ANONYMES (dashboard FinOps)
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS finops_expenses (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id    UUID REFERENCES investigations(id) ON DELETE SET NULL,
    provider            VARCHAR(100) NOT NULL,   -- "dehashed", "intelx", "proxypool_1h"
    method              VARCHAR(20) NOT NULL,     -- "lightning" | "xmr"
    amount              NUMERIC(20, 8) NOT NULL,
    currency            VARCHAR(10) NOT NULL,     -- "sats" | "xmr"
    result_count        INTEGER DEFAULT 0,
    -- tx_hash chiffré — jamais en clair
    tx_hash_enc         TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_finops_expenses_investigation ON finops_expenses(investigation_id);
CREATE INDEX idx_finops_expenses_provider ON finops_expenses(provider);
CREATE INDEX idx_finops_expenses_created_at ON finops_expenses(created_at DESC);

-- ─────────────────────────────────────────────────────────
--  ADRESSES FURTIVES GÉNÉRÉES (Stealth Addresses)
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS finops_stealth_addresses (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_id           UUID REFERENCES finops_wallets(id),
    address_enc         TEXT NOT NULL,           -- Subaddress XMR chiffrée
    label               VARCHAR(200),
    used_for            VARCHAR(200),            -- Contexte d'utilisation
    received_amount     NUMERIC(20, 8) DEFAULT 0,
    is_used             BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────
--  TRANSACTIONS CRYPTO TRACÉES (OSINT)
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crypto_traces (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id    UUID REFERENCES investigations(id) ON DELETE CASCADE,
    chain               VARCHAR(20) NOT NULL,    -- "bitcoin" | "ethereum" | "monero"
    address             TEXT NOT NULL,
    risk_score          FLOAT DEFAULT 0.0,
    risk_flags          TEXT[],
    cluster_data        JSONB DEFAULT '{}',
    entity_matches      JSONB DEFAULT '[]',
    raw_tx_count        INTEGER DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_crypto_traces_investigation ON crypto_traces(investigation_id);
CREATE INDEX idx_crypto_traces_risk ON crypto_traces(risk_score DESC);
