# ARGUS-INT ISO Image

Ce dossier contient les scripts pour générer l'image ISO hybride ARGUS-INT.

## Contenu
- `build_iso.sh` : Script de création via live-build (Debian 12).
- `verify.sh` : Script de vérification d'intégrité de l'ISO générée (SHA256 + GPG).

## Utilisation
Pour flasher l'image ISO sur une clé USB sous Linux :
```bash
# Vérifiez l'intégrité d'abord
./verify.sh argus-int-v0.5.0.iso argus-int-v0.5.0.iso.sha256

# Copiez l'image (Remplacez sdX par votre clé USB - ATTENTION AUX ERREURS DE LECTEUR)
sudo dd if=argus-int-v0.5.0.iso of=/dev/sdX bs=4M status=progress; sync
```

La clé est désormais bootable en UEFI Secure Boot.
