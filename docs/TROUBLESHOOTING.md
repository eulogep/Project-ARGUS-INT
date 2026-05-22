# ARGUS-INT : TROUBLESHOOTING GUIDE

Arbre de décision pour les pannes courantes.

---

## 1. GPU OOM (Out Of Memory)
**Symptôme** : Inférence lente, plantages de Celery, modèle refusant de charger.
- **Diagnostic** :
  ```bash
  watch -n 1 nvidia-smi
  docker logs argus-celery-gpu-heavy
  ```
- **Résolution** :
  - Lancer manuellement `torch.cuda.empty_cache()` si possible.
  - Redémarrer le conteneur VLLM : `docker restart argus-vllm`

## 2. Neo4j Saturé
**Symptôme** : Le graphe frontend fige, requêtes Cypher timeout (>30s).
- **Diagnostic** :
  - Trop de nœuds ajoutés simultanément.
  - Index manquant sur certaines propriétés.
- **Résolution** :
  - Tuer les transactions bloquées via la console Web Neo4j (`CALL dbms.listQueries()`, puis `CALL dbms.killQuery(...)`).

## 3. Dead Man's Switch Triggered par erreur
**Symptôme** : Kernel Panic soudain.
- **Diagnostic** : Vérifiez l'heure du dernier Heartbeat dans Redis.
- **Résolution** : Démarrez, entrez LUKS, et utilisez `restore.sh` si le script Nuke a corrompu certaines données temporelles, puis relancez le cron Heartbeat sur votre machine distante.

## 4. Panne Réseau Tor (ProxyRouter)
**Symptôme** : "Circuit Breaker Open", impossible d'envoyer un message HUMINT.
- **Diagnostic** : Les nœuds de sortie sont flaggés ou bloqués.
- **Résolution** : Demandez une rotation du circuit dans le router `ProxyRouter` ou passez sur un proxy résidentiel de secours.
