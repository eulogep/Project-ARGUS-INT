# ARGUS-INT : LONG-TERM SUPPORT (LTS) PLAN

Ce document décrit le calendrier de maintenance et le cycle de vie (End-of-Life) de la plateforme.

## 1. Calendrier de Maintenance

- **Quotidien** :
  - Sauvegarde chiffrée GPG (Postgres, Neo4j, Milvus) vers un disque externe.
  - Heartbeat du Dead Man's Switch.
- **Hebdomadaire** :
  - Test automatisé de restauration des backups (`test_restore.sh`).
  - Mises à jour de sécurité de l'OS (`unattended-upgrades`).
- **Mensuel** :
  - Mises à jour des dépendances Docker (Cosign verified).
  - Rotation des Honeytokens (Canaris).
- **Trimestriel** :
  - Rotation des clés API et clés LUKS secondaires.
  - Mise à jour des poids des modèles d'IA si des versions plus performantes sont publiées.
- **Annuel** :
  - Audit de sécurité complet / Red Teaming.
  - Key Ceremony pour rotation de la clé GPG Master.

## 2. Procédure de Fin de Vie (EOL / Decommissioning)

Lorsqu'un serveur ARGUS-INT doit être détruit (migration ou fin de mission) :
1. Déclenchez le `Panic Wipe` (`nuke.sh`) pour écraser les clés LUKS de la RAM.
2. Formatez bas-niveau les disques SSD de données avec un Secure Erase constructeur ou `shred` (3 passes minimum).
3. Révocation des certificats TLS et clés API liées à l'IP de la machine.
4. Destruction physique (broyeur) des disques si requis par le niveau de classification.
