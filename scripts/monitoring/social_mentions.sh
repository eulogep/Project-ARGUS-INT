#!/usr/bin/env bash
# ==============================================================================
# Veille OSINT sur les mentions du projet (Reddit)
# ==============================================================================
set -euo pipefail

echo "[*] Scanning Reddit (r/osint, r/netsec) for 'ARGUS-INT'..."

# Headers pour éviter le rate-limiting 429 de Reddit
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

for SUBREDDIT in "osint" "netsec" "cybersecurity"; do
    echo "  -> Checking r/$SUBREDDIT..."
    # Utilisation du endpoint JSON natif de Reddit
    DATA=$(curl -s -A "$USER_AGENT" "https://www.reddit.com/r/${SUBREDDIT}/search.json?q=ARGUS-INT&restrict_sr=1" || true)
    
    if echo "$DATA" | jq -e '.data.children | length > 0' >/dev/null 2>&1; then
        echo "$DATA" | jq -r '.data.children[] | "- [\(.data.author)] \(.data.title) (Score: \(.data.score)) -> \(.data.url)"'
    else
        echo "     (Aucune mention récente)"
    fi
    sleep 2 # Respect rate limit
done

echo "✅ Scan terminé."
