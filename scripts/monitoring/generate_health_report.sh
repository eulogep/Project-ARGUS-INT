#!/usr/bin/env bash
# ==============================================================================
# Génération du Rapport de Santé Communautaire
# ==============================================================================
set -euo pipefail

REPO="yourorg/argus-int"

echo "[*] Génération du rapport de santé..."

if ! command -v gh >/dev/null; then
    echo '{"error": "gh cli not found"}'
    exit 1
fi

OPEN_PRS=$(gh pr list -R "$REPO" --json number | jq 'length' || echo 0)
MERGED_PRS=$(gh pr list -R "$REPO" --state merged --limit 100 --json number | jq 'length' || echo 0)
OPEN_ISSUES=$(gh issue list -R "$REPO" --state open --json number | jq 'length' || echo 0)

cat <<EOF > community_health.json
{
  "timestamp": "$(date -Iseconds)",
  "repository": "$REPO",
  "metrics": {
    "open_pull_requests": $OPEN_PRS,
    "recently_merged_prs": $MERGED_PRS,
    "open_issues": $OPEN_ISSUES
  }
}
EOF

echo "✅ Rapport JSON généré dans community_health.json"
cat community_health.json
