# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Graph Intel : Création de nœuds Neo4j depuis les résultats Vision
backend/app/services/graph_intel.py

Crée et lie les entités extraites par le pipeline Vision dans le graphe Neo4j :
  Person (visage identifié) → [:SPOTTED_IN] → Investigation
  Vehicle (plaque ou modèle) → [:SEEN_AT] → Location
  Document (ID/passeport OCR) → [:BELONGS_TO] → Person
"""
from __future__ import annotations

from typing import Any, Optional

import structlog

from app.services.graph import GraphService

logger = structlog.get_logger(__name__)


class GraphIntelService:
    """
    Extension du GraphService pour l'intégration des résultats Vision dans Neo4j.

    Usage :
        service = GraphIntelService()
        await service.upsert_face_cluster(investigation_id, cluster)
        await service.upsert_vehicle(investigation_id, plate="AB-123-CD", source_url="...")
        await service.upsert_document(investigation_id, doc_fields={...}, source_image="...")
    """

    def __init__(self) -> None:
        self._graph = GraphService()

    async def upsert_face_cluster(
        self,
        investigation_id: str,
        cluster: dict[str, Any],
    ) -> str:
        """
        Crée un nœud Person pour un cluster facial identifié.

        Args:
            investigation_id : ID de l'investigation
            cluster          : Résultat de FaceClusterPipeline.cluster_investigation()

        Returns:
            entity_uid du nœud créé
        """
        cluster_id = cluster["cluster_id"]
        entity_uid = f"face_cluster_{investigation_id}_{cluster_id}"
        sources = [m["source_url"] for m in cluster.get("members", [])]
        platforms = list({m["platform"] for m in cluster.get("members", [])})

        cypher = """
        MERGE (p:Person {entity_uid: $uid})
        SET p.face_cluster_id    = $cluster_id,
            p.sighting_count     = $count,
            p.source_platforms   = $platforms,
            p.source_urls        = $sources,
            p.confidence         = $confidence,
            p.investigation_id   = $investigation_id,
            p.updated_at         = datetime()
        WITH p
        MATCH (i:Investigation {id: $investigation_id})
        MERGE (p)-[:SPOTTED_IN]->(i)
        RETURN p.entity_uid AS uid
        """
        try:
            result = await self._graph.run_query(cypher, {
                "uid":              entity_uid,
                "cluster_id":       cluster_id,
                "count":            cluster["size"],
                "platforms":        platforms,
                "sources":          sources[:10],
                "confidence":       cluster.get("confidence", "MEDIUM"),
                "investigation_id": investigation_id,
            })
            logger.info(
                "graph_intel.face_upserted",
                entity_uid=entity_uid,
                cluster_size=cluster["size"],
                investigation=investigation_id,
            )
            return entity_uid
        except Exception as exc:
            logger.error("graph_intel.face_upsert_failed", error=str(exc))
            raise

    async def upsert_vehicle(
        self,
        investigation_id: str,
        plate: Optional[str],
        source_url: str,
        detected_class: str = "vehicle",
        confidence: float = 0.0,
    ) -> Optional[str]:
        """Crée un nœud Vehicle (plaque/modèle) dans le graphe."""
        if not plate:
            return None
        entity_uid = f"vehicle_{plate.upper().replace(' ', '')}_{investigation_id[:8]}"
        cypher = """
        MERGE (v:Vehicle {entity_uid: $uid})
        SET v.plate              = $plate,
            v.detected_class     = $class,
            v.source_url         = $source_url,
            v.detection_score    = $confidence,
            v.investigation_id   = $investigation_id,
            v.updated_at         = datetime()
        WITH v
        MATCH (i:Investigation {id: $investigation_id})
        MERGE (v)-[:SEEN_IN]->(i)
        """
        try:
            await self._graph.run_query(cypher, {
                "uid":              entity_uid,
                "plate":            plate.upper(),
                "class":            detected_class,
                "source_url":       source_url[:500],
                "confidence":       confidence,
                "investigation_id": investigation_id,
            })
            logger.info("graph_intel.vehicle_upserted", plate=plate, investigation=investigation_id)
            return entity_uid
        except Exception as exc:
            logger.error("graph_intel.vehicle_upsert_failed", error=str(exc))
            return None

    async def upsert_document(
        self,
        investigation_id: str,
        doc_fields: dict[str, str],
        source_image: str,
        doc_type: str = "unknown",
    ) -> Optional[str]:
        """Crée un nœud Document (ID, passeport) et le lie à l'investigation."""
        if not doc_fields:
            return None
        # Utiliser le nom comme identifiant partiel
        name_hint = doc_fields.get("nom", doc_fields.get("surname", "unknown"))[:30]
        entity_uid = f"doc_{doc_type}_{name_hint}_{investigation_id[:8]}".replace(" ", "_")
        cypher = """
        MERGE (d:Document {entity_uid: $uid})
        SET d.doc_type           = $doc_type,
            d.fields             = $fields,
            d.source_image       = $source_image,
            d.investigation_id   = $investigation_id,
            d.updated_at         = datetime()
        WITH d
        MATCH (i:Investigation {id: $investigation_id})
        MERGE (d)-[:FOUND_IN]->(i)
        """
        try:
            import json
            await self._graph.run_query(cypher, {
                "uid":              entity_uid,
                "doc_type":         doc_type,
                "fields":           json.dumps(doc_fields),
                "source_image":     source_image[:500],
                "investigation_id": investigation_id,
            })
            logger.info("graph_intel.document_upserted", doc_type=doc_type, investigation=investigation_id)
            return entity_uid
        except Exception as exc:
            logger.error("graph_intel.document_upsert_failed", error=str(exc))
            return None

    async def link_face_to_document(
        self,
        face_entity_uid: str,
        doc_entity_uid: str,
        confidence: float = 0.75,
    ) -> None:
        """Crée une relation [:IDENTIFIED_AS] entre un cluster facial et un document."""
        cypher = """
        MATCH (p:Person {entity_uid: $face_uid})
        MATCH (d:Document {entity_uid: $doc_uid})
        MERGE (p)-[r:IDENTIFIED_AS]->(d)
        SET r.confidence = $confidence, r.updated_at = datetime()
        """
        try:
            await self._graph.run_query(cypher, {
                "face_uid":   face_entity_uid,
                "doc_uid":    doc_entity_uid,
                "confidence": confidence,
            })
            logger.info("graph_intel.face_doc_linked", face=face_entity_uid, doc=doc_entity_uid)
        except Exception as exc:
            logger.error("graph_intel.link_failed", error=str(exc))
