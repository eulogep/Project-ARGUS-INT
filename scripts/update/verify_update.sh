#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# Vérification Post-Update (Tests de non-régression)
# ==============================================================================

set -euo pipefail

echo "[*] Lancement des tests de validation post-update..."
FAILURES=0

check_endpoint() {
    local url=$1
    local name=$2
    if curl -f -s "$url" > /dev/null; then
        echo "  [PASS] $name est en ligne."
    else
        echo "  [FAIL] $name ne répond pas."
        FAILURES=$((FAILURES + 1))
    fi
}

check_endpoint "http://localhost:8000/health" "API FastAPI"
check_endpoint "http://localhost:3000/" "Frontend Next.js"
check_endpoint "http://localhost:7474/" "Console Neo4j"

# Vérification des workers Celery
CELERY_WORKERS=$(docker ps --filter "name=celery" --format "{{.Names}}")
if [ -z "$CELERY_WORKERS" ]; then
    echo "  [FAIL] Aucun worker Celery détecté."
    FAILURES=$((FAILURES + 1))
else
    echo "  [PASS] Workers Celery actifs : $(echo $CELERY_WORKERS | wc -w)"
fi

if [ "$FAILURES" -eq 0 ]; then
    echo "✅ SUCCESS: La mise à jour est opérationnelle."
    exit 0
else
    echo "❌ ERROR: $FAILURES services sont défaillants après la mise à jour."
    exit 1
fi
