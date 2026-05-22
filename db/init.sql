-- PHYNX — Schéma PostgreSQL
-- db/init.sql

-- Extension pour UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────────────────
--  INVESTIGATIONS
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS investigations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target              TEXT NOT NULL,          -- Chiffré AES-256-GCM
    target_type         VARCHAR(50) NOT NULL,   -- email, username, domain, ip, phone
    depth               INTEGER DEFAULT 1,
    status              VARCHAR(20) DEFAULT 'PENDING',
    -- PENDING | COLLECTING | CORRELATING | COMPLETED | FAILED
    result_count        INTEGER DEFAULT 0,
    pivot_suggestions   TEXT,
    llm_summary         TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    created_by          UUID,

    CONSTRAINT status_check CHECK (
        status IN ('PENDING', 'COLLECTING', 'CORRELATING', 'COMPLETED', 'FAILED')
    )
);

CREATE INDEX idx_investigations_status ON investigations(status);
CREATE INDEX idx_investigations_created_at ON investigations(created_at DESC);

-- ─────────────────────────────────────────────────────────
--  RÉSULTATS BRUTS (archive des collectes)
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_results (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id    UUID REFERENCES investigations(id) ON DELETE CASCADE,
    module              VARCHAR(100) NOT NULL,  -- identity, breach, darkweb, geoint...
    source              VARCHAR(200),           -- Nom de la plateforme/service
    data                JSONB NOT NULL,         -- Résultats bruts (chiffrés si sensibles)
    confidence          FLOAT DEFAULT 0.5,
    sha256_hash         CHAR(64),               -- Hash du contenu pour intégrité
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_raw_results_investigation ON raw_results(investigation_id);
CREATE INDEX idx_raw_results_module ON raw_results(module);
CREATE INDEX idx_raw_results_data ON raw_results USING GIN(data);

-- ─────────────────────────────────────────────────────────
--  ARCHIVES (ArchiveBox + hachage)
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS archives (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id    UUID REFERENCES investigations(id) ON DELETE SET NULL,
    original_url        TEXT NOT NULL,
    archive_url         TEXT,
    sha256_hash         CHAR(64) NOT NULL,
    file_size_bytes     BIGINT,
    captured_at         TIMESTAMPTZ DEFAULT NOW(),
    diff_from_previous  TEXT                    -- Diff si URL déjà archivée
);

-- ─────────────────────────────────────────────────────────
--  RAPPORTS GÉNÉRÉS
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reports (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id    UUID REFERENCES investigations(id) ON DELETE CASCADE,
    format              VARCHAR(20) DEFAULT 'JSON',  -- JSON, PDF, HTML
    file_path           TEXT,                         -- Chemin chiffré local
    sha256_hash         CHAR(64),
    generated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────
--  MODULES DISPONIBLES (registre des plugins)
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS modules (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(100) UNIQUE NOT NULL,
    version             VARCHAR(20),
    enabled             BOOLEAN DEFAULT TRUE,
    target_types        TEXT[],                 -- Types de cibles supportés
    queue               VARCHAR(50),            -- Queue Celery associée
    config              JSONB DEFAULT '{}'
);

-- Seed des modules par défaut
INSERT INTO modules (name, version, enabled, target_types, queue) VALUES
    ('identity',    '1.0.0', TRUE, ARRAY['email','username','phone'], 'identity'),
    ('breach',      '1.0.0', TRUE, ARRAY['email','username','domain'], 'breach'),
    ('darkweb',     '1.0.0', TRUE, ARRAY['email','username','domain','ip'], 'darkweb'),
    ('geoint',      '1.0.0', TRUE, ARRAY['image','location'], 'geoint'),
    ('techrecon',   '1.0.0', TRUE, ARRAY['domain','ip'], 'techrecon'),
    ('crypto',      '1.0.0', TRUE, ARRAY['wallet','address'], 'techrecon')
ON CONFLICT (name) DO NOTHING;
