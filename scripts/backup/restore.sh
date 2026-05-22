#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# Restauration des Backups ARGUS-INT
# Reconstitue, déchiffre et restaure.
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <date_prefix> <target_dir>"
    echo "Ex: $0 argus_backup_20260523_100000 /opt/argus-backups"
    exit 1
fi

PREFIX="$1"
BACKUP_DIR="$2"
EXTRACT_DIR="/tmp/argus_restore_$(date +%s)"

echo "[*] Démarrage de la restauration: $PREFIX"

# 1. Vérification du manifest
MANIFEST_SIG="${BACKUP_DIR}/${PREFIX}_manifest.json.sig"
if [ ! -f "$MANIFEST_SIG" ]; then
    echo "[-] Manifest introuvable: $MANIFEST_SIG"
    exit 1
fi

echo "[*] Vérification de la signature du Manifest..."
if ! gpg --verify "$MANIFEST_SIG"; then
    echo "[-] ERREUR: Signature du manifest invalide."
    exit 1
fi

mkdir -p "$EXTRACT_DIR"

# 2. Reconstitution des parts
echo "[*] Reconstitution de l'archive chiffrée..."
cat ${BACKUP_DIR}/${PREFIX}.tar.gpg.part_* > "${EXTRACT_DIR}/backup.tar.gpg"

# 3. Déchiffrement
echo "[*] Déchiffrement (Votre Passphrase GPG sera demandée)..."
gpg --decrypt "${EXTRACT_DIR}/backup.tar.gpg" > "${EXTRACT_DIR}/backup.tar"

# 4. Extraction
tar -xf "${EXTRACT_DIR}/backup.tar" -C "$EXTRACT_DIR"

# 5. Restauration PostgreSQL
if [ -f "${EXTRACT_DIR}/postgres.dump" ]; then
    echo "[*] Restauration PostgreSQL..."
    docker cp "${EXTRACT_DIR}/postgres.dump" argus-postgres:/tmp/
    # Arrêt du backend pour éviter les écritures concurrentes
    docker stop argus-backend argus-celery-worker || true
    docker exec argus-postgres pg_restore -U argus -d argus_int --clean --if-exists /tmp/postgres.dump
fi

# Nettoyage
echo "[*] Nettoyage RAM/Disque (shred)..."
shred -u "${EXTRACT_DIR}/backup.tar"
rm -rf "$EXTRACT_DIR"

echo "✅ Restauration terminée. Pensez à redémarrer les services (docker-compose up -d)."
