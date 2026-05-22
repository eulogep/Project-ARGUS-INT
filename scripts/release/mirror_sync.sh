#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# Synchronisation de la release vers les miroirs (IPFS, etc.)
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <release_dir>"
    exit 1
fi

RELEASE_DIR="$1"

echo "[*] Synchronisation vers les miroirs officiels..."

if command -v ipfs >/dev/null; then
    echo "  -> Publication sur IPFS..."
    CID=$(ipfs add -r -q "$RELEASE_DIR" | tail -n 1)
    echo "  ✅ Pinned on IPFS: ipfs://$CID"
    
    # Update IPNS (optionnel)
    # ipfs name publish "$CID"
else
    echo "  [-] IPFS daemon introuvable."
fi

echo "  -> Création d'un torrent (transmission-cli requis)..."
if command -v transmission-create >/dev/null; then
    transmission-create -o "${RELEASE_DIR}.torrent" -t udp://tracker.opentrackr.org:1337 "$RELEASE_DIR"
    echo "  ✅ Torrent généré."
fi

echo "[*] Sync terminée."
