#!/usr/bin/env bash
# ==============================================================================
# Script de tracking basique des métriques GitHub
# ==============================================================================
set -euo pipefail

REPO="yourorg/argus-int"

echo "=== MÉTRIQUES GITHUB: $REPO ==="
if [ -n "${GITHUB_TOKEN:-}" ]; then
    AUTH="-H \"Authorization: token $GITHUB_TOKEN\""
else
    AUTH=""
fi

DATA=$(curl -s $AUTH "https://api.github.com/repos/$REPO")

STARS=$(echo "$DATA" | grep '"stargazers_count":' | grep -o '[0-9]*')
FORKS=$(echo "$DATA" | grep '"forks_count":' | grep -o '[0-9]*')
ISSUES=$(echo "$DATA" | grep '"open_issues_count":' | grep -o '[0-9]*')

echo "Stars: $STARS"
echo "Forks: $FORKS"
echo "Open Issues: $ISSUES"

echo "==============================="
