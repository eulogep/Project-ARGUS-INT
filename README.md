# 🌐 Project ARGUS-INT: Multi-Spectrum Intelligence Fusion Platform

<p align="center">
  <img src="https://via.placeholder.com/800x200/0a0a0a/00ff00?text=PROJECT+ARGUS-INT" alt="ARGUS-INT Banner"/>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Status-Active_Development_(Alpha_Core)-orange?style=for-the-badge" alt="Status"></a>
  <a href="#"><img src="https://img.shields.io/badge/Architecture-Kubernetes_/_Zero_Trust-blue?style=for-the-badge" alt="Architecture"></a>
  <a href="#"><img src="https://img.shields.io/badge/OPSEC-Tier_1_(SCIF_Ready)-red?style=for-the-badge" alt="OPSEC"></a>
  <a href="#"><img src="https://img.shields.io/badge/License-AGPL_v3-lightgrey?style=for-the-badge" alt="License"></a>
</p>

> **"OSINT is no longer about collecting data. It is about cognitive dominance, multi-INT fusion, and adversarial resilience."**

## 🌌 The Paradigm Shift: Why ARGUS-INT?

The current OSINT landscape is fragmented. Analysts are forced to juggle dozens of brittle scripts, rely on censored commercial APIs, and manually correlate data across disconnected tools (Maltego, SpiderFoot, custom Python scripts). 

**Project ARGUS-INT** is the next evolutionary step in Open Source Intelligence. It is not a "toolkit"; it is a **State-Sponsor Grade Multi-INT Fusion Platform**. 
Designed for elite Cyber Threat Intelligence (CTI) units, investigative journalists, and advanced researchers, ARGUS-INT shifts the paradigm from *manual querying* to **autonomous, AI-driven, multi-spectrum data ingestion and holographic graph correlation**.

### Core Differentiators
1. **Unrestricted & Agnostic:** No artificial ethical guardrails, no API censorship. The operator assumes full legal responsibility.
2. **Multi-INT Fusion:** Natively correlates OSINT (Surface/Deep/Dark), GEOINT (SAR/Hyperspectral), SIGINT (pDNS/BGP), and MASINT.
3. **Financial OPSEC (FinOps):** Native Monero/Lightning Network integration for untraceable procurement of proxies, APIs, and Dark Web data.
4. **Cognitive AI Swarms:** Replaces basic LLM chatbots with autonomous agent swarms capable of HUMINT pretexting, stylometric authorship attribution, and adversarial red-teaming.
5. **Zero Trust & Immutable Custody:** Air-gapped ready, hardware data-diode compatible, with cryptographic anchoring on IPFS/Bitcoin for immutable chain of custody.

---

## 📍 Current Status: Where We Are

**We are currently at the end of Phase 2 (Core Engine & Graph Integration).** 
The foundational architecture is stable. The transition from a monolithic Docker Compose setup to a distributed Kubernetes (K8s) architecture is underway. 

**What is working right now:**
* The FastAPI/Rust backend is successfully ingesting surface web and basic Dark Web (Tor) data.
* The Neo4j graph database is dynamically updating nodes and edges in real-time.
* The FinOps module can successfully execute micro-transactions via Lightning Network to unlock premium API endpoints anonymously.
* Local LLM (Ollama/Llama-3) is integrated for basic semantic parsing and PII extraction.

**Where we stopped (The immediate bottleneck):**
We are currently optimizing the **Milvus Vector DB integration for cross-lingual stylometry** and finalizing the **Kubernetes NetworkPolicies** to enforce strict Zero-Trust micro-segmentation between the "Dirty" (Collection) and "Clean" (Analysis) zones.

---

## 🗺️ Roadmap: Done vs. To Do

If you are looking to contribute, this is the exact map of the project's lifecycle.

### ✅ Phase 1 & 2: Foundation & Core Engine (COMPLETED)
- [x] **Architecture Design:** Zero-Trust micro-services architecture.
- [x] **Backend Core:** FastAPI (Python) + High-performance parsers (Rust).
- [x] **Graph Engine:** Neo4j integration with custom Cypher queries for 4D (time-travel) relationship mapping.
- [x] **FinOps Module:** Monero (XMR) and BTC Lightning wallet integration for anonymous resource procurement.
- [x] **Basic Scrapers:** Headless browser (Playwright) with TLS/Canvas spoofing and residential proxy rotation.
- [x] **OPSEC Baseline:** Mat2 metadata stripping, WebRTC/DNS leak prevention modules.

### 🚧 Phase 3: Cognitive AI & Vectorization (IN PROGRESS - *HELP NEEDED HERE*)
- [ ] **Stylometry Engine:** Fine-tuning local NLP models for cross-lingual authorship attribution.
- [ ] **Vector DB Tuning:** Optimizing Milvus for massive-scale facial and behavioral embedding searches.
- [ ] **Adversarial AI (Red Teaming):** Training the GAN module to automatically generate counter-hypotheses and challenge the investigator's graph.
- [ ] **HUMINT Swarms:** Implementing the multi-agent framework for autonomous social engineering (pretexting) on forums/Discord.

