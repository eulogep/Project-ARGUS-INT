# ARGUS-INT : INCIDENT RESPONSE RUNBOOK & FORENSIC PROTOCOLS

**CLASSIFICATION:** TIER-1 / RESTRICTED  
**LAST UPDATED:** 2026-05-23  

> [!CAUTION]  
> Ce document doit être conservé dans un emplacement sécurisé et imprimé pour un accès hors-ligne. Les procédures décrites ci-dessous incluent des options d'effacement de données irréversibles.  

---

## 🛑 ARBRES DE DÉCISION D'URGENCE

### 🚨 Scénario A : Saisie Physique Imminente (Physical Raid)
**Symptômes :** Détection d'intrusion physique dans l'installation ou raid imminent.

1. **L'opérateur a-t-il un accès physique ou distant immédiat au système ?**
   - **OUI** ➔ Exécuter immédiatement le *Panic Wipe* local ou via l'API cachée.
     ```bash
     # Local
     sudo CONFIRM_NUKE=YES ARGUS_ENV=production bash /opt/argus-int/scripts/nuke.sh
     
     # Distant
     curl -X POST https://[SERVER_IP]/api/v1/system/panic \
          -H "x-panic-token: [VOTRE_TOKEN_HMAC]"
     ```
   - **NON** ➔ Passer à l'étape 2.
2. **Attendre le *Dead Man's Switch*.** 
   - L'infrastructure s'auto-détruira si aucun signal n'est reçu sous 48h.

### 🚨 Scénario B : Compromission Réseau (Network Breach / RCE)
**Symptômes :** Alerte Canari (Honeytoken) déclenchée, activité ssh inhabituelle, anomalies CPU/GPU massives sans investigation en cours.

1. **Isolation Immédiate (Lockdown) :**
   - Débrancher physiquement le câble réseau OU exécuter :
     ```bash
     sudo ufw default deny incoming
     sudo ufw default deny outgoing
     sudo ufw allow in on lo
     sudo ufw reload
     ```
2. **Préservation Forensique (Si nécessaire pour attribution) :**
   - Ne **pas** éteindre le serveur (perte des clés en RAM et des malwares "fileless").
   - Créer un dump mémoire :
     ```bash
     sudo dd if=/dev/mem of=/media/usb/memory_dump.bin bs=1M
     ```
3. **Audit et Révocation :**
   - Vérifier les alertes Canaris dans Redis/Logs.
   - Faire tourner le script : `bash scripts/forensic_audit.sh`

### 🚨 Scénario C : Data Poisoning (Milvus Vector DB)
**Symptômes :** Le module `anti_poisoning.py` émet une alerte `cluster_collapse` ou `high_outlier_ratio`.

1. **Isoler l'Investigation Corrompue :**
   - Le système a automatiquement placé le batch en quarantaine (PostgreSQL `quarantined_vectors`).
2. **Analyse du Vecteur d'Attaque :**
   - Vérifier si les images proviennent d'une source OSINT récemment compromise ou si des *Adversarial Patches* ont été identifiés par le module YOLOv8/InsightFace Red Team.
3. **Rollback Milvus :**
   - Supprimer la partition d'investigation affectée :
     ```python
     # Script utilitaire
     from pymilvus import Collection
     collection = Collection("FaceVectors")
     collection.drop_partition("inv-compromised-123")
     ```

### 🚨 Scénario D : Perte de Heartbeat (Dead Man's Switch Triggered)
**Symptômes :** Le système a déclenché le `nuke.sh` automatiquement après 48h sans ping.

1. **Vérifier s'il s'agit d'un Faux Positif :**
   - Le VPN de l'opérateur était-il en panne ? L'opérateur est-il en sécurité ?
2. **Restitution après Faux Positif :**
   - Le serveur est en *Kernel Panic*. Redémarrer physiquement.
   - Entrer la phrase secrète LUKS au boot.
   - Le système d'exploitation et la base de données sont intacts (les données n'ont pas été formatées, seules les clés RAM ont été purgées et les processus coupés).

---

## 📞 CONTACTS & PROCÉDURES SÉCURISÉES

- Ne **jamais** discuter d'une brèche sur des canaux en clair (SMS, Telegram classique, Discord).
- Utiliser **Signal** avec des messages éphémères (1h).
- Pour l'envoi de logs compromis, utiliser le chiffrement **PGP** avec la clé publique de l'équipe d'intervention de niveau 2 (Tier-2 IRT).

**Clé PGP Tier-2 :**
```text
-----BEGIN PGP PUBLIC KEY BLOCK-----
[Insérer la clé publique opérationnelle]
-----END PGP PUBLIC KEY BLOCK-----
```
