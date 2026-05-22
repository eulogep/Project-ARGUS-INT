# ARGUS-INT Bug Bounty Scope

## In-Scope
Les composants suivants sont admissibles à notre programme de récompenses :
- **Backend API (FastAPI)** : Injections (SQL/Cypher), Bypass d'authentification, RCE, fuites de données.
- **Frontend (Next.js)** : XSS, CSRF, failles de gestion de session.
- **AI Firewall Middleware** : Contournement des filtres d'injection de prompts LLM.
- **Modules OSINT / Vision** : Empoisonnement du pipeline de détection d'images, SSRF via téléchargement d'avatars.
- **Infrastructure Docker** : Échappement de conteneur, fuite de variables d'environnement (`.env`).

## Out-of-Scope (NON-ÉLIGIBLES)
Les rapports concernant les éléments suivants seront rejetés :
- Attaques par Déni de Service (DoS / DDoS) volumétriques.
- Ingénierie Sociale (Phishing, Vishing) contre les mainteneurs.
- Attaques physiques sur les bureaux ou datacenters des mainteneurs.
- Vulnérabilités sans impact démontrable (ex: manque d'en-têtes HTTP de sécurité non-critiques, enumeration de version).
- Bugs dans les dépendances tierces (sauf s'ils peuvent être exploités de manière unique via notre implémentation).
