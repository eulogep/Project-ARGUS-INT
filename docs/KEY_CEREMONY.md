# ARGUS-INT : KEY CEREMONY GUIDE

La sécurité entière des mises à jour Air-Gapped et des sauvegardes repose sur l'intégrité de votre paire de clés GPG. Ce document décrit la cérémonie de génération.

## Protocole de Cérémonie
1. **Environnement** : Démarrez un ordinateur physiquement déconnecté du réseau sur un OS amnésique (Tails OS) via clé USB.
2. **Exécution du Script** :
   Lancez le script interactif prévu à cet effet :
   ```bash
   bash scripts/security/key_ceremony.sh
   ```
3. **Distribution** :
   - Sauvegardez le fichier `argus_pubkey.asc` sur une clé USB standard.
   - Sauvegardez le fichier `argus_privkey.asc` sur DEUX clés USB chiffrées matérielles ou LUKS.
   - Imprimez la *Paper Key* et placez-la dans un coffre-fort physique.
4. **Destruction** :
   - Éteignez l'ordinateur Tails OS. La RAM s'efface automatiquement, supprimant toute trace résiduelle de la clé privée.
