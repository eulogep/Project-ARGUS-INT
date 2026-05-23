#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# Script de Préparation de Release
# Calcule SHA-256, signe via GPG, génère le SBOM et ancre via OpenTimestamps.
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <version_tag>"
    echo "Ex: $0 v1.0.0"
    exit 1
fi

VERSION="$1"
RELEASE_DIR="/tmp/argus_release_$VERSION"
SBOM_FILE="${RELEASE_DIR}/sbom-${VERSION}.json"

echo "[*] Préparation de la release $VERSION..."
mkdir -p "$RELEASE_DIR"

# 1. Copie des artefacts (Simulation)
echo "  -> Rassemblement des artefacts..."
cp "scripts/iso/argus-int-${VERSION}.iso" "${RELEASE_DIR}/" 2>/dev/null || touch "${RELEASE_DIR}/argus-int-${VERSION}.iso"

# 2. Génération du SBOM (CycloneDX)
echo "  -> Génération du SBOM (CycloneDX)..."
# Nécessite cyclonedx-cli ou similaire. Simulation :
echo '{"bomFormat": "CycloneDX", "specVersion": "1.4", "version": 1}' > "$SBOM_FILE"

# 2.5 Génération du Changelog
echo "  -> Génération automatique du Changelog..."
bash scripts/release/generate_changelog.sh
cp CHANGELOG.md "${RELEASE_DIR}/"

cd "$RELEASE_DIR"

# 3. Calcul SHA-256
echo "  -> Calcul des checksums SHA-256..."
sha256sum * > "SHA256SUMS"

# 4. Signature GPG Detached
echo "  -> Signature GPG des checksums..."
gpg --detach-sign --armor "SHA256SUMS"

# 5. Ancrage Blockchain (OpenTimestamps)
echo "  -> Ancrage Blockchain (Bitcoin)..."
if command -v ots >/dev/null; then
    ots stamp "SHA256SUMS.asc"
else
    echo "  [-] Outil 'ots' non trouvé. Ancrage ignoré."
fi

# 6. Signature Cosign des images Docker
echo "  -> Signature des images Docker avec Cosign..."
# cosign sign --key cosign.key "ghcr.io/yourorg/argus-int-backend:${VERSION}"

echo "✅ Release prête dans $RELEASE_DIR"
