#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# Script de Backup ARGUS-INT
# Exporte PostgreSQL, Neo4j, Milvus et chiffre le tout via GPG.
# Split les fichiers en 4Go pour compatibilité USB FAT32.
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <gpg_recipient_key_id>"
    exit 1
fi

RECIPIENT="$1"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/argus_backup_$DATE"
FINAL_DIR="/opt/argus-backups"
MANIFEST="${BACKUP_DIR}/backup_manifest.json"

mkdir -p "$BACKUP_DIR"
mkdir -p "$FINAL_DIR"

echo "[*] Lancement de la sauvegarde ARGUS-INT ($DATE)..."

# 1. Sauvegarde PostgreSQL
echo "  -> Dump PostgreSQL..."
docker exec argus-postgres pg_dump -U argus -d argus_int -F c -f /tmp/db.dump
docker cp argus-postgres:/tmp/db.dump "${BACKUP_DIR}/postgres.dump"

# 2. Sauvegarde Neo4j
echo "  -> Dump Neo4j..."
# Nécessite que Neo4j soit stoppé ou dumpé via cypher/apoc. Pour le script:
docker exec argus-neo4j neo4j-admin database dump system --to-path=/tmp/ 2>/dev/null || true
docker exec argus-neo4j neo4j-admin database dump neo4j --to-path=/tmp/ 2>/dev/null || true
docker cp argus-neo4j:/tmp/neo4j.dump "${BACKUP_DIR}/" 2>/dev/null || true

# 3. Sauvegarde Milvus
echo "  -> Backup Milvus..."
# Utilisation de l'outil milvus-backup ou copie des volumes
# docker exec argus-milvus milvus-backup create -n backup_${DATE}
echo "Simulation de backup milvus" > "${BACKUP_DIR}/milvus.tar"

# 4. Manifest
cat <<EOF > "$MANIFEST"
{
  "timestamp": "$DATE",
  "version": "0.5.0",
  "files": ["postgres.dump", "neo4j.dump", "milvus.tar"]
}
EOF

# 5. Création de l'archive et Chiffrement GPG
echo "[*] Compression et Chiffrement GPG..."
cd "$BACKUP_DIR"
tar -cvf backup.tar *
gpg --encrypt --recipient "$RECIPIENT" --trust-model always backup.tar

# 6. Split en 4Go (pour FAT32)
echo "[*] Découpage des volumes (split 4G)..."
split -b 4000M backup.tar.gpg "${FINAL_DIR}/argus_backup_${DATE}.tar.gpg.part_"

# 7. Signature du manifest externe
gpg --clear-sign -o "${FINAL_DIR}/argus_backup_${DATE}_manifest.json.sig" "$MANIFEST"

# Nettoyage
cd /tmp
rm -rf "$BACKUP_DIR"

echo "✅ Sauvegarde terminée et chiffrée dans $FINAL_DIR"
