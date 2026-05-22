# Foire Aux Questions (FAQ)

### 1. Pourquoi utiliser des modèles locaux (vLLM) plutôt que l'API d'OpenAI ?
Pour garantir l'OPSEC absolue. Dans le cadre d'investigations sensibles, l'envoi de données vers des serveurs tiers expose l'analyste et ses cibles. ARGUS-INT traite tout localement, garantissant une souveraineté de la donnée à 100%.

### 2. Mon serveur a "kernel panic" mystérieusement après 2 jours d'inactivité, pourquoi ?
C'est le système de **Dead Man's Switch**. S'il ne reçoit pas de ping API (`/api/v1/system/heartbeat`) avec une signature HMAC valide sous 48h, l'infrastructure d'auto-protection efface les clés LUKS de la RAM et provoque le crash du serveur pour prévenir toute saisie. Redémarrez et insérez la passphrase pour restaurer.

### 3. ARGUS-INT est-il légal ?
L'outil en lui-même est un logiciel neutre (Framework d'analyse). L'usage que vous en faites (extraction d'identités, OSINT de masse) est soumis aux lois de votre juridiction (RGPD en Europe, CFAA aux USA, etc.). Vous êtes responsable de vos cibles.
