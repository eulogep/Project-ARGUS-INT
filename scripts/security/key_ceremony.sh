#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# Cérémonie de création des clés GPG pour les Opérations ARGUS-INT
# Documenté dans docs/KEY_CEREMONY.md
# ==============================================================================

set -euo pipefail

echo "[!!!] ARGUS-INT KEY CEREMONY [!!!]"
echo "Ce script générera une clé GPG RSA 4096 sécurisée."
echo "Il DOIT être exécuté sur un Live USB amnésique (ex: Tails)."
echo "--------------------------------------------------------"

read -p "Avez-vous déconnecté cette machine d'Internet ? (y/N) " offline
if [ "$offline" != "y" ]; then
    echo "Annulation. Veuillez vous déconnecter d'Internet."
    exit 1
fi

read -p "Entrez le nom de l'Opérateur (ex: ARGUS-INT Master Key): " key_name
read -p "Entrez l'email (ex: admin@argus.local): " key_email

cat > /tmp/gpg-gen.conf <<EOF
%echo Generating ARGUS-INT Master Key...
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: $key_name
Name-Email: $key_email
Expire-Date: 1y
%commit
%echo Done
EOF

echo "[*] Génération de la clé GPG (une fenêtre demandera la passphrase)..."
gpg --batch --generate-key /tmp/gpg-gen.conf

KEY_ID=$(gpg --list-keys --with-colons "$key_email" | awk -F: '/^pub:/ { print $5 }')

echo "[*] Clé générée: $KEY_ID"

echo "[*] Export de la clé publique..."
gpg --armor --export "$KEY_ID" > /tmp/argus_pubkey.asc

echo "[*] Export de la clé privée (POUR STOCKAGE HORS-LIGNE SECURISE)..."
gpg --armor --export-secret-keys "$KEY_ID" > /tmp/argus_privkey.asc

echo "[*] Génération d'une Paper Key (nécessite paperkey)..."
if command -v paperkey >/dev/null; then
    gpg --export-secret-key "$KEY_ID" | paperkey --output /tmp/argus_paperkey.txt
    echo "  -> Paper Key générée dans /tmp/argus_paperkey.txt"
    echo "  -> À IMPRIMER IMMÉDIATEMENT."
else
    echo "  [-] Outil 'paperkey' introuvable. Skip."
fi

echo "✅ Cérémonie terminée. Sauvegardez les clés sur 2 clés USB chiffrées distinctes, puis éteignez cette machine."
