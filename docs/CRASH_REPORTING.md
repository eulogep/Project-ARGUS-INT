# ARGUS-INT Anonymous Crash Reporting

En cas de défaillance critique du système (Kernel Panic, OOM GPU persistant), vous pouvez nous faire parvenir un rapport de crash.
Pour garantir une OPSEC stricte, ce rapport est expurgé de toute donnée personnelle, chiffré, et routé via Tor.

## Comment générer un rapport ?

Exécutez simplement le script prévu à cet effet :
```bash
./scripts/support/report_crash.sh
```

## Que contient le rapport ?
Le script effectue automatiquement les actions suivantes :
1. **Extraction** : Récupère les 500 dernières lignes des logs de `argus-backend` et `argus-vllm`.
2. **Anonymisation** : Remplace les adresses IP (IPv4/IPv6), les chemins absolus (ex: `/home/user/...`) et les hashes par des placeholders (`[REDACTED]`).
3. **Chiffrement** : Chiffre le rapport avec notre clé PGP publique.
4. **Envoi** : Utilise `torsocks` pour expédier le paquet vers notre backend de support via le réseau Tor.

## Soumission Manuelle
Si la machine n'a pas accès au réseau Tor, le script génèrera un fichier `crash_report.tar.gz.gpg` en local. Vous pourrez l'extraire par USB et l'envoyer manuellement à `support@argus.local`.
