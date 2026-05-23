#!/usr/bin/env bash
# ==============================================================================
# Agrégation des Issues GitHub (Monitoring)
# ==============================================================================
set -euo pipefail

REPO="yourorg/argus-int"
REPORT_FILE="/tmp/argus_issues_report.md"

echo "[*] Récupération des issues avec 'gh' CLI..."
if ! command -v gh >/dev/null; then
    echo "[-] L'outil 'gh' (GitHub CLI) n'est pas installé."
    exit 1
fi

echo "# ARGUS-INT Issues Report - $(date -I)" > "$REPORT_FILE"

echo "## 🐛 Bugs Critiques" >> "$REPORT_FILE"
gh issue list -R "$REPO" --label "bug" --label "critical" --state open --limit 10 | awk '{print "- ["$1"] "$3}' >> "$REPORT_FILE" || echo "- Aucun bug critique" >> "$REPORT_FILE"

echo -e "\n## 💡 Feature Requests" >> "$REPORT_FILE"
gh issue list -R "$REPO" --label "enhancement" --state open --limit 10 | awk '{print "- ["$1"] "$3}' >> "$REPORT_FILE" || echo "- Aucune demande" >> "$REPORT_FILE"

echo "✅ Rapport généré : $REPORT_FILE"
cat "$REPORT_FILE"
