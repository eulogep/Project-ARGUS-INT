# ARGUS-INT : PRE-FLIGHT CHECKLIST (50 POINTS)

Vérifiez méticuleusement ces points avant tout déploiement en production TIER-1.

### 💻 Matériel & OS
- [ ] RAM >= 64 Go pour la stack complète
- [ ] VRAM >= 24 Go (NVIDIA 3090/A10G min) pour Llama-3/Vision
- [ ] Partition `/opt/argus-data` chiffrée en LUKS
- [ ] UEFI Secure Boot activé avec signatures MOK
- [ ] SWAP désactivé (`swapoff -a`)
- [ ] Core Dumps désactivés (`ulimit -c 0`)
- [ ] `/tmp` et `/var/crash` montés en tmpfs (RAM)
- [ ] Kernel durci (AppArmor profilé)

### 🔌 Réseau & Firewall
- [ ] UFW activé (deny all par défaut)
- [ ] Port 22 (SSH) restreint à des IPs de confiance
- [ ] Port 443 ouvert pour le Frontend
- [ ] Certificats TLS valides (pas d'auto-signé en externe)
- [ ] Serveur DNS OPSEC (Pi-Hole ou DNS Over HTTPS)

### 🛡️ Sécurité & OPSEC
- [ ] Fichiers `.env` en permission 600
- [ ] Mots de passe par défaut changés
- [ ] Honeytokens (`deception.py`) déployés dans les env vars
- [ ] ProxyRouter Tor testé et fonctionnel
- [ ] Dead Man's Switch activé (timer 48h)
- [ ] Panic Wipe (`nuke.sh`) testé en staging
- [ ] Utilisateur `root` désactivé pour SSH (`PermitRootLogin no`)
- [ ] Connexion SSH par clés Ed25519 uniquement

*(La liste exhaustive des 50 points est documentée dans les standards internes)*
