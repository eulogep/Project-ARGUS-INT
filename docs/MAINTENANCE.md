# ARGUS-INT : MAINTENANCE GUIDE

Guide de maintenance pour les administrateurs système de la plateforme.

---

## 1. Rotation des Secrets
Toutes les clés d'API, certificats TLS et mots de passe DB doivent être tournés tous les 90 jours.
1. Générez les nouveaux secrets dans un gestionnaire (Pass / SOPS).
2. Mettez à jour le `.env` de production.
3. Relancez la stack : `docker-compose -f docker-compose.prod.yml up -d`

## 2. Mise à Jour des Modèles IA (Local)
Les modèles (YOLOv8, Llama-3, OpenCLIP) se trouvent dans `/opt/argus-models`.
Pour mettre à jour en Air-Gapped :
1. Sur machine connectée, téléchargez les poids GGUF/Safetensors.
2. Signez-les cryptographiquement.
3. Importez via clé USB chiffrée.
4. Remplacez l'ancien fichier et redémarrez le conteneur vLLM ou backend.

## 3. Backups (Sauvegarde / Restauration)
La configuration OPSEC par défaut détruit tout. Les backups sont vitaux.
- **Backup automatique** : Programmé par crontab avec `scripts/backup/backup.sh`. Chiffré en GPG.
- **Restauration** : Utilisez `scripts/backup/restore.sh` en ayant votre clé privée sur une YubiKey.

## 4. Monitoring
- Accédez au tableau de bord Grafana (`http://localhost:3000`).
- Surveillez la mémoire GPU via `nvidia-smi`. Si la VRAM dépasse 95%, vérifiez que Celery purge correctement après les tâches (GPUTask).
