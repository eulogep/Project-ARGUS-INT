# ARGUS-INT Succession Plan (Bus Factor)

La pérennité d'un outil CTI critique ne doit pas dépendre d'un seul individu.

## Passation des Clés Maîtresses
La clé GPG principale de release est segmentée en utilisant l'algorithme de Shamir (Shamir's Secret Sharing). 
- 5 fragments matériels existent.
- 3 sont nécessaires pour reconstituer la clé privée.
- Ces fragments sont détenus par des membres du Board de Gouvernance situés dans des juridictions différentes.

## Scénario d'Indisponibilité
Si le Lead Architect est indisponible (injoignable pendant plus de 30 jours sans préavis), le protocole d'urgence est déclenché sur le groupe Signal sécurisé.
1. Le Head of OPSEC prend temporairement la direction du projet.
2. Les mainteneurs se réunissent pour rassembler les fragments de Shamir.
3. Une nouvelle clé "Subkey" est émise pour signer les releases futures.
4. Un avis de succession est publié de manière transparente à la communauté via l'annonce PGP.