### ⏳ Phase 4: Multi-INT & Space/RF Integration (PLANNED)
- [ ] **SIGINT/pDNS Pipeline:** Integrating Apache Kafka for high-throughput passive DNS and BGP routing ingestion.
- [ ] **Astro-GEOINT:** Adding SAR (Synthetic Aperture Radar) and hyperspectral image processing pipelines.
- [ ] **SDR/RF Ingestion:** Modules for Software Defined Radio telemetry parsing (Wi-Fi/Bluetooth/IoT fingerprinting).

### 🔮 Phase 5: Hardening & Post-Quantum (FUTURE)
- [ ] **Post-Quantum Cryptography (PQC):** Migrating internal comms and data-at-rest encryption to Kyber/Dilithium standards.
- [ ] **Hardware Data Diodes:** Software simulation and hardware integration guides for strict unidirectional data flow.
- [ ] **SCIF Deployment:** Finalizing the automated air-gapped deployment scripts for Sensitive Compartmented Information Facilities.

---

## 🏗️ Architecture Overview

ARGUS-INT relies on a distributed, event-driven architecture designed for petabyte-scale processing.

```text
[ DIRTY ZONE (Collection) ]          [ DMZ / DATA DIODE ]         [ CLEAN ZONE (Analysis) ]
                                                                      
 Tor/I2P Nodes  ──┐                                                    ┌──> Neo4j (Graph)
 Surface Scrapers ─┤                                                   │
 pDNS/SIGINT    ──┼──> Apache Kafka ──> [ Sanitization ] ──> Spark ───┼──> Milvus (Vectors)
 Dark Web APIs  ──┤       (Streaming)      & Parsing       (ETL)     │
 SDR/RF Feeds   ──┘                                                    └──> ClickHouse (OLAP)
                                                                         │
[ FinOps / XMR ] ──> Autonomous Resource Procurement                     └──> Local LLM Swarm (AI)
```

---

## 🤝 Contributing: Join the Vanguard

We are looking for elite engineers, data scientists, and CTI analysts. If you want to push the boundaries of what is possible in intelligence gathering, read this carefully.

### How to Pick Up Where We Left Off
*   **Check the Issues:** Look for tags `[Phase 3]`, `[Help Wanted]`, or `[Bottleneck]`.
*   **Current Focus:** We urgently need Rust developers to optimize the pDNS packet parser, and AI researchers to help tune the Milvus vector embeddings for stylometry.
*   **Fork & Branch:** Create a branch named `feature/<module-name>` or `fix/<issue-id>`.

### 🛡️ Contributor OPSEC (Crucial)
Given the unrestricted nature of this project, we highly recommend the following for our contributors:
*   Do not use your real identity if you are contributing to the FinOps, Dark Web, or HUMINT Swarm modules.
*   Use a dedicated, anonymous GitHub/GitLab account.
*   Route your `git push` through Tor or a trusted VPN.
*   Never commit hardcoded API keys, proxy credentials, or wallet seeds. Use the `.env.example` template.

---

## 🚀 Development Environment Setup

```bash
# Clone the repository
git clone https://github.com/yourorg/argus-int.git
cd argus-int

# Configure variables
cp .env.example .env
nano .env

# Deploy local stack
docker-compose up -d
```

For full hardware requirements (GPU/VRAM for local LLMs) and Kubernetes deployment, see `docs/DEPLOYMENT.md`.

---

## 📚 Documentation

*   [Architecture Deep Dive](file:///home/euloge/Documents/Projets/PHYNX/docs/architecture.md) - Detailed breakdown of the K8s clusters and data flow.
*   [OPSEC & Provisioning Guide](file:///home/euloge/Documents/Projets/PHYNX/docs/OPSEC_PROVISIONING_GUIDE.md) - How to acquire proxies, APIs, and infrastructure without KYC.
*   [SCIF Deployment Guide](file:///home/euloge/Documents/Projets/PHYNX/docs/SCIF_DEPLOYMENT_GUIDE.md) - Air-gapped installation and data sanitization protocols.

---

## ⚖️ Legal & Ethical Disclaimer

**READ CAREFULLY:** ARGUS-INT is a sovereign, agnostic intelligence platform. It is designed for authorized Cyber Threat Intelligence (CTI), law enforcement, investigative journalism, and academic research.

*   **No Artificial Guardrails:** This software does not restrict queries based on Terms of Service (ToS) or local laws. It is a neutral instrument.
*   **Operator Responsibility:** The developers assume no liability for the actions of the operators. It is the sole responsibility of the user to ensure their intelligence gathering activities comply with the laws of their jurisdiction (e.g., GDPR, CFAA, local privacy laws).
*   **Do No Harm:** This tool is for intelligence gathering and analysis, not for active exploitation, kinetic attacks, or unauthorized system compromise.

<p align="center">
<b>"Information is power. Fusion is dominance."</b><br>
<i>Project ARGUS-INT Core Team</i>
</p>
