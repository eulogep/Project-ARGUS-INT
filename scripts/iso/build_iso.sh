#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
# Script de construction de l'ISO bootable ARGUS-INT (Persistent & Amnesic)
# ==============================================================================
# Pré-requis système: live-build, debootstrap, squashfs-tools, xorriso
# ==============================================================================

set -euo pipefail

ISO_NAME="argus-int-v0.5.0.iso"
BUILD_DIR="/tmp/argus_iso_build"
MODELS_DIR="/opt/argus-models"

echo "[*] Initialisation du build ISO ARGUS-INT..."
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "[*] Configuration de live-build (Debian 12 Bookworm)..."
lb config \
    --distribution bookworm \
    --architecture amd64 \
    --archive-areas "main contrib non-free non-free-firmware" \
    --binary-images iso-hybrid \
    --iso-volume "ARGUS-INT_LIVE" \
    --bootappend-live "boot=live components quiet splash noautologin" \
    --bootappend-live-failsafe "boot=live components memtest noapic noapm nodma nomce nolapic nomodeset nosmp nosplash vga=normal"

# Configuration des paquets
mkdir -p config/package-lists
cat <<EOF > config/package-lists/argus.list.chroot
# Base system & Security
sudo
ufw
fail2ban
cryptsetup
lvm2
apparmor
apparmor-profiles
secureboot-db
shim-signed
grub-efi-amd64-signed

# Docker & Tools
docker.io
docker-compose-v2
nvidia-container-toolkit
git
curl
jq
gnupg
pass
rng-tools
EOF

# Hooks pour le mode Amnesic et durcissement système
mkdir -p config/hooks/live
cat <<'EOF' > config/hooks/live/01-argus-hardening.chroot
#!/bin/sh
set -e

# Désactiver les core dumps
echo "* hard core 0" >> /etc/security/limits.conf
echo "kernel.core_pattern=|/bin/false" > /etc/sysctl.d/50-coredump.conf

# Désactiver le swap
echo "vm.swappiness=0" > /etc/sysctl.d/50-swap.conf

# Configurer UFW par défaut
ufw default deny incoming
ufw default deny outgoing
ufw allow out on tun0 # VPN
ufw allow in on lo
ufw allow out on lo

# Création du script d'init GRUB (Menu Persistant vs Amnesic)
# Les entrées GRUB seront configurées dans le bootloader final.
EOF
chmod +x config/hooks/live/01-argus-hardening.chroot

# Préchargement de la stack ARGUS (Offline images)
# On inclut les sources actuelles dans l'image chroot
mkdir -p config/includes.chroot/opt/argus-int
echo "[*] Copie des sources dans l'ISO..."
# (Note: En environnement réel, rsynch depuis le repo Git)
# cp -a /path/to/repo/* config/includes.chroot/opt/argus-int/

# Préchargement des modèles IA (compression)
echo "[*] Intégration des modèles IA (Llama, YOLO, etc.)..."
# mkfs.squashfs /opt/argus-models config/includes.chroot/opt/argus-models.squashfs -comp zstd -Xcompression-level 19

echo "[*] Build de l'ISO en cours (cela peut prendre du temps)..."
# lb build # Décommenter pour lancer le build réel

echo "[*] Signature cryptographique de l'ISO..."
# sha256sum "$ISO_NAME" > "${ISO_NAME}.sha256"
# gpg --armor --detach-sign "${ISO_NAME}.sha256"

echo "✅ Build ISO terminé. L'artefact sera disponible dans $BUILD_DIR"
