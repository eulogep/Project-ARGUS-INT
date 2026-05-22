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
ARGUS-INT — Milvus Vector DB Service
backend/app/services/vector_db.py

Gère deux collections :
  1. StyleVectors  : embeddings stylistiques (788d) pour l'attribution d'auteur
  2. FaceVectors   : embeddings faciaux (512d) pour le cross-platform matching
"""

import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

STYLE_COLLECTION = "phynx_style_vectors"
FACE_COLLECTION  = "phynx_face_vectors"
STYLE_DIM = 788    # 768d embedding + 20 features scalaires
FACE_DIM  = 512    # ArcFace / InsightFace embedding


class VectorDBService:
    """
    Client Milvus pour la recherche vectorielle.
    Pattern Singleton — connexion partagée entre workers.
    """
    _client = None

    def __init__(self):
        if not VectorDBService._client:
            self._connect()

    def _connect(self):
        try:
            from pymilvus import connections, Collection, utility
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
            )
            VectorDBService._client = True
            self._ensure_collections()
            logger.info("[VectorDB] Connecté à Milvus")
        except Exception as e:
            logger.error(f"[VectorDB] Connexion Milvus échouée : {e}")
            VectorDBService._client = False

    def _ensure_collections(self):
        """Crée les collections si elles n'existent pas."""
        from pymilvus import CollectionSchema, FieldSchema, DataType, Collection, utility

        # ─── Collection Stylométrie ──────────────────────────────
        if not utility.has_collection(STYLE_COLLECTION):
            fields = [
                FieldSchema(name="id",          dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="entity_uid",  dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="pseudo",      dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="platform",    dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="text_hash",   dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="vector",      dtype=DataType.FLOAT_VECTOR, dim=STYLE_DIM),
            ]
            schema = CollectionSchema(fields, description="Vecteurs stylistiques PHYNX")
            col = Collection(STYLE_COLLECTION, schema)
            col.create_index(
                field_name="vector",
                index_params={
                    "metric_type": "COSINE",
                    "index_type": "HNSW",
                    "params": {"M": 16, "efConstruction": 200},
                }
            )
            col.load()
            logger.info(f"[VectorDB] Collection '{STYLE_COLLECTION}' créée")

        # ─── Collection Visages ──────────────────────────────────
        if not utility.has_collection(FACE_COLLECTION):
            fields = [
                FieldSchema(name="id",          dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="entity_uid",  dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="image_hash",  dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="source_url",  dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="platform",    dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="vector",      dtype=DataType.FLOAT_VECTOR, dim=FACE_DIM),
            ]
            schema = CollectionSchema(fields, description="Vecteurs faciaux PHYNX")
            col = Collection(FACE_COLLECTION, schema)
            col.create_index(
                field_name="vector",
                index_params={
                    "metric_type": "IP",   # Inner Product pour ArcFace normalisé
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 128},
                }
            )
            col.load()
            logger.info(f"[VectorDB] Collection '{FACE_COLLECTION}' créée")

    # ─────────────────────────────────────────────────────────────
    #  STYLOMÉTRIE
    # ─────────────────────────────────────────────────────────────

    def upsert_style_vector(
        self,
        entity_uid: str,
        pseudo: str,
        platform: str,
        text_hash: str,
        vector: list[float],
    ) -> bool:
        """Indexe un vecteur stylistique dans Milvus."""
        if not VectorDBService._client:
            return False
        try:
            from pymilvus import Collection
            col = Collection(STYLE_COLLECTION)
            col.insert([{
                "entity_uid": entity_uid,
                "pseudo":     pseudo,
                "platform":   platform,
                "text_hash":  text_hash,
                "vector":     vector,
            }])
            col.flush()
            return True
        except Exception as e:
            logger.error(f"[VectorDB] Erreur upsert style : {e}")
            return False

    def search_similar_style(
        self,
        query_vector: list[float],
        top_k: int = 10,
        min_similarity: float = 0.82,
        exclude_entity: Optional[str] = None,
    ) -> list[dict]:
        """
        Recherche les entités au style similaire.
        Seuil 0.82 = très forte probabilité d'être le même auteur.
        Seuil 0.70 = style similaire, possible même individu.
        """
        if not VectorDBService._client:
            return []
        try:
            from pymilvus import Collection
            col = Collection(STYLE_COLLECTION)
            results = col.search(
                data=[query_vector],
                anns_field="vector",
                param={"metric_type": "COSINE", "params": {"ef": 64}},
                limit=top_k + 5,
                output_fields=["entity_uid", "pseudo", "platform", "text_hash"],
            )
            matches = []
            for hits in results:
                for hit in hits:
                    score = hit.score
                    if score < min_similarity:
                        continue
                    if exclude_entity and hit.entity.get("entity_uid") == exclude_entity:
                        continue
                    matches.append({
                        "entity_uid": hit.entity.get("entity_uid"),
                        "pseudo":     hit.entity.get("pseudo"),
                        "platform":   hit.entity.get("platform"),
                        "similarity": round(score, 4),
                        "confidence_label": _similarity_to_label(score),
                    })
            return matches[:top_k]
        except Exception as e:
            logger.error(f"[VectorDB] Erreur search style : {e}")
            return []

    # ─────────────────────────────────────────────────────────────
    #  RECONNAISSANCE FACIALE CROSS-PLATFORM
    # ─────────────────────────────────────────────────────────────

    def upsert_face_vector(
        self,
        entity_uid: str,
        image_hash: str,
        source_url: str,
        platform: str,
        vector: list[float],
    ) -> bool:
        """Indexe un embedding facial (ArcFace 512d) dans Milvus."""
        if not VectorDBService._client:
            return False
        try:
            from pymilvus import Collection
            col = Collection(FACE_COLLECTION)
            col.insert([{
                "entity_uid": entity_uid,
                "image_hash": image_hash,
                "source_url": source_url,
                "platform":   platform,
                "vector":     vector,
            }])
            col.flush()
            return True
        except Exception as e:
            logger.error(f"[VectorDB] Erreur upsert face : {e}")
            return False

    def search_similar_face(
        self,
        query_vector: list[float],
        top_k: int = 5,
        min_similarity: float = 0.75,
    ) -> list[dict]:
        """
        Recherche les visages similaires (cross-platform avatar matching).
        Seuil 0.75 = forte similitude faciale.
        """
        if not VectorDBService._client:
            return []
        try:
            from pymilvus import Collection
            col = Collection(FACE_COLLECTION)
            results = col.search(
                data=[query_vector],
                anns_field="vector",
                param={"metric_type": "IP", "params": {"nprobe": 16}},
                limit=top_k,
                output_fields=["entity_uid", "image_hash", "source_url", "platform"],
            )
            matches = []
            for hits in results:
                for hit in hits:
                    if hit.score >= min_similarity:
                        matches.append({
                            "entity_uid": hit.entity.get("entity_uid"),
                            "source_url": hit.entity.get("source_url"),
                            "platform":   hit.entity.get("platform"),
                            "image_hash": hit.entity.get("image_hash"),
                            "similarity": round(hit.score, 4),
                        })
            return matches
        except Exception as e:
            logger.error(f"[VectorDB] Erreur search face : {e}")
            return []


