# ARGUS-INT Release Notes

## Version 0.5.0 (Phase 7 - Crucible & Operational Readiness)

**Date**: 2026-05-23
**Type**: Stable / Release Candidate

### Changements Majeurs
- **Amnesic ISO Build** : Introduction de la distribution Debian ARGUS-INT Live bootable. Permet des opérations forensiques sécurisées sans écriture disque.
- **Air-Gapped Updates** : Support complet des mises à jour hors-ligne (Air-gapped) via des bundles Docker chiffrés en GPG.
- **Key Ceremony** : Nouveau processus de génération sécurisée de clés asymétriques pour les opérations de haut niveau.
- **Backup & Restore** : Automatisation des dumps chiffrés GPG (split en 4Go pour FAT32) pour Postgres, Neo4j et Milvus.

### Securité & OPSEC
- Durcissement des limites système (désactivation des Core dumps, tmpfs, swap désactivé par défaut).
- Chiffrement GPG de chaque artefact.
- Signature d'image Cosign intégrée au pipeline de mise à jour.

### Breaking Changes
- Les clés de déchiffrement LUKS et GPG ne sont plus stockées dans des volumes de données montés automatiquement, nécessitant une intervention de l'opérateur (passphrase) lors d'un redémarrage.
