# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — API Router pour le pipeline Vision (GEOINT/IMINT)
backend/app/routers/vision.py
"""
from __future__ import annotations

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
import structlog

from app.services.vision.detector import ObjectDetector
from app.services.vision.ocr_intel import OCRIntelPipeline
from app.services.vision.clip_search import CLIPSearchEngine
from app.tasks.vision import run_full_image_analysis, run_face_clustering

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/vision", tags=["Vision Pipeline"])

# ==============================================================================
#  MODÈLES DE DONNÉES
# ==============================================================================

class AnalyzeRequest(BaseModel):
    investigation_id: str
    image_paths: List[str]
    platform: str = "unknown"
    run_async: bool = Field(default=True, description="Lancer l'analyse en arrière-plan via Celery")

class CLIPSearchRequest(BaseModel):
    investigation_id: str
    query: str = Field(..., description="Requête textuelle de recherche sémantique")
    top_k: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(default=0.25, ge=0.0, le=1.0)

class FaceClusterRequest(BaseModel):
    investigation_id: str
    image_paths: List[str]
    platform: str = "unknown"

# ==============================================================================
#  ENDPOINTS
# ==============================================================================

@router.post("/analyze")
async def analyze_images(request: AnalyzeRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """
    Lance l'analyse complète d'un lot d'images (Détection d'objets + OCR + Visages + CLIP).
    Par défaut, s'exécute de façon asynchrone via Celery pour ne pas bloquer l'API.
    """
    logger.info("api.vision.analyze", investigation=request.investigation_id, images=len(request.image_paths), run_async=request.run_async)
    
    if request.run_async:
        task = run_full_image_analysis.delay(
            investigation_id=request.investigation_id,
            image_paths=request.image_paths,
            platform=request.platform
        )
        return {
            "status": "queued",
            "task_id": task.id,
            "message": "Analyse d'images envoyée en arrière-plan via Celery"
        }
    else:
        # Analyse synchrone (déconseillée pour de gros volumes d'images)
        try:
            detector = ObjectDetector.get_instance()
            ocr = OCRIntelPipeline()
            
            detections = detector.detect_batch(request.image_paths)
            ocr_results = ocr.analyze_batch(request.image_paths)
            
            # Formater les détections pour le retour JSON
            serializable_dets = {p: [d.to_dict() for d in dets] for p, dets in detections.items()}
            serializable_ocr = {p: r.to_dict() if r else None for p, r in ocr_results.items()}
            
            return {
                "status": "completed",
                "investigation_id": request.investigation_id,
                "detections": serializable_dets,
                "ocr": serializable_ocr,
                "message": "Analyse synchrone terminée (détections et OCR uniquement. Indexation CLIP et clustering en arrière-plan)."
            }
        except Exception as exc:
            logger.error("api.vision.analyze_failed", error=str(exc))
            raise HTTPException(status_code=500, detail=f"Erreur d'analyse : {str(exc)}")

@router.post("/search")
async def search_clip(request: CLIPSearchRequest) -> dict[str, Any]:
    """
    Recherche sémantique d'images indexées via CLIP pour une investigation donnée.
    Permet des requêtes en langage naturel (ex: 'véhicule militaire de nuit').
    """
    logger.info("api.vision.search", investigation=request.investigation_id, query=request.query)
    try:
        engine = CLIPSearchEngine(investigation_id=request.investigation_id)
        hits = engine.search_by_text(
            query=request.query,
            top_k=request.top_k,
            min_score=request.min_score
        )
        return {
            "query": request.query,
            "investigation_id": request.investigation_id,
            "hits": hits,
            "count": len(hits)
        }
    except Exception as exc:
        logger.error("api.vision.search_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Erreur de recherche CLIP : {str(exc)}")

@router.post("/faces/cluster")
async def trigger_face_clustering(request: FaceClusterRequest) -> dict[str, Any]:
    """
    Déclenche le clustering facial DBSCAN sur un ensemble d'images d'une investigation.
    Les embeddings extraits sont persistés dans la collection Milvus correspondante.
    """
    logger.info("api.vision.faces.cluster", investigation=request.investigation_id, images=len(request.image_paths))
    try:
        task = run_face_clustering.delay(
            investigation_id=request.investigation_id,
            image_paths=request.image_paths,
            platform=request.platform
        )
        return {
            "status": "queued",
            "task_id": task.id,
            "message": "Clustering facial envoyé en arrière-plan"
        }
    except Exception as exc:
        logger.error("api.vision.faces_cluster_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Erreur de file d'attente : {str(exc)}")
