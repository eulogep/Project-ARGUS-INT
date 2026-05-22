-- ==============================================================================
-- Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
-- Migration 003 : Phase 5 — Cognitive Engine Tables
-- ==============================================================================

-- Table d'état persisté des agents (snapshot de la State Machine)
CREATE TABLE IF NOT EXISTS agent_states (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id        VARCHAR(100) NOT NULL UNIQUE,
    agent_role      VARCHAR(50)  NOT NULL,
    investigation_id UUID REFERENCES investigations(id) ON DELETE CASCADE,
    current_state   VARCHAR(30)  NOT NULL DEFAULT 'IDLE',
    previous_state  VARCHAR(30),
    transition_count INTEGER DEFAULT 0,
    error_message   TEXT,
    context         JSONB DEFAULT '{}',
    state_entered_at TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_state CHECK (
        current_state IN ('IDLE','PLANNING','COLLECTING','ANALYZING','WAITING_HUMAN','REPORTING','COMPLETED','ERROR')
    )
);

CREATE INDEX IF NOT EXISTS idx_agent_states_investigation ON agent_states(investigation_id);
CREATE INDEX IF NOT EXISTS idx_agent_states_role ON agent_states(agent_role);

-- Journal épisodique des actions/décisions des agents
CREATE TABLE IF NOT EXISTS agent_memory (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id        VARCHAR(100) NOT NULL,
    investigation_id UUID REFERENCES investigations(id) ON DELETE CASCADE,
    action          VARCHAR(200) NOT NULL,
    state_from      VARCHAR(30),
    state_to        VARCHAR(30),
    payload         JSONB DEFAULT '{}',
    result          TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_memory_agent ON agent_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_memory_investigation ON agent_memory(investigation_id);
CREATE INDEX IF NOT EXISTS idx_agent_memory_created ON agent_memory(created_at DESC);

-- Événements de sécurité AI Firewall
CREATE TABLE IF NOT EXISTS ai_security_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id UUID REFERENCES investigations(id) ON DELETE SET NULL,
    source          VARCHAR(200),
    score           INTEGER NOT NULL,
    triggered_layer INTEGER NOT NULL,
    reasons         JSONB DEFAULT '[]',
    text_snippet    TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_security_events_score ON ai_security_events(score DESC);
CREATE INDEX IF NOT EXISTS idx_ai_security_events_created ON ai_security_events(created_at DESC);

-- Messages HUMINT en attente d'approbation humaine
CREATE TABLE IF NOT EXISTS humint_approvals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id        VARCHAR(100) NOT NULL,
    investigation_id UUID REFERENCES investigations(id) ON DELETE CASCADE,
    persona_name    VARCHAR(200),
    target_platform VARCHAR(100),
    target_context  TEXT,
    generated_message TEXT NOT NULL,
    style_score     FLOAT,
    status          VARCHAR(20) DEFAULT 'PENDING',
    approved_by     VARCHAR(200),
    approved_at     TIMESTAMPTZ,
    rejection_reason TEXT,
    sent_via_proxy  BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_humint_status CHECK (
        status IN ('PENDING','APPROVED','REJECTED','SENT','FAILED')
    )
);

CREATE INDEX IF NOT EXISTS idx_humint_approvals_status ON humint_approvals(status);
CREATE INDEX IF NOT EXISTS idx_humint_approvals_investigation ON humint_approvals(investigation_id);

-- Trigger de mise à jour de updated_at pour agent_states
CREATE OR REPLACE FUNCTION update_agent_states_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_agent_states_updated ON agent_states;
CREATE TRIGGER trigger_agent_states_updated
    BEFORE UPDATE ON agent_states
    FOR EACH ROW EXECUTE FUNCTION update_agent_states_updated_at();
