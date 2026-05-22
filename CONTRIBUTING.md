# Contributing to ARGUS-INT

Merci de l'intérêt que vous portez au développement d'ARGUS-INT ! En tant que projet de sécurité tactique, nous avons des exigences strictes concernant les contributions.

## OPSEC pour les Contributeurs
- Vous pouvez contribuer de manière totalement anonyme ou sous pseudonyme.
- L'utilisation d'emails masqués (ex: `@users.noreply.github.com`) est recommandée.
- Évitez de commiter des chemins locaux, des IPs ou des clés de test dans votre code.

## Processus de Pull Request (PR)
1. Forkez le projet.
2. Créez une branche (`feat/mon-ajout` ou `fix/bug-critique`).
3. **SIGNATURE OBLIGATOIRE** : Tous vos commits doivent être signés (`git commit -S`). Les PRs non signées seront automatiquement rejetées.
4. Assurez-vous de passer les linters et la suite de tests Red Team.
5. Décrivez explicitement l'impact sécurité de votre changement dans la PR.

## Règles de Codage
- Pas de requêtes sortantes (API tierces) sans approbation de l'utilisateur (HITL) et sans passer par le `ProxyRouter`.
- Pas de librairies propriétaires ou trackées par de la télémétrie.
