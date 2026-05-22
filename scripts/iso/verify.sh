#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# Vérification de l'intégrité de l'ISO (SHA-256 + GPG Signature)
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <iso_file> <sha256_file>"
    echo "Example: $0 argus-int-v0.5.0.iso argus-int-v0.5.0.iso.sha256"
    exit 1
fi

ISO_FILE="$1"
SHA_FILE="$2"
SIG_FILE="${SHA_FILE}.asc"

if [ ! -f "$ISO_FILE" ]; then
    echo "[-] Fichier ISO introuvable: $ISO_FILE"
    exit 1
fi

if [ ! -f "$SHA_FILE" ]; then
    echo "[-] Fichier de somme de contrôle introuvable: $SHA_FILE"
    exit 1
fi

if [ ! -f "$SIG_FILE" ]; then
    echo "[-] Fichier de signature GPG introuvable: $SIG_FILE"
    exit 1
fi

echo "[*] 1. Vérification de la signature GPG du fichier de somme de contrôle..."
if gpg --verify "$SIG_FILE" "$SHA_FILE" 2>/dev/null; then
    echo "  [+] Signature GPG valide."
else
    echo "  [-] ERREUR: Signature GPG invalide ! L'ISO peut être compromise."
    exit 1
fi

echo "[*] 2. Vérification de la somme de contrôle SHA-256 de l'ISO..."
EXPECTED_SHA=$(awk '{print $1}' "$SHA_FILE")
ACTUAL_SHA=$(sha256sum "$ISO_FILE" | awk '{print $1}')

if [ "$EXPECTED_SHA" == "$ACTUAL_SHA" ]; then
    echo "  [+] Somme de contrôle SHA-256 valide."
else
    echo "  [-] ERREUR: La somme de contrôle de l'ISO ne correspond pas !"
    echo "      Attendu : $EXPECTED_SHA"
    echo "      Actuel  : $ACTUAL_SHA"
    exit 1
fi

echo "✅ L'image ISO est intègre et authentique. Vous pouvez la flasher sur USB."
