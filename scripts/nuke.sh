#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# SCRIPT DE PANIC WIPE (AUTO-DESTRUCTION) NIVEAU INFRASTRUCTURE
# ==============================================================================
# ATTENTION : CE SCRIPT EFFECTUE DES OPERATIONS DESTRUCTRICES IRREVERSIBLES.
# IL EST CONÇU POUR LES SCÉNARIOS DE SAISIE PHYSIQUE IMMINENTE.

set -euo pipefail

# 1. Protections de sécurité contre une exécution accidentelle
if [[ "${ARGUS_ENV:-}" != "production" ]]; then
    echo "[!] ARGUS_ENV n'est pas 'production'. Arrêt du script."
    exit 1
fi

if [[ "${CONFIRM_NUKE:-}" != "YES" ]]; then
    echo "[!] CONFIRM_NUKE n'est pas 'YES'. Arrêt du script."
    exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
    echo "[!] Ce script doit être exécuté en tant que root."
    exit 1
fi

echo "[!!!] INITIATION DE L'AUTO-DESTRUCTION DE L'INFRASTRUCTURE ARGUS-INT [!!!]"

# 2. Arrêt d'urgence de tous les conteneurs (sans délai de grâce)
echo "[*] Arrêt immédiat de tous les conteneurs..."
docker ps -q | xargs -r docker kill >/dev/null 2>&1 || true

# 3. Destruction des clés LUKS en RAM (si LUKS est utilisé)
# Supprime les clés actives en mémoire. Le disque deviendra immédiatement illisible au redémarrage,
# mais restera accessible tant qu'il n'est pas démonté ou que le cache système n'est pas vidé.
echo "[*] Effacement des clés LUKS de la mémoire vive..."
# On liste les volumes LUKS ouverts
CRYPT_VOLUMES=$(lsblk -o NAME,FSTYPE | grep crypt | awk '{print $1}' | sed 's/└─//g' | sed 's/├─//g')
for vol in $CRYPT_VOLUMES; do
    echo "  -> Suspension du volume chiffré: $vol"
    # L'option suspend efface la clé de la RAM.
    # Pour accéder au volume, il faudrait utiliser 'cryptsetup resume' + mot de passe.
    cryptsetup suspend "$vol" || echo "     [!] Echec suspension $vol"
done

# 4. Déclenchement d'un Kernel Panic
# SYSRQ doit être activé : echo 1 > /proc/sys/kernel/sysrq
# Ceci crash le système immédiatement, vide la RAM (si l'OS est configuré pour ne pas faire de dump)
# et prévient les attaques de type Cold Boot en limitant le temps de rétention en RAM.
echo "[*] DÉCLENCHEMENT DU KERNEL PANIC..."

# On s'assure que SysRq est activé
echo 1 > /proc/sys/kernel/sysrq || true

# Synchro disque avant crash (optionnel, mais utile si on veut s'assurer que des fichiers d'audit écrasés le sont bien)
# sync

# CRASH (ne passera jamais à l'instruction suivante)
echo c > /proc/sysrq-trigger
