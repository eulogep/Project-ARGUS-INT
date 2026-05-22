# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Celery Vision Tasks (queue: gpu-light / gpu-heavy)
backend/app/tasks/vision.py

Tâches asynchrones pour le pipeline Vision :
  run_face_clustering    → gpu-heavy (InsightFace + DBSCAN)
  run_object_detection   → gpu-light (YOLOv8)
  run_clip_indexing      → gpu-light (OpenCLIP)
  run_full_image_analysis → gpu-heavy (tout en un)
"""
from __future__ import annotations

from typing import Any

import structlog
from celery import Task

from app.celery_app import celery_app
from app.middleware.ai_firewall import firewall_protected

logger = structlog.get_logger(__name__)


class GPUTask(Task):
    """Base task qui libère la VRAM après exécution."""
    abstract = True

    def after_return(self, *args: Any, **kwargs: Any) -> None:
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass


@celery_app.task(
    bind=True,
    base=GPUTask,
    name="app.tasks.vision.run_face_clustering",
    queue="gpu-heavy",
    soft_time_limit=600,
    time_limit=900,
    max_retries=2,
)
def run_face_clustering(
    self: Task,
    investigation_id: str,
    image_paths: list[str],
    platform: str = "unknown",
    source_urls: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Extrait les embeddings faciaux des images et les indexe dans Milvus.
    Lance ensuite le clustering DBSCAN sur l'investigation complète.
    """
    logger.info("vision.face_clustering.start", investigation=investigation_id, images=len(image_paths))
    try:
        from app.services.vision.face_cluster import FaceClusterPipeline
        pipeline = FaceClusterPipeline(investigation_id)
        embeddings = pipeline.extract_from_images(image_paths, batch_size=16)
        indexed = pipeline.index_to_milvus(embeddings, source_urls, platform)
        clusters = pipeline.cluster_investigation()
        result = {
            "status":       "completed",
            "faces_found":  len(embeddings),
            "faces_indexed": indexed,
            "clusters":     clusters,
            "investigation_id": investigation_id,
        }
        logger.info("vision.face_clustering.done", **{k: v for k, v in result.items() if k != "clusters"})
        return result
    except Exception as exc:
        logger.error("vision.face_clustering.failed", investigation=investigation_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(
    bind=True,
    base=GPUTask,
    name="app.tasks.vision.run_object_detection",
    queue="gpu-light",
    soft_time_limit=300,
    time_limit=600,
    max_retries=2,
)
def run_object_detection(
    self: Task,
    investigation_id: str,
    image_paths: list[str],
    min_confidence: float = 0.35,
) -> dict[str, Any]:
    """Détecte les objets dans une liste d'images (YOLOv8)."""
    logger.info("vision.detection.start", investigation=investigation_id, images=len(image_paths))
    try:
        from app.services.vision.detector import ObjectDetector
        detector = ObjectDetector.get_instance()
        detections_raw = detector.detect_batch(image_paths, min_confidence=min_confidence)
        # Sérialiser pour Celery (JSON)
        detections = {path: [d.to_dict() for d in dets] for path, dets in detections_raw.items()}
        sensitive_count = sum(
            1 for dets in detections_raw.values()
            for d in dets if d.is_sensitive
        )
        result = {
            "status":          "completed",
            "images_processed": len(image_paths),
            "sensitive_objects": sensitive_count,
            "detections":      detections,
            "investigation_id": investigation_id,
        }
        logger.info("vision.detection.done", investigation=investigation_id, sensitive=sensitive_count)
        return result
    except Exception as exc:
        logger.error("vision.detection.failed", investigation=investigation_id, error=str(exc))
        raise self.retry(exc=exc, countdown=15)


@celery_app.task(
    bind=True,
    base=GPUTask,
    name="app.tasks.vision.run_clip_indexing",
    queue="gpu-light",
    soft_time_limit=300,
    time_limit=600,
    max_retries=2,
)
def run_clip_indexing(
    self: Task,
    investigation_id: str,
    image_paths: list[str],
    source_urls: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Indexe une liste d'images dans Milvus CLIPVectors pour recherche sémantique."""
    logger.info("vision.clip_indexing.start", investigation=investigation_id, images=len(image_paths))
    try:
        from app.services.vision.clip_search import CLIPSearchEngine
        engine = CLIPSearchEngine(investigation_id)
        indexed = engine.index_images(image_paths, source_urls, batch_size=16)
        result = {
            "status":      "completed",
            "indexed":     indexed,
            "investigation_id": investigation_id,
        }
        logger.info("vision.clip_indexing.done", investigation=investigation_id, indexed=indexed)
        return result
    except Exception as exc:
        logger.error("vision.clip_indexing.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=15)


@celery_app.task(
    bind=True,
    base=GPUTask,
    name="app.tasks.vision.run_full_image_analysis",
    queue="gpu-heavy",
    soft_time_limit=900,
    time_limit=1200,
    max_retries=1,
)
def run_full_image_analysis(
    self: Task,
    investigation_id: str,
    image_paths: list[str],
    platform: str = "unknown",
) -> dict[str, Any]:
    """
    Analyse complète d'un lot d'images :
    1. Détection d'objets (YOLOv8)
    2. Extraction faciale + indexation Milvus (InsightFace)
    3. Indexation sémantique (CLIP)
    4. OCR intelligence (PaddleOCR)
    """
    logger.info("vision.full_analysis.start", investigation=investigation_id, images=len(image_paths))
    results: dict[str, Any] = {"investigation_id": investigation_id, "status": "completed"}
    errors: list[str] = []

    # 1. Détection objets
    try:
        from app.services.vision.detector import ObjectDetector
        detector = ObjectDetector.get_instance()
        detections_raw = detector.detect_batch(image_paths)
        results["detections"] = {p: [d.to_dict() for d in dets] for p, dets in detections_raw.items()}
        results["sensitive_objects"] = sum(1 for dets in detections_raw.values() for d in dets if d.is_sensitive)
    except Exception as exc:
        errors.append(f"detection: {exc}")

    # 2. Faces
    try:
        from app.services.vision.face_cluster import FaceClusterPipeline
        fp = FaceClusterPipeline(investigation_id)
        embs = fp.extract_from_images(image_paths)
        results["faces_indexed"] = fp.index_to_milvus(embs, platform=platform)
    except Exception as exc:
        errors.append(f"faces: {exc}")

    # 3. CLIP
    try:
        from app.services.vision.clip_search import CLIPSearchEngine
        engine = CLIPSearchEngine(investigation_id)
        results["clip_indexed"] = engine.index_images(image_paths)
    except Exception as exc:
        errors.append(f"clip: {exc}")

    # 4. OCR
    try:
        from app.services.vision.ocr_intel import OCRIntelPipeline
        ocr = OCRIntelPipeline()
        ocr_results = ocr.analyze_batch(image_paths)
        results["ocr"] = {p: r.to_dict() if r else None for p, r in ocr_results.items()}
    except Exception as exc:
        errors.append(f"ocr: {exc}")

    if errors:
        results["warnings"] = errors

    logger.info("vision.full_analysis.done", investigation=investigation_id, errors=len(errors))
    return results
