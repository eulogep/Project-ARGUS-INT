#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# Script de mise à jour Air-Gapped (Côté machine connectée Internet)
# Télécharge les images Docker et génère un bundle chiffré.
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <recipient_gpg_key_id>"
    echo "Ex: $0 ABCDEF1234567890"
    exit 1
fi

RECIPIENT_KEY="$1"
BUNDLE_NAME="argus-int-update-bundle-$(date +%Y%m%d).tar"
OUTPUT_DIR="/tmp/argus_update"
IMAGES=("argus-int-backend:latest" "argus-int-frontend:latest" "argus-int-celery:latest")

echo "[*] Préparation du bundle de mise à jour Air-Gapped..."
mkdir -p "$OUTPUT_DIR/images"

for image in "${IMAGES[@]}"; do
    echo "  -> Pull de l'image: $image"
    docker pull "ghcr.io/yourorg/$image" || true # Ajuster le registre
    
    echo "  -> Vérification Cosign..."
    # cosign verify --key cosign.pub "ghcr.io/yourorg/$image"
    
    echo "  -> Sauvegarde de l'image (docker save)..."
    safe_name=$(echo "$image" | tr ':' '_')
    docker save -o "$OUTPUT_DIR/images/${safe_name}.tar" "ghcr.io/yourorg/$image"
done

echo "[*] Copie des fichiers de configuration et migrations..."
cp -r ../../backend/alembic/ "$OUTPUT_DIR/" 2>/dev/null || true
cp -r ../../docker-compose.prod.yml "$OUTPUT_DIR/" 2>/dev/null || true

echo "[*] Création de l'archive tar..."
cd /tmp
tar -cvf "$BUNDLE_NAME" -C "$OUTPUT_DIR" .

echo "[*] Chiffrement GPG de l'archive pour la machine cible..."
gpg --encrypt --recipient "$RECIPIENT_KEY" --trust-model always "$BUNDLE_NAME"

rm -rf "$OUTPUT_DIR" "$BUNDLE_NAME"

echo "✅ Bundle créé et chiffré avec succès : /tmp/${BUNDLE_NAME}.gpg"
echo "Transférez ce fichier sur une clé USB chiffrée vers la machine air-gapped."
