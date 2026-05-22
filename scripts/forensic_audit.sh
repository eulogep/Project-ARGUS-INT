#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# Script d'audit Anti-Forensic & OPSEC
# Vérifie l'absence de swap, l'état des core dumps, et l'utilisation de tmpfs.

set -euo pipefail

echo "[*] Démarrage de l'audit forensique ARGUS-INT..."
FAILURES=0

check_status() {
    local status=$1
    local msg=$2
    if [ "$status" -eq 0 ]; then
        echo -e "  [PASS] $msg"
    else
        echo -e "  [FAIL] $msg"
        FAILURES=$((FAILURES + 1))
    fi
}

echo -e "\n[1] Vérification du Swap (Cold Boot Attack Vector)"
SWAP_COUNT=$(swapon -s | grep -v "Filename" | wc -l || true)
if [ "$SWAP_COUNT" -eq 0 ]; then
    check_status 0 "Aucun fichier d'échange (swap) actif."
else
    check_status 1 "Fichiers de swap détectés ! Risque de fuite de mémoire."
    swapon -s
fi

echo -e "\n[2] Vérification des Core Dumps"
CORE_LIMIT=$(ulimit -c || true)
if [ "$CORE_LIMIT" = "0" ]; then
    check_status 0 "Core dumps désactivés au niveau ulimit."
else
    check_status 1 "Core dumps activés (ulimit -c = $CORE_LIMIT)."
fi

SYSCTL_CORE=$(sysctl kernel.core_pattern 2>/dev/null | awk '{print $3}' || echo "N/A")
if [[ "$SYSCTL_CORE" == "/dev/null" ]] || [[ "$SYSCTL_CORE" == "" ]]; then
    check_status 0 "kernel.core_pattern redirigé ou désactivé."
else
    check_status 1 "kernel.core_pattern est configuré : $SYSCTL_CORE"
fi

echo -e "\n[3] Vérification des points de montage critiques en tmpfs (RAM)"
CRITICAL_DIRS=("/tmp" "/var/crash")
for dir in "${CRITICAL_DIRS[@]}"; step=0; do
    if mount | grep -q "on $dir type tmpfs"; then
        check_status 0 "$dir est monté en tmpfs."
    else
        check_status 1 "$dir n'est PAS monté en tmpfs. Les données sont écrites sur disque !"
    fi
done

echo -e "\n[4] Vérification des logs Docker (mode local / json-file)"
# On vérifie si Docker est configuré avec un pilote de journalisation sécurisé ou avec une rotation très stricte.
DOCKER_CFG="/etc/docker/daemon.json"
if [ -f "$DOCKER_CFG" ]; then
    if grep -q '"log-driver": "local"' "$DOCKER_CFG"; then
        check_status 0 "Le démon Docker utilise le log-driver 'local' (compressé/binaire par défaut)."
    elif grep -q '"max-size"' "$DOCKER_CFG"; then
        check_status 0 "Le démon Docker a une taille max de logs définie."
    else
         check_status 1 "Configuration de logging Docker sub-optimale. Risque d'accumulation sur disque."
    fi
else
    check_status 1 "Fichier de configuration $DOCKER_CFG introuvable."
fi

echo -e "\n[5] Vérification des permissions de fichiers sensibles (.env)"
ENV_FILES=$(find /opt/argus-int "$(pwd)" -name ".env" -type f 2>/dev/null || true)
if [ -z "$ENV_FILES" ]; then
    echo "  [INFO] Aucun fichier .env trouvé."
else
    for file in $ENV_FILES; do
        PERMS=$(stat -c "%a" "$file")
        if [ "$PERMS" -eq 600 ] || [ "$PERMS" -eq 400 ]; then
            check_status 0 "$file a des permissions sécurisées ($PERMS)."
        else
            check_status 1 "$file a des permissions non sécurisées ($PERMS). Devrait être 600 ou 400."
        fi
    done
fi

echo -e "\n[*] Bilan de l'audit :"
if [ "$FAILURES" -eq 0 ]; then
    echo -e "✅ AUDIT RÉUSSI : La configuration OPSEC Anti-Forensic est conforme."
    exit 0
else
    echo -e "❌ AUDIT ÉCHOUÉ : $FAILURES vulnérabilités de rétention de données détectées."
    exit 1
fi
