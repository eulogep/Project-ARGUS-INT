# ARGUS-INT Operations Manual

Ce document régit l'ensemble des procédures d'exploitation, de déploiement et de gestion des incidents pour la plateforme ARGUS-INT.

---

## 🚀 Deployment Procedures

### Initial Deployment
```bash
# 1. Clone repository
git clone https://github.com/your-org/argus-int.git
cd argus-int

# 2. Decrypt production secrets
sops --decrypt .env.prod.enc > .env.prod

# 3. Run hardening script
sudo ./deploy.sh

# 4. Verify deployment
curl http://localhost:8000/health
curl http://localhost:3000
```

### Rolling Updates
```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild images
docker compose -f docker-compose.prod.yml build

# 3. Rolling restart (zero downtime)
docker compose -f docker-compose.prod.yml up -d --no-deps --build backend
docker compose -f docker-compose.prod.yml up -d --no-deps --build frontend

# 4. Verify health
docker compose -f docker-compose.prod.yml ps
```

---

## 🔐 Secrets Management

### Decrypt, Edit and Re-encrypt
```bash
# 1. Generate new secret
openssl rand -hex 32

# 2. Edit encrypted file
sops .env.prod.enc

# 3. Restart affected services
docker compose -f docker-compose.prod.yml restart backend celery-worker

# 4. Verify services healthy
docker compose -f docker-compose.prod.yml ps
```

### Adding New Secrets
```bash
# 1. Decrypt, edit, re-encrypt
sops --decrypt .env.prod.enc > .env.prod
echo "NEW_SECRET=value" >> .env.prod
sops --encrypt --age $(cat ~/.config/sops/age/keys.txt | grep public | awk '{print $NF}') .env.prod > .env.prod.enc
rm .env.prod
```

---

## 🖋️ Signature & Traçabilité (GPG & OpenTimestamps)

Afin de garantir l'imputabilité et de prévenir toute falsification de l'historique de livraison :

### 1. Signature GPG des commits et tags
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

### 2. Ancrage OpenTimestamps des releases
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

## 🗄️ Backup & Restoration

### Backup Procedure (Cron automated)
Le script `/etc/cron.daily/argus-backup` s'exécute automatiquement chaque jour, extrait les données, les compresse et les chiffre à l'aide de la clé GPG de sauvegarde configurée.

### Restoration Procedure
```bash
# 1. Stop services
docker compose -f docker-compose.prod.yml down

# 2. Restore PostgreSQL
gunzip -c backup-20240115.sql.gz | docker exec -i argus-postgres psql -U argus argus_int

# 3. Restore Neo4j
docker cp neo4j-20240115.dump argus-neo4j:/backups/
docker exec argus-neo4j neo4j-admin load --from=/backups/neo4j-20240115.dump --database=neo4j --force

# 4. Restart services
docker compose -f docker-compose.prod.yml up -d
```

---

## 🚨 Incident Response

### Panic Wipe (Emergency Data Destruction)
En cas de compromission physique d'un poste ou du serveur :
- **Côté analyste** : Enfoncer 3 fois rapidement la touche `Échap` sur le C2 frontend (purgera instantanément le cache local).
- **Côté serveur de production** (Wipe complet) :
  ```bash
  # Trigger immediate data wipe
  docker compose -f docker-compose.prod.yml down -v
  rm -rf /opt/argus-data/*
  shred -vfz -n 3 /opt/argus-data/.  # Overwrite 3 times
  
  # Wipe Docker volumes
  docker volume rm $(docker volume ls -q | grep argus)
  
  # Clear logs
  rm -rf /var/lib/docker/containers/*/*-json.log
  ```

### Service Recovery
```bash
# Check service status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs --tail=100 backend

# Restart specific service
docker compose -f docker-compose.prod.yml restart backend

# Force recreate container
docker compose -f docker-compose.prod.yml up -d --force-recreate backend
```

---

## 📊 Monitoring & Alerting

### Prometheus Metrics
- **Backend API**: `http://localhost:8000/metrics`
- **Neo4j**: `http://localhost:7474/metrics`
- **PostgreSQL**: Configuré via `postgres_exporter`

### Key Metrics to Monitor
- Temps de réponse de l'API (p95 < 200ms)
- Taux d'erreur HTTP (réponses 5xx)
- Nombre de connexions WebSockets actives
- Longueur de la queue Celery
- Utilisation du pooler de connexion DB
- Utilisation de la mémoire et du CPU

### Alert Thresholds
- Taux d'erreur API > 1% pendant 5 minutes
- Temps de réponse p95 > 500ms pendant 10 minutes
- Connexions WebSockets > 1000 actives
- Queue Celery > 100 tâches
- Utilisation mémoire > 80%

---

## 🔧 Troubleshooting

### Backend Won't Start
```bash
# Check logs
docker compose -f docker-compose.prod.yml logs backend

# Verify database connectivity
docker exec argus-backend curl http://postgres:5432

# Check environment variables
docker exec argus-backend env | grep DATABASE
```

### Neo4j Performance Issues
```bash
# Check Neo4j logs
docker compose -f docker-compose.prod.yml logs neo4j

# Verify heap memory
docker exec argus-neo4j neo4j-admin memrec

# Restart with increased memory (Edit docker-compose.prod.yml variables if needed)
docker compose -f docker-compose.prod.yml up -d neo4j
```

### WebSocket Disconnections
```bash
# Check backend logs for WebSocket errors
docker compose -f docker-compose.prod.yml logs backend | grep -i websocket
```

---

## 📞 Emergency Contacts
- **Administrateur Système** : [Nom] - [Téléphone/Signal]
- **Équipe Sécurité** : [Nom] - [Téléphone/Signal]
- **Administrateur DB** : [Nom] - [Téléphone/Signal]

**Dernière mise à jour** : 2024-01-15  
**Propriétaire** : ARGUS-INT Operations Team  
**Classification** : INTERNAL USE ONLY
