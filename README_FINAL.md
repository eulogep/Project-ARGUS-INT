# ARGUS-INT : Sovereign Cyber Threat Intelligence

![Version](https://img.shields.io/badge/version-1.0.0--rc1-blue.svg)
![License](https://img.shields.io/badge/license-AGPLv3-green.svg)
![Security](https://img.shields.io/badge/security-audited-brightgreen.svg)

**ARGUS-INT** est un framework OSINT/CTI souverain de nouvelle génération, conçu pour les environnements de haute sécurité, les déploiements air-gapped et la lutte contre la désinformation.

## 👁️ Vision et Philosophie
Dans un monde où le Renseignement en Source Ouverte dépend de plus en plus d'API propriétaires (OpenAI, AWS), ARGUS-INT ramène l'Intelligence Artificielle à la source : **Chez vous, hors-ligne, sans télémétrie**.
- **Souveraineté** : Modèles d'IA (LLMs, Vision) hébergés localement.
- **OPSEC-First** : Architecture Zero-Trust, routage Tor/SOCKS5, Amnesic Live CD.
- **Résilience** : Panic Wipe (Destruction crypto), Dead Man's Switch, Anti-Poisoning.

## 🚀 Démarrage Rapide (Quickstart)

```bash
# 1. Cloner le dépôt et vérifier les signatures (voir VERIFICATION_GUIDE.md)
git clone https://github.com/yourorg/argus-int.git
cd argus-int

# 2. Configurer les variables d'environnement
cp .env.example .env

# 3. Lancer la plateforme (Docker requis)
docker-compose -f docker-compose.prod.yml up -d
```

## 📚 Documentation
- [Guide d'Installation](docs/INSTALLATION.md)
- [Manuel de l'Opérateur](docs/OPERATOR_GUIDE.md)
- [Procédures d'Urgence (Runbook)](docs/INCIDENT_RESPONSE.md)

## 🤝 Contribuer & Sécurité
Consultez notre [Code de Conduite](CODE_OF_CONDUCT.md) et notre politique de [Disclosure Responsable](SECURITY.md).
