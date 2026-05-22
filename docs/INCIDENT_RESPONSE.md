# ARGUS-INT : INCIDENT RESPONSE RUNBOOK & FORENSIC PROTOCOLS

**CLASSIFICATION:** TIER-1 / RESTRICTED  
**LAST UPDATED:** 2026-05-23  

> [!CAUTION]  
> Ce document doit être conservé dans un emplacement sécurisé et imprimé pour un accès hors-ligne. Les procédures décrites ci-dessous incluent des options d'effacement de données irréversibles.  

---

## 🛑 ARBRES DE DÉCISION D'URGENCE

### 🚨 Scenario A: Physical Raid (Saisie Physique Imminente)
**Trigger:** Détection d'intrusion physique dans l'installation ou raid imminent.

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

2. **Verify Wipe Initiated**
   - Server should become unresponsive within 10 seconds.
   - Kernel panic will trigger, clearing RAM.
   - LUKS keys destroyed, volumes encrypted.

3. **Destroy Backup Media**
   - Physically destroy any external backup drives.
   - Burn paper documentation.
   - Wipe mobile devices if necessary.

4. **Post-Incident**
   - **DO NOT** attempt to contact the seized server.
   - Activate backup infrastructure (if available).
   - Notify legal counsel immediately.
   - Prepare statement for authorities (if required).

---

### 🕵️ Scenario B: Network Compromise Detected
**Trigger:** Honeytoken triggered, unauthorized access logs, anomalous traffic.

**Immediate Actions (< 5 minutes)**

1. **Isolate the Server**
   ```bash
   # Block all incoming traffic except your IP
   ufw default deny incoming
   ufw allow from YOUR_IP to any port 22,3000,8000
   
   # Kill all active sessions except yours
   w  # List sessions
   pkill -9 -u UNAUTHORIZED_USER
   ```

2. **Preserve Evidence (If Forensics Needed)**
   ```bash
   # Dump RAM (if you have physical access)
   # WARNING: This may alert the attacker
   dd if=/dev/mem of=/tmp/ram_dump.bin bs=1M
   
   # Capture network traffic
   tcpdump -i any -w /tmp/capture.pcap &
   
   # Snapshot running processes
   ps aux > /tmp/processes.txt
   netstat -tulnp > /tmp/network.txt
   ```

3. **Identify Compromise Vector & Containment**
   - **DO NOT** shut down the server (preserves RAM evidence).
   - **DO NOT** run antivirus (may destroy evidence).
   - Change all credentials from a clean machine.
   - Revoke all API keys and tokens.
   - Enable lockdown mode: `POST /api/v1/system/lockdown`

4. **Eradication**
   - **If compromise confirmed:** Trigger Panic Wipe and rebuild from scratch.
   - **If uncertain:** Snapshot the system, wipe, and restore from known-good backup.

---

### 🧪 Scenario C: Data Poisoning in Milvus
**Trigger:** Anti-poisoning module alerts, search results degraded, cluster collapse detected.

**Immediate Actions (< 15 minutes)**

1. **Quarantine Affected Collection**
   ```bash
   # Disable writes to the collection
   curl -X POST http://localhost:8000/api/v1/admin/milvus/quarantine \
     -d '{"collection": "FaceVectors", "investigation_id": "XXX"}'
   ```

2. **Identify Poisoned Batch**
   ```bash
   # Check quarantine table
   psql -d argus_int -c "SELECT * FROM quarantined_vectors ORDER BY created_at DESC LIMIT 10;"
   ```

3. **Rollback to Last Known Good State**
   ```bash
   # Restore from backup (if available)
   # This will lose recent legitimate data
   docker exec argus-milvus milvus-backup restore --collection FaceVectors --timestamp YYYY-MM-DD
   ```

4. **Investigation & Recovery**
   - Analyze the poisoned batch for patterns.
   - Identify the source (which scraper, which investigation).
   - Check if attacker is actively targeting your collection.
   - Retrain any affected ML models.
   - Re-index the collection from clean data.
   - Implement stricter validation for that source.

---

### 💀 Scenario D: Dead Man's Switch Triggered
**Trigger:** Server wiped automatically due to missed heartbeat.

**Immediate Actions**

1. **Verify False Positive**
   - Check if you missed the heartbeat window (travel, illness, device failure).
   - Check backup infrastructure status.

