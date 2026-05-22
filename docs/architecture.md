# PHYNX — Framework OSINT Full-Spectrum

## Vue d'ensemble

PHYNX est un framework OSINT modulaire, souverain et sans restriction, conçu pour la Cyber Threat Intelligence (CTI). Il opère sur la Surface Web, le Deep Web et le Dark Web, avec une architecture micro-services entièrement conteneurisée.

---

## Diagramme d'Architecture Global

```
┌─────────────────────────────────────────────────────────────────────┐
│                          PHYNX CORE PLATFORM                        │
│                                                                     │
│  ┌──────────┐   ┌──────────────────────────────────────────────┐   │
│  │  CLI     │   │              FRONTEND (Next.js)              │   │
│  │ (Typer)  │   │  Graph View │ Guided Mode │ Expert Terminal  │   │
│  └────┬─────┘   └─────────────────────┬────────────────────────┘   │
│       │                               │                             │
│       └───────────────┬───────────────┘                             │
│                       ▼                                             │
│            ┌─────────────────────┐                                  │
│            │   FastAPI Gateway   │  ← Auth / Rate-limit / Router   │
│            └──────────┬──────────┘                                  │
│                       │                                             │
│         ┌─────────────┼─────────────┐                               │
│         ▼             ▼             ▼                               │
│  ┌─────────────┐ ┌─────────┐ ┌───────────┐                         │
│  │Celery Worker│ │Celery   │ │Celery     │  ← Tâches async         │
│  │ (OSINT)     │ │Worker   │ │Worker     │                         │
│  │             │ │(GEOINT) │ │(Tech Recon│                         │
│  └──────┬──────┘ └────┬────┘ └─────┬─────┘                         │
│         │             │            │                                │
│         └─────────────┼────────────┘                                │
│                       ▼                                             │
│         ┌─────────────────────────┐                                 │
│         │      Redis (Queue)      │ ← Broker Celery + Cache        │
│         └─────────────────────────┘                                 │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────┐ │
│  │  PostgreSQL  │ │    Neo4j     │ │   Redis    │ │Elasticsearch│ │
│  │ (Relations)  │ │  (Graphe)    │ │  (Cache)   │ │  (Full-text)│ │
│  └──────────────┘ └──────────────┘ └────────────┘ └─────────────┘ │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │               MODULES CONTENEURISÉS (Plugins)                │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │  │
│  │  │ Identity │ │  Breach  │ │ Dark Web │ │  GEOINT/IMINT │  │  │
│  │  │ Resolver │ │ & Leaks  │ │ Scraper  │ │               │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │  │
│  │  │   Tech   │ │ Crypto / │ │  LLM     │ │   ArchiveBox  │  │  │
│  │  │  Recon   │ │Blockchain│ │  Local   │ │  + Hasher     │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Flux de Données Détaillé

```
INPUT (cible: email / pseudo / IP / domaine / image / wallet)
  │
  ▼
[1] RESOLVER — Normalisation & typage de la cible
  │  → Détecte le type (email, IP, phone, domain, username, hash...)
  │  → Génère les variantes (aliases, permutations)
  ▼
[2] DISPATCHER (FastAPI → Celery)
  │  → Sélectionne les modules pertinents selon le type de cible
  │  → Injecte dans la queue Redis avec priorité et profondeur
  ▼
[3] COLLECTE PARALLÈLE (Workers Celery)
  │
  ├──► Module IDENTITY   → Sherlock+, Holehe, Epieos, phonebook.cz
  ├──► Module BREACH     → COMB parser, Dehashed API, IntelX, Stealer Logs
  ├──► Module DARK WEB   → Tor crawler, I2P, Telegram/Discord scrapers
  ├──► Module GEOINT     → EXIF, SunCalc, GeoSpy, Yandex Images, PimEyes
  ├──► Module TECH RECON → Amass, Subfinder, Nuclei, ffuf, Wappalyzer
  └──► Module CRYPTO     → Blockchain tracers (BTC/ETH/XMR)
  │
  ▼
[4] PARSING & ENRICHISSEMENT
  │  → Extraction d'entités (NLP / LLM local Ollama)
  │  → Normalisation des résultats bruts
  │  → Calcul de scores de confiance
  ▼
[5] CORRÉLATION — Neo4j
  │  → Création / mise à jour des nœuds
  │  → Inférence de nouvelles relations
  │  → Suggestions automatiques de pivots
  ▼
[6] ARCHIVAGE — ArchiveBox + SHA256
  │  → SingleFile capture
  │  → Horodatage certifié
  │  → Chiffrement AES-256-GCM
  ▼
