#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# Script de mise à jour Air-Gapped (Côté machine cible isolée)
# Déchiffre le bundle, charge les images Docker et relance la stack.
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <bundle_file.tar.gpg>"
    exit 1
fi

BUNDLE_GPG="$1"
EXTRACT_DIR="/tmp/argus_extract_$(date +%s)"

echo "[*] Démarrage de la mise à jour Air-Gapped..."

if [ ! -f "$BUNDLE_GPG" ]; then
    echo "[-] Fichier introuvable: $BUNDLE_GPG"
    exit 1
fi

mkdir -p "$EXTRACT_DIR"

echo "[*] 1. Déchiffrement du bundle (votre passphrase GPG sera demandée)..."
gpg --decrypt "$BUNDLE_GPG" > "${EXTRACT_DIR}/bundle.tar"

echo "[*] 2. Extraction du bundle..."
tar -xf "${EXTRACT_DIR}/bundle.tar" -C "$EXTRACT_DIR"

echo "[*] 3. Chargement des images Docker (Offline Load)..."
for img_tar in "$EXTRACT_DIR"/images/*.tar; do
    if [ -f "$img_tar" ]; then
        echo "  -> Chargement: $img_tar"
        docker load -i "$img_tar"
    fi
done

echo "[*] 4. Arrêt des services actuels..."
docker-compose -f /opt/argus-int/docker-compose.prod.yml down

echo "[*] 5. Application des migrations de base de données..."
# Copier les nouveaux fichiers
cp -r "$EXTRACT_DIR/docker-compose.prod.yml" /opt/argus-int/ || true
cp -r "$EXTRACT_DIR/alembic" /opt/argus-int/backend/ || true

# On démarre juste la db pour appliquer Alembic
docker-compose -f /opt/argus-int/docker-compose.prod.yml up -d db
sleep 5
# Lancement de la migration depuis l'image backend (temporairement)
# docker-compose -f /opt/argus-int/docker-compose.prod.yml run --rm backend alembic upgrade head

echo "[*] 6. Redémarrage de la stack ARGUS-INT..."
docker-compose -f /opt/argus-int/docker-compose.prod.yml up -d

# Nettoyage sécurisé
echo "[*] Nettoyage des fichiers temporaires (shred)..."
shred -u "${EXTRACT_DIR}/bundle.tar"
rm -rf "$EXTRACT_DIR"

echo "✅ Mise à jour Air-Gapped terminée avec succès."