def _similarity_to_label(score: float) -> str:
    if score >= 0.92:
        return "TRÈS HAUTE — même auteur quasi-certain"
    elif score >= 0.82:
        return "HAUTE — forte probabilité même auteur"
    elif score >= 0.70:
        return "MODÉRÉE — style similaire, possible même individu"
    else:
        return "FAIBLE — style vaguement similaire"


def extract_face_embedding(image_path: str) -> Optional[list[float]]:
    """
    Extrait un embedding facial via InsightFace (ArcFace).
    Retourne None si aucun visage détecté.
    """
    try:
        import cv2
        import insightface
        from insightface.app import FaceAnalysis

        app = FaceAnalysis(providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=0, det_size=(640, 640))

        img = cv2.imread(image_path)
        if img is None:
            return None

        faces = app.get(img)
        if not faces:
            logger.debug(f"[VectorDB] Aucun visage détecté dans {image_path}")
            return None

        # Prendre le visage avec le plus grand bbox (visage principal)
        main_face = max(faces, key=lambda f: f.det_score)
        return main_face.embedding.tolist()

    except ImportError:
        logger.warning("[VectorDB] InsightFace non installé")
        return None
    except Exception as e:
        logger.error(f"[VectorDB] Erreur extraction faciale : {e}")
        return None
