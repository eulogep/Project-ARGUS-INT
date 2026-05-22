# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Face Clustering Pipeline : InsightFace (ArcFace 512d) + DBSCAN
backend/app/services/vision/face_cluster.py

Pipeline :
  Image → InsightFace (détection + ArcFace embedding 512d)
  → Milvus FaceVectors (partitionné par investigation_id)
  → DBSCAN clustering cross-images → Groupes de visages identiques
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Optional

import numpy as np
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

_INSIGHTFACE_MODEL_PATH = os.getenv("INSIGHTFACE_MODEL_PATH", "/models/vision/insightface")
_FACE_COLLECTION = "phynx_face_vectors"
_FACE_DIM = 512


class FaceEmbedding:
    """Embedding facial extrait par ArcFace."""
    __slots__ = ("image_path", "image_hash", "bbox", "det_score", "embedding", "entity_uid")

    def __init__(
        self,
        image_path: str,
        bbox: list[float],
        det_score: float,
        embedding: list[float],
        entity_uid: Optional[str] = None,
    ) -> None:
        self.image_path = image_path
        self.image_hash = hashlib.sha256(Path(image_path).read_bytes()).hexdigest()[:16] if Path(image_path).exists() else "unknown"
        self.bbox = bbox
        self.det_score = round(det_score, 4)
        self.embedding = embedding
        self.entity_uid = entity_uid

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_path": self.image_path,
            "image_hash": self.image_hash,
            "bbox":       self.bbox,
            "det_score":  self.det_score,
            "entity_uid": self.entity_uid,
        }


class FaceClusterPipeline:
    """
    Pipeline complet : extraction → indexation Milvus → clustering DBSCAN.

    Usage :
        pipeline = FaceClusterPipeline(investigation_id="inv-abc")
        embeddings = pipeline.extract_from_images(["/tmp/a.jpg", "/tmp/b.jpg"])
        pipeline.index_to_milvus(embeddings)
        clusters = pipeline.cluster_investigation()
    """

    def __init__(self, investigation_id: str) -> None:
        self.investigation_id = investigation_id
        self._app: Any = None

    def _get_insightface_app(self) -> Any:
        """Charge InsightFace en singleton (lazy)."""
        if self._app is not None:
            return self._app
        try:
            import insightface
            from insightface.app import FaceAnalysis
            os.environ["INSIGHTFACE_HOME"] = _INSIGHTFACE_MODEL_PATH
            self._app = FaceAnalysis(
                name="buffalo_l",
                root=_INSIGHTFACE_MODEL_PATH,
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )
            self._app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("face_cluster.insightface_loaded", model_path=_INSIGHTFACE_MODEL_PATH)
        except Exception as exc:
            logger.error("face_cluster.insightface_load_failed", error=str(exc))
            self._app = None
        return self._app

    def extract_from_image(self, image_path: str) -> list[FaceEmbedding]:
        """Extrait tous les embeddings faciaux d'une image."""
        app = self._get_insightface_app()
        if app is None:
            return []
        try:
            import cv2
            img = cv2.imread(image_path)
            if img is None:
                logger.warning("face_cluster.image_unreadable", path=image_path)
                return []
            faces = app.get(img)
            embeddings: list[FaceEmbedding] = []
            for face in faces:
                if face.det_score < 0.65:  # Filtre basse qualité
                    continue
                bbox = face.bbox.tolist()
                emb = face.normed_embedding.tolist()  # ArcFace normalisé L2
                embeddings.append(FaceEmbedding(image_path, bbox, float(face.det_score), emb))
            logger.debug("face_cluster.extracted", path=image_path, faces=len(embeddings))
            return embeddings
        except Exception as exc:
            logger.error("face_cluster.extract_failed", path=image_path, error=str(exc))
            return []

    def extract_from_images(
        self,
        image_paths: list[str],
        batch_size: int = 16,
    ) -> list[FaceEmbedding]:
        """Extraction batch depuis une liste d'images."""
        import torch
        all_embeddings: list[FaceEmbedding] = []
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i : i + batch_size]
            for path in batch:
                all_embeddings.extend(self.extract_from_image(path))
            # Libération VRAM entre batches
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        logger.info("face_cluster.batch_done", total_faces=len(all_embeddings), images=len(image_paths))
        return all_embeddings

    def index_to_milvus(
        self,
        embeddings: list[FaceEmbedding],
        source_url_map: Optional[dict[str, str]] = None,
        platform: str = "unknown",
    ) -> int:
        """
        Indexe les embeddings dans Milvus (collection FaceVectors).
        Partitionné par investigation_id pour isolation logique.
        Retourne le nombre d'embeddings indexés.
        """
        if not embeddings:
            return 0
        try:
            from pymilvus import Collection, connections
            connections.connect("default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
            col = Collection(_FACE_COLLECTION)
            records = []
            for emb in embeddings:
                source_url = (source_url_map or {}).get(emb.image_path, emb.image_path)
                records.append({
                    "entity_uid":       emb.entity_uid or f"face_{emb.image_hash}",
                    "image_hash":       emb.image_hash,
                    "source_url":       source_url[:500],
                    "platform":         platform,
                    "investigation_id": self.investigation_id,
                    "vector":           emb.embedding,
                })
            col.insert(records)
            col.flush()
            logger.info("face_cluster.indexed", count=len(records), investigation=self.investigation_id)
            return len(records)
        except Exception as exc:
            logger.error("face_cluster.milvus_index_failed", error=str(exc))
            return 0

    def cluster_investigation(
        self,
        eps: float = 0.35,
        min_samples: int = 2,
        top_k_search: int = 500,
    ) -> list[dict[str, Any]]:
        """
        Charge tous les vecteurs de l'investigation et applique DBSCAN.
        Retourne les groupes de visages similaires (même identité probable).

        eps=0.35 correspond à ~0.75 similarité cosinus (1-cos → L2)
        """
        try:
            from pymilvus import Collection, connections
            from sklearn.cluster import DBSCAN
            connections.connect("default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
            col = Collection(_FACE_COLLECTION)
            # Récupère tous les vecteurs de cette investigation
            results = col.query(
                expr=f'investigation_id == "{self.investigation_id}"',
                output_fields=["entity_uid", "image_hash", "source_url", "platform", "vector"],
                limit=top_k_search,
            )
            if len(results) < 2:
                return []
            vectors = np.array([r["vector"] for r in results], dtype=np.float32)
            # DBSCAN sur les distances L2 (embeddings déjà normalisés)
            db = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean", n_jobs=-1)
            labels = db.fit_predict(vectors)
            # Groupement par cluster
            clusters: dict[int, list[dict]] = {}
            for idx, label in enumerate(labels):
                if label == -1:  # Bruit (visage unique)
                    continue
                clusters.setdefault(label, []).append(results[idx])
            output = []
            for cluster_id, members in clusters.items():
                output.append({
                    "cluster_id":   cluster_id,
                    "size":         len(members),
                    "members":      [{"entity_uid": m["entity_uid"], "source_url": m["source_url"], "platform": m["platform"]} for m in members],
                    "confidence":   "HIGH" if len(members) >= 3 else "MEDIUM",
                })
            logger.info("face_cluster.clustered", clusters=len(output), investigation=self.investigation_id)
            return sorted(output, key=lambda c: c["size"], reverse=True)
        except Exception as exc:
            logger.error("face_cluster.cluster_failed", error=str(exc))
            return []
