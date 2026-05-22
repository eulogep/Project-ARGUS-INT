# Operations Runbook — ARGUS-INT

Ce document décrit les procédures de maintenance, de sauvegarde, de rotation des secrets et de réponse aux incidents pour la plateforme ARGUS-INT en production.

---

## 🔐 Gestion des Secrets (SOPS + age)

Les secrets de production sont chiffrés avec SOPS (Secrets Operations) et `age` afin de ne pas être commités en clair sur le repository.

### Initialisation & Configuration
1. Générer la paire de clés `age` sur le serveur de déploiement :
   ```bash
   age-keygen -o ~/.config/sops/age/keys.txt
   ```
2. Récupérer la clé publique générée et l'inscrire dans le fichier `.sops.yaml` à la racine.
3. Chiffrer le fichier d'environnement :
   ```bash
   sops --encrypt --age <public_key> .env > .env.enc
   ```
4. Décoder à la volée pendant le déploiement (géré par `deploy.sh`) :
   ```bash
   sops --decrypt .env.enc > .env
   ```

### Procédure de Rotation des Clés
1. Générer une nouvelle clé d'encryption :
   ```bash
   openssl rand -hex 32
   ```
2. Modifier le fichier `.env.enc` avec sops :
   ```bash
   sops .env.enc
   ```
3. Mettre à jour la variable `ENCRYPTION_KEY` et sauvegarder.
4. Redémarrer les services pour appliquer la rotation :
   ```bash
   docker compose -f docker-compose.prod.yml restart backend celery-worker-identity
   ```

### 🖋️ Signature & Traçabilité (GPG & OpenTimestamps)

Afin de garantir l'imputabilité et de prévenir toute falsification de l'historique de livraison :

#### 1. Signature GPG des commits et tags
Tous les commits de développement et tags de release doivent être signés avec la clé GPG de l'analyste.
- Configurer la signature automatique locale :
  ```bash
  git config --local user.signingkey <KEY_ID>
  git config --local commit.gpgsign true
  git config --local tag.gpgSign true
  ```
- Créer un tag de release signé :
  ```bash
  git tag -s v1.0.0 -m "Release v1.0.0"
  ```

#### 2. Ancrage OpenTimestamps des releases
Chaque tag de release signé doit être ancré de manière immuable sur la blockchain Bitcoin via OpenTimestamps.
- Générer l'ancrage à partir du tag Git :
  ```bash
  git cat-file tag v1.0.0 > v1.0.0.tag
  ots stamp v1.0.0.tag
  ```
- Cela crée un fichier d'attestation `v1.0.0.tag.ots` à conserver dans le dossier des releases de l'infrastructure.
- Pour vérifier la signature temporelle ultérieurement :
  ```bash
  ots verify v1.0.0.tag.ots
  ```

---

## 🗄️ Sauvegarde & Restauration (Backups)

### 1. PostgreSQL (Base de données relationnelle)
* **Sauvegarde** :
  ```bash
  docker exec -t argus-postgres pg_dumpall -c -U phynx > postgres_backup_$(date +%F).sql
  ```
* **Restauration** :
  ```bash
  cat postgres_backup_xxx.sql | docker exec -i argus-postgres psql -U phynx -d phynx
  ```

### 2. Neo4j (Base de données Graphe)
* **Sauvegarde** (Arrêt temporaire nécessaire pour cohérence en mode Community) :
  ```bash
  docker compose -f docker-compose.prod.yml stop neo4j
  tar -czf neo4j_backup_$(date +%F).tar.gz -C /var/lib/docker/volumes/phynx_neo4j_prod_data/_data .
  docker compose -f docker-compose.prod.yml start neo4j
  ```
* **Restauration** :
  ```bash
  docker compose -f docker-compose.prod.yml stop neo4j
  tar -xzf neo4j_backup_xxx.tar.gz -C /var/lib/docker/volumes/phynx_neo4j_prod_data/_data
  docker compose -f docker-compose.prod.yml start neo4j
  ```

---

## 🚨 Réponses aux Incidents & Runbooks

### 1. Fuite ou Compromission des Données (Panic Trigger)
En cas de compromission physique d'un poste analyste :
- L'analyste doit enfoncer 3 fois rapidement la touche `Échap` sur le C2 frontend.
- Cela purge instantanément IndexedDB, les cookies de session et le stockage local, coupant la connexion au serveur.
- Si le serveur lui-même est compromis, exécuter sur la machine hôte :
  ```bash
  # Effacement à froid de l'infrastructure
  docker compose -f docker-compose.prod.yml down -v
  rm -rf /var/lib/docker/volumes/phynx_*
  ```

### 2. Surcharge de Requêtes (HTTP 429)
Si un client ou un service externe déclenche trop d'alertes de Rate Limiting :
- Consulter les logs structurés filtrés par niveau d'avertissement :
  ```bash
  docker logs argus-backend | grep -i "rate limit"
  ```
- Les adresses IP de confiance peuvent être exclues dans la configuration du middleware `security.py`.
