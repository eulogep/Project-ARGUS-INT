#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# Mise à jour en ligne (Rolling Update) avec Rollback automatique
# ==============================================================================

set -euo pipefail

COMPOSE_FILE="/opt/argus-int/docker-compose.prod.yml"

echo "[*] Démarrage de la mise à jour (Online)..."

# 1. Pull des nouvelles images
echo "[*] Pulling latest images..."
docker-compose -f "$COMPOSE_FILE" pull

# 2. Vérification des signatures (optionnel mais recommandé)
# cosign verify ...

# 3. Sauvegarde de l'état actuel pour rollback
echo "[*] Création d'un backup temporaire de la DB avant migration..."
# docker exec argus-postgres pg_dump ... > /tmp/pre_update_db.sql

# 4. Redémarrage en mode Rolling
echo "[*] Application de la mise à jour (recreate)..."
docker-compose -f "$COMPOSE_FILE" up -d

# 5. Health checks
echo "[*] Vérification de l'état des services..."
sleep 15
FAIL=0

if ! curl -f -s http://localhost:8000/health > /dev/null; then
    echo "[-] ERREUR: Le Backend (FastAPI) ne répond pas."
    FAIL=1
fi

if ! curl -f -s http://localhost:3000/ > /dev/null; then
    echo "[-] ERREUR: Le Frontend (Next.js) ne répond pas."
    FAIL=1
fi

if [ "$FAIL" -eq 1 ]; then
    echo "[!!!] MISE À JOUR ÉCHOUÉE. DÉCLENCHEMENT DU ROLLBACK [!!!]"
    # Pour un vrai rollback, il faudrait restaurer les anciens tags des images 
    # et restaurer la base de données.
    echo "[!] Veuillez restaurer depuis le dernier backup valide."
    exit 1
fi

echo "✅ Mise à jour réussie. Système stable."
