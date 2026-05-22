# ==============================================================================
# Project ARGUS-INT - Multi-Spectrum Intelligence Fusion Platform
# ==============================================================================
# Copyright (C) 2026 eulogep
#
# This file is part of Project ARGUS-INT.
#
# Project ARGUS-INT is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Project ARGUS-INT is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Project ARGUS-INT. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================

"""
ARGUS-INT — GraphService : Interface Neo4j
backend/app/services/graph.py

Encapsule toutes les interactions avec Neo4j (neo4j-driver).
"""

import logging
from typing import Optional
from neo4j import GraphDatabase, Driver
from app.config import settings
from app.utils.resilience import neo4j_retry

logger = logging.getLogger(__name__)


class GraphService:
    """
    Service singleton pour l'accès à Neo4j.
    Utilise le driver officiel Python (bolt://).
    """
    _driver: Optional[Driver] = None

    def __init__(self):
        if not GraphService._driver:
            GraphService._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_pool_size=50,
            )

    @property
    def driver(self) -> Driver:
        return GraphService._driver

    def close(self):
        if GraphService._driver:
            GraphService._driver.close()
            GraphService._driver = None

    # ─────────────────────────────────────────────────────────────
    #  UPSERT NODE
    # ─────────────────────────────────────────────────────────────

    @neo4j_retry
    def upsert_node(self, label: str, properties: dict) -> dict:
        """
        Crée ou met à jour un nœud Neo4j.
        L'uid est la clé d'idempotence.

        Cypher généré :
            MERGE (n:Label {uid: $uid})
            SET n += $props
            RETURN n
        """
        uid = properties.get("uid")
        if not uid:
            raise ValueError("Le nœud doit avoir un champ 'uid'")

        query = f"""
        MERGE (n:{label} {{uid: $uid}})
        SET n += $props
        SET n.last_seen = datetime()
        RETURN n
        """
        with self.driver.session() as session:
            result = session.run(query, uid=uid, props=properties)
            record = result.single()
            if record:
                return dict(record["n"])
        return properties

    # ─────────────────────────────────────────────────────────────
    #  UPSERT RELATION
    # ─────────────────────────────────────────────────────────────

    @neo4j_retry
    def upsert_relation(
        self,
        from_uid: str,
        to_uid: str,
        relation_type: str,
        properties: Optional[dict] = None
    ) -> bool:
        """
        Crée ou met à jour une relation entre deux nœuds.
        Idempotent grâce à MERGE.
        """
        props = properties or {}
        query = f"""
        MATCH (a {{uid: $from_uid}})
        MATCH (b {{uid: $to_uid}})
        MERGE (a)-[r:{relation_type}]->(b)
        SET r += $props
        SET r.last_updated = datetime()
        RETURN r
        """
        with self.driver.session() as session:
            result = session.run(
                query,
                from_uid=from_uid,
                to_uid=to_uid,
                props=props
            )
            return result.single() is not None

    # ─────────────────────────────────────────────────────────────
    #  SUGGESTIONS DE PIVOTS (Auto-OSINT)
    # ─────────────────────────────────────────────────────────────

    @neo4j_retry
    def get_pivot_suggestions(self, uid: str, max_depth: int = 2) -> list[dict]:
        """
        Suggère automatiquement les prochains pivots d'investigation
        basés sur les voisins du graphe et leur score d'importance.

        Algorithme :
        - Nœuds avec beaucoup de connexions = fort potentiel de pivot
        - Score = degré × confiance moyenne des relations
        """
        query = """
        MATCH (n {uid: $uid})-[r*1..$depth]-(neighbor)
        WHERE neighbor.uid <> $uid
        WITH neighbor,
             COUNT(r) as path_count,
             AVG(r[-1].confidence) as avg_confidence
        WHERE avg_confidence IS NOT NULL
        RETURN
            neighbor.uid as uid,
            labels(neighbor)[0] as entity_type,
            neighbor as properties,
            path_count * avg_confidence as pivot_score
        ORDER BY pivot_score DESC
        LIMIT 10
        """
        with self.driver.session() as session:
            result = session.run(query, uid=uid, depth=max_depth)
            return [
                {
                    "uid": r["uid"],
                    "entity_type": r["entity_type"],
                    "pivot_score": round(r["pivot_score"], 3),
                    "properties": dict(r["properties"])
                }
                for r in result
            ]

    # ─────────────────────────────────────────────────────────────
    #  EXPORT GRAPHE
    # ─────────────────────────────────────────────────────────────

    @neo4j_retry
    def export_investigation_graph(self, investigation_id: str) -> dict:
        """
        Exporte tous les nœuds et relations d'une investigation.
        Format : {nodes: [...], edges: [...]} compatible D3.js / vis.js
        """
        query = """
        MATCH (n {investigation_id: $inv_id})
        OPTIONAL MATCH (n)-[r]-(m {investigation_id: $inv_id})
        RETURN
            collect(DISTINCT {
                id: n.uid,
                label: labels(n)[0],
                data: properties(n)
            }) as nodes,
            collect(DISTINCT {
                source: startNode(r).uid,
                target: endNode(r).uid,
                type: type(r),
                data: properties(r)
            }) as edges
        """
        with self.driver.session() as session:
            result = session.run(query, inv_id=investigation_id)
            record = result.single()
            if record:
                return {
                    "nodes": record["nodes"],
                    "edges": [e for e in record["edges"] if e["source"] and e["target"]]
                }
        return {"nodes": [], "edges": []}

    # ─────────────────────────────────────────────────────────────
    #  INITIALISATION DES CONTRAINTES
    # ─────────────────────────────────────────────────────────────

    def initialize_schema(self):
        """Crée les index et contraintes d'unicité au démarrage."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Email) REQUIRE n.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Username) REQUIRE n.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:SocialProfile) REQUIRE n.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:OnlineService) REQUIRE n.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Domain) REQUIRE n.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:IPAddress) REQUIRE n.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:CryptoWallet) REQUIRE n.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Person) REQUIRE n.uid IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (n:SocialProfile) ON (n.platform)",
            "CREATE INDEX IF NOT EXISTS FOR (n:OnlineService) ON (n.service)",
        ]
        with self.driver.session() as session:
            for constraint in constraints:
                session.run(constraint)
        logger.info("[GraphService] Schéma Neo4j initialisé")
