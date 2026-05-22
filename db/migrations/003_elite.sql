-- PHYNX — Extension State-Sponsor / Red Teaming du schéma PostgreSQL
-- db/migrations/003_elite.sql
-- À appliquer après 002_finops.sql

-- ─────────────────────────────────────────────────────────
--  RED TEAMING & CRITIQUE COGNITIVE
-- ─────────────────────────────────────────────────────────
ALTER TABLE investigations ADD COLUMN IF NOT EXISTS red_team_critique TEXT;

-- ─────────────────────────────────────────────────────────
--  PROFIL TEMPOREL ET CHRONOBIOLOGIQUE
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chronobiology_profiles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_uid          VARCHAR(200) UNIQUE NOT NULL,
    active_hours        INTEGER[],
    active_days         VARCHAR(20)[],
    estimated_timezone  VARCHAR(50),
    sleep_window_start  INTEGER,
    sleep_window_end    INTEGER,
    work_pattern        VARCHAR(50),
    confidence          FLOAT DEFAULT 0.0,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chrono_entity ON chronobiology_profiles(entity_uid);
