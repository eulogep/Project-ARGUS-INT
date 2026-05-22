# ARGUS-INT : EMBARGO POLICY

En raison de la nature critique des environnements de déploiement d'ARGUS-INT (CTI, Journalisme, Infrastructures Air-Gapped), nous appliquons une politique stricte d'embargo sur les divulgations de vulnérabilités.

## Service-Level Agreement (SLA) de Résolution

| Criticité (CVSS) | Délai de Patch (Maintainers) | Délai d'Embargo avant Disclosure Publique | Notification Enterprise |
|------------------|------------------------------|------------------------------------------|--------------------------|
| **CRITICAL** (9.0-10.0) | 7 jours | 14 jours post-patch | Immédiate (PGP) |
| **HIGH** (7.0-8.9) | 14 jours | 30 jours post-patch | Sous 24h |
| **MEDIUM** (4.0-6.9) | 30 jours | 90 jours post-patch | Batch Mensuel |
| **LOW** (0.1-3.9) | 90 jours | 120 jours post-patch | Non requise |

## Définitions de Criticité
- **CRITICAL** : Exécution de code à distance (RCE) sur le backend, contournement total de l'authentification, fuite massive de la base de données Neo4j/Postgres.
- **HIGH** : Élévation de privilèges (de simple analyste à admin), injection SQL/Cypher complexe nécessitant des droits.
- **MEDIUM** : XSS stockée, fuite d'informations partielles, contournement du proxy HUMINT.
- **LOW** : Problèmes de configuration par défaut mineurs, bugs sans impact de sécurité direct.

## Processus de Coordination
1. **Tri et Validation** : Sous 72 heures après réception du rapport via email PGP.
2. **Patching** : L'équipe Core développe un correctif dans un dépôt privé.
3. **Notification Privée** : Les utilisateurs enregistrés (liste de diffusion PGP sécurisée) reçoivent l'avis de sécurité et le patch avant la publication publique.
4. **Disclosure Publique** : Passé le délai d'embargo, les détails techniques et la CVE (si applicable) sont publiés dans `SECURITY_ADVISORY`.

> [!WARNING]
> La publication non coordonnée (Zero-Day drop) d'une vulnérabilité critique sur ARGUS-INT met potentiellement en danger la vie des opérateurs sur le terrain. Nous appelons à la plus grande responsabilité.
