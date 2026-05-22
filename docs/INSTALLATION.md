# ARGUS-INT : INSTALLATION GUIDE

Ce document couvre l'installation d'ARGUS-INT pour trois profils de déploiement distincts. 

---

## 1. Profil Débutant : Déploiement VPS (Connecté)
*Idéal pour les tests, OSINT de surface.*

1. **Pré-requis** : Ubuntu 22.04 LTS, 16 Go RAM, 4 vCPU.
2. **Clonage** :
   ```bash
   git clone https://github.com/yourorg/argus-int.git
   cd argus-int
   ```
3. **Configuration** :
   Copiez `.env.example` en `.env` et générez des mots de passe forts.
4. **Lancement** :
   ```bash
   sudo ./deploy.sh
   docker-compose -f docker-compose.prod.yml up -d
   ```

---

## 2. Profil Avancé : Déploiement Kubernetes (K8s)
*Idéal pour une équipe CTI, haute disponibilité, inférence distribuée.*

1. **Pré-requis** : Cluster K8s (1 master, 2 workers GPU).
2. **Secrets** :
   Utilisez SOPS pour chiffrer vos secrets et déployer `SealedSecrets` sur le cluster.
3. **Déploiement Helm** :
   ```bash
   helm upgrade --install argus-int ./helm/argus-int \
     --namespace intelligence --create-namespace \
     -f values.prod.yaml
   ```

---

## 3. Profil Expert : Serveur Air-Gapped (Mode Paranoïaque)
*Idéal pour le traitement de données classifiées / saisies, isolé d'Internet.*

1. **Pré-requis** :
   - Ordinateur dédié, disque dur vierge.
   - Boot depuis l'ISO ARGUS-INT (`build_iso.sh`).
2. **Installation** :
   - Au menu GRUB, choisissez **Install ARGUS-INT (Persistent LUKS)**.
   - Suivez le guide Debian pour définir votre passphrase LUKS.
3. **Premier démarrage** :
   - Le système est prêt. Pas de Wi-Fi, pas d'Ethernet connecté.
   - Les modèles IA (vLLM, Vision) sont préchargés dans `/opt/argus-models`.
   - Lancez `docker-compose up -d`.