2. **If Legitimate Wipe**
   - **DO NOT** attempt to recover data (it's cryptographically destroyed).
   - Activate disaster recovery plan.
   - Notify team via secure channel.

3. **If False Positive**
   - Investigate why heartbeat failed.
   - Check network connectivity from your device.
   - Verify Dead Man's Switch configuration.

4. **Prevention**
   - Set up redundant heartbeat paths (phone, laptop, trusted contact).
   - Test the heartbeat system monthly.
   - Keep timeout conservative (48h minimum).

---

## 📊 Incident Response Checklist

### Detection Phase
- [ ] Alert received and acknowledged
- [ ] Incident severity assessed
- [ ] Incident commander assigned
- [ ] Communication channel established (Signal group)

### Containment Phase
- [ ] Affected systems isolated
- [ ] Evidence preservation initiated (if needed)
- [ ] Credentials rotated
- [ ] Lockdown mode enabled

### Eradication Phase
- [ ] Root cause identified
- [ ] Malicious artifacts removed
- [ ] Vulnerabilities patched
- [ ] Systems wiped and rebuilt (if necessary)

### Recovery Phase
- [ ] Services restored from clean backups
- [ ] Monitoring enhanced
- [ ] Users notified (if data breach)
- [ ] Legal/regulatory notifications made

### Lessons Learned
- [ ] Post-incident review scheduled
- [ ] Runbook updated
- [ ] Training needs identified
- [ ] Preventive measures implemented

---

## 🛠️ Useful Commands

**Forensic Data Collection:**
```bash
# Memory dump
dd if=/dev/mem of=/tmp/ram.bin bs=1M

# Disk image (if not encrypted)
dd if=/dev/sda of=/tmp/disk.img bs=4M

# Network connections
ss -tulnp > /tmp/connections.txt

# Running processes
ps auxf > /tmp/processes.txt

# Recent logins
last -f /var/log/wtmp > /tmp/logins.txt

# Bash history
cat ~/.bash_history > /tmp/history.txt
```

**Secure Deletion:**
```bash
# Wipe a file
shred -vfz -n 3 /path/to/file

# Wipe free space
dd if=/dev/urandom of=/tmp/bigfile bs=1M
rm /tmp/bigfile

# Wipe entire partition
cryptsetup erase /dev/mapper/argus-data
```

**Network Isolation:**
```bash
# Block all traffic
iptables -P INPUT DROP
iptables -P OUTPUT DROP
iptables -P FORWARD DROP

# Allow only SSH from specific IP
iptables -A INPUT -s YOUR_IP -p tcp --dport 22 -j ACCEPT
```

---

## 📞 Communication Templates

**Internal Alert (Signal/PGP Email):**
```text
Subject: [P0] Security Incident - ARGUS-INT

Severity: P0 - Critical
Time: [Timestamp UTC]
Affected Systems: [List]
Current Status: [Containment/Eradication/Recovery]

Summary:
[Brief description of incident]

Actions Taken:
- [Action 1]
- [Action 2]

Next Steps:
- [Planned action 1]
- [Planned action 2]

Incident Commander: [Name]
Secure Channel: [Signal group / PGP keys]
```

**External Notification (Legal/Regulatory):**
> [!IMPORTANT]
> Consult legal counsel before sending.
```text
To: [Regulatory Authority]
From: [Your Organization]
Date: [Date]
Re: Data Breach Notification

[Follow jurisdiction-specific requirements]
```

---

## 🔐 Post-Incident Security Review

*To be completed within 72 hours of incident resolution.*

**Technical Review**
- How was the breach detected?
- What was the attack vector?
- What data was accessed/exfiltrated?
- How long was the attacker present?

**Process Review**
- Did monitoring detect the incident promptly?
- Was the response timely and effective?
- Were runbooks followed?
- What communication breakdowns occurred?

**Improvements**
- What technical controls failed?
- What processes need updating?
- What training is needed?
- What tools should be added?

> [!WARNING]
> **Remember:** In a true emergency, destroy first, investigate later. Data can be re-collected. Your safety and operational security cannot be recovered once compromised.
> 
> *This runbook should be printed and stored in a secure physical location. Digital copies should be encrypted and stored offline.*
