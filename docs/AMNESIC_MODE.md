# ARGUS-INT : AMNESIC MODE GUIDE (Forensic-Safe)

L'ISO bootable d'ARGUS-INT possède un mode "Amnesic" conçu pour le déploiement temporaire et l'absence totale de traces forensiques.

## Fonctionnement
- **Support Live** : L'OS se charge entièrement en mémoire vive (RAM).
- **Zéro Écriture** : Par défaut, aucun disque dur interne n'est monté.
- **Désactivation SWAP** : Empêche la mémoire de s'écrire sur le disque.
- **Logs en Tmpfs** : Les journaux Docker disparaissent à l'extinction.

## Cas d'Usage
- Saisie de matériel suspect sur site (extraction OCR via PaddleOCR sans laisser de traces).
- Accès à une investigation chiffrée depuis une machine non-maîtrisée (Cybercafé, poste compromis).

## Utilisation
1. Flashez l'ISO ARGUS-INT sur une clé USB.
2. Rebootez la machine cible sur l'USB.
3. Au menu GRUB, choisissez **ARGUS-INT Amnesic (Forensic-Safe)**.
4. Une fois le travail terminé, éteignez la machine. Tout est détruit.
