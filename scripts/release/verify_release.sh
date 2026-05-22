#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# Vérification Client des Releases
# ==============================================================================

set -euo pipefail

echo "[*] ARGUS-INT Verification Tool"

if [ ! -f "SHA256SUMS" ] || [ ! -f "SHA256SUMS.asc" ]; then
    echo "[-] ERREUR: Fichiers SHA256SUMS ou SHA256SUMS.asc manquants."
    exit 1
fi

echo "1. Vérification de la signature GPG..."
if gpg --verify "SHA256SUMS.asc" "SHA256SUMS" 2>/dev/null; then
    echo "  ✅ Signature GPG VALIDE."
else
    echo "  ❌ Signature GPG INVALIDE."
    exit 1
fi

echo "2. Vérification de l'ancrage Blockchain (OpenTimestamps)..."
if command -v ots >/dev/null; then
    if ots verify "SHA256SUMS.asc.ots" >/dev/null 2>&1; then
        echo "  ✅ Timestamp Blockchain VALIDE."
    else
        echo "  ❌ Timestamp Blockchain INVALIDE."
    fi
else
    echo "  ⚠️ 'ots' non installé, vérification blockchain ignorée."
fi

echo "3. Vérification des Checksums SHA-256..."
if sha256sum --check "SHA256SUMS" --quiet; then
    echo "  ✅ Checksums SHA-256 VALIDES."
else
    echo "  ❌ Checksums SHA-256 INVALIDES."
    exit 1
fi

echo "✅ TOUTES LES VÉRIFICATIONS SONT RÉUSSIES. LE FICHIER EST INTÈGRE."
