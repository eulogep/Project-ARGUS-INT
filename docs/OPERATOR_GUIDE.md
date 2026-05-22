# ARGUS-INT : OPERATOR GUIDE

Manuel d'utilisation pour les analystes CTI et opérateurs HUMINT.

---

## 1. Création d'une Investigation
1. Allez dans le tableau de bord.
2. Cliquez sur **Nouvelle Investigation**.
3. Définissez le point d'entrée (Numéro de téléphone, Pseudo, Email).
4. Le graphe Neo4j s'ouvre. Utilisez le clic droit sur un nœud pour déployer les essaims (Swarms) dessus.

## 2. Interprétation du Graphe
- **Nœuds Rouges** : Identités compromises (Leak).
- **Nœuds Bleus** : Infrastructure (IP, Domaines).
- **Requête Cypher Courante** :
  Trouver le chemin le plus court entre deux cibles :
  ```cypher
  MATCH (p1:Person {name: "Cible A"}), (p2:Person {name: "Cible B"}),
  p = shortestPath((p1)-[*..5]-(p2))
  RETURN p
  ```

## 3. Module HUMINT (Pretexting)
1. Demandez la création d'un persona dans l'onglet **HUMINT**.
2. Soumettez un corpus textuel de la cible (pour l'analyse stylométrique).
3. L'IA générera un brouillon. **Il est obligatoire qu'un opérateur humain valide le brouillon** (HITL).
4. L'envoi se fera toujours via le réseau Tor/SOCKS5 (ProxyRouter).

## 4. Procédures d'Urgence
En cas d'urgence, référez-vous au document `INCIDENT_RESPONSE.md`.
- **Panic Wipe** : Accessible via API cachée ou `nuke.sh`.
- **Dead Man's Switch** : Nécessite une validation manuelle toutes les 48h.
