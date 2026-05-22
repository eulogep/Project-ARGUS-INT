# Guide de Vérification Cryptographique ARGUS-INT

N'exécutez **JAMAIS** un binaire ou une ISO ARGUS-INT sans l'avoir vérifié cryptographiquement au préalable.

## Pré-requis
Avoir `gpg` ou `gpg2` installé sur votre système hôte.

## Étapes de Validation
1. **Importer la Clé Publique**
   Récupérez la clé publique officielle depuis le fichier `MAINTAINERS.md` ou un serveur de clés (ex: keys.openpgp.org).
   ```bash
   gpg --recv-keys [FINGERPRINT]
   ```

2. **Vérifier le fichier SHA256SUMS**
   Une fois l'ISO et les fichiers de signature téléchargés :
   ```bash
   gpg --verify SHA256SUMS.asc SHA256SUMS
   ```
   *Vous devez obtenir un message indiquant "Bonne signature de..."*

3. **Valider l'Intégrité de l'Archive**
   ```bash
   sha256sum --check SHA256SUMS
   ```

*(Vous pouvez également utiliser notre script automatisé `scripts/release/verify_release.sh` si vous disposez du code source validé).*