[7] EXPORT
     → Rapport PDF/HTML/JSON structuré
     → Export graphe (GEXF / CSV)
     → Nettoyage métadonnées (mat2/exiftool)
```

---

## Interaction FastAPI ↔ Celery ↔ Neo4j

```
Client HTTP
    │  POST /api/v1/investigations
    ▼
FastAPI Router
    │  1. Valide & normalise la requête
    │  2. Crée une Investigation en PostgreSQL (statut: PENDING)
    │  3. Retourne investigation_id immédiatement (202 Accepted)
    │
    │  celery_app.send_task("tasks.run_module", args=[...])
    ▼
Redis Queue (broker)
    │
    ▼
Celery Worker
    │  1. Exécute le module OSINT (scraping, API call, etc.)
    │  2. Parse les résultats bruts
    │  3. Appelle graph_service.inject(entities, relations)
    │
    ▼
Neo4j (via neo4j-driver)
    │  MERGE (n:Entity {uid: $uid})
    │  SET n += $properties
    │  MERGE (a)-[:RELATION {type: $rel_type}]->(b)
    ▼
PostgreSQL
    │  UPDATE investigations SET status='DONE', result_summary=...
    ▼
FastAPI WebSocket (push)
    │  → Notification temps réel au frontend
    ▼
Frontend (Next.js)
    │  → Mise à jour du graphe D3.js / vis.js
    │  → Affichage des nouvelles entités et relations
```

---

## Modules — Description Fonctionnelle

### Module 1 : Identity Resolver
- **Outils** : Sherlock+, Blackbird, Whatsmyname (1000+ plateformes)
- **Méthode** : Requêtes HTTP asynchrones (httpx), rotation de User-Agent, délais aléatoires
- **Output** : Liste de profils confirmés + URLs + screenshots

### Module 2 : Breach & Leaks
- **Outils** : Parser COMB local, Dehashed API, Intelligence X, Stealer Logs DB
- **Méthode** : Recherche par email, domaine, IP, username dans des dumps indexés par Elasticsearch
- **Output** : Credentials, passwords, cookies, tokens

### Module 3 : Dark Web Crawler
- **Outils** : Scrapy + Tor SOCKS5, I2P HTTP proxy
- **Cibles** : Forums .onion, marchés, canaux Telegram/Discord/IRC
- **Anti-detection** : Rotation d'identités Tor (NEWNYM), délais aléatoires, circuit isolation

### Module 4 : GEOINT / IMINT
- **EXIF** : ExifTool (GPS, device, timestamps cachés)
- **Géoloc par ombres** : API SunCalc + calcul d'azimut
- **IA Vision** : GeoSpy local, reconnaissance faciale (deepface, insightface)
- **Recherche inversée** : Yandex, Baidu, Bing Visual (via Selenium furtif)

### Module 5 : Tech Recon
- **Sous-domaines** : Amass, Subfinder, CRT.sh parser
- **Scan** : Nuclei (CVE templates), ffuf (endpoints cachés)
- **Fingerprinting** : Wappalyzer, WhatWeb

### Module 6 : Crypto / Blockchain
- **Bitcoin** : Blockstream API, OXT.me
- **Ethereum** : Etherscan, The Graph Protocol
- **Monero** : Analyse heuristique (monero-lws)
- **Clustering** : Identification des wallets liés, exchanges KYC

---

## Garanties OPSEC & Anti-Scraping

### Gestion des Sessions & Proxies
- Pool de proxies SOCKS5 résidentiels avec health-check automatique (toutes les 5 min)
- Rotation intelligente : ban-detection → switch automatique
- Support Tor natif avec contrôle du circuit via ControlPort

### Fingerprint Spoofing
- Rotation User-Agent (ua-parser + listes Chromium/Firefox récentes)
- Spoofing Canvas, WebGL, AudioContext via Playwright stealth
- Délais aléatoires inter-requêtes (loi exponentielle, non-détectable)
- Résolution CAPTCHA : 2captcha, anticaptcha, CapMonster (API locale)

### Souveraineté des Données
- **Zéro cloud** : Toutes les données restent locales
- **Chiffrement au repos** : AES-256-GCM (clé dérivée PBKDF2)
- **LLM souverain** : Ollama (Llama 3 / Mistral) — aucune requête externe
- **Zéro télémétrie** : Toutes dépendances auditées, pas de callbacks externes
- **Air-gap possible** : Fonctionne sans Internet (bases locales pré-chargées)
