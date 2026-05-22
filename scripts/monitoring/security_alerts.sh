#!/usr/bin/env bash
# ==============================================================================
# Monitoring des alertes de sécurité (Dépendances)
# ==============================================================================
set -euo pipefail

echo "[*] Exécution de Dependabot / Trivy (Local Scan)..."

# Analyse du backend Python
echo "  -> Analyse pip-audit (backend)..."
if command -v pip-audit >/dev/null; then
    (cd ../../backend && pip-audit -r requirements.txt) || echo "Vulnérabilités trouvées dans requirements.txt"
else
    echo "  [-] pip-audit non installé."
fi

# Analyse Docker
echo "  -> Analyse Trivy (Images Docker)..."
if command -v trivy >/dev/null; then
    trivy image --severity HIGH,CRITICAL argus-int-backend:latest || true
else
    echo "  [-] Trivy non installé."
fi

echo "✅ Audit de sécurité terminé."
