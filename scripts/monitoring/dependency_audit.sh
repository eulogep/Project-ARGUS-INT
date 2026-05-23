#!/usr/bin/env bash
# ==============================================================================
# Audit des dépendances et alertes Signal
# ==============================================================================
set -euo pipefail

# Endpoint webhook de votre bot Signal (Optionnel)
SIGNAL_WEBHOOK="${SIGNAL_WEBHOOK_URL:-}"

echo "[*] Démarrage de l'audit des dépendances..."
ALERTS=0
REPORT="/tmp/dep_audit_report.txt"
> "$REPORT"

# 1. Audit Python
if command -v pip-audit >/dev/null; then
    echo "  -> pip-audit (backend)..."
    if ! pip-audit -r backend/requirements.txt >> "$REPORT" 2>&1; then
        ALERTS=$((ALERTS + 1))
        echo "⚠️ Vulnérabilités Python détectées."
    fi
fi

# 2. Audit Node (Frontend)
if command -v npm >/dev/null && [ -d "frontend" ]; then
    echo "  -> npm audit (frontend)..."
    if ! (cd frontend && npm audit --audit-level=high >> "$REPORT" 2>&1); then
        ALERTS=$((ALERTS + 1))
        echo "⚠️ Vulnérabilités Node détectées."
    fi
fi

# 3. Notification Webhook Signal si critique
if [ "$ALERTS" -gt 0 ]; then
    echo "❌ $ALERTS analyses ont échoué. Examen requis."
    if [ -n "$SIGNAL_WEBHOOK" ]; then
        curl -X POST -H "Content-Type: application/json" -d '{"message": "⚠️ ARGUS-INT: Vulnérabilités détectées lors de l audit quotidien. Voir les logs CI."}' "$SIGNAL_WEBHOOK" || true
    fi
else
    echo "✅ Aucune vulnérabilité haute/critique détectée."
fi
