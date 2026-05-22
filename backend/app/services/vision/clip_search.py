# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — CLIP Search Engine : Recherche sémantique d'images
backend/app/services/vision/clip_search.py

Permet des requêtes naturelles type : "homme avec sac à dos rouge près d'un arrêt de bus"
Collection Milvus : argus_clip_vectors (512d COSINE HNSW)
Partitionnement par investigation_id.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Optional

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

_CLIP_MODEL_PATH = os.getenv("CLIP_MODEL_PATH", "/models/vision/clip/ViT-B-32.pt")
_CLIP_PRETRAINED = os.getenv("CLIP_PRETRAINED", "openai")
_CLIP_COLLECTION = "argus_clip_vectors"
_CLIP_DIM = 512

# Singleton modèle CLIP
_clip_model: Any = None
_clip_preprocess: Any = None
_clip_tokenizer: Any = None


def _get_clip() -> tuple[Any, Any, Any]:
    global _clip_model, _clip_preprocess, _clip_tokenizer
    if _clip_model is not None:
        return _clip_model, _clip_preprocess, _clip_tokenizer
    try:
        import open_clip
        import torch
        os.environ["HF_HUB_OFFLINE"] = "1"
        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained=_CLIP_MODEL_PATH if Path(_CLIP_MODEL_PATH).exists() else _CLIP_PRETRAINED,
        )
        tokenizer = open_clip.get_tokenizer("ViT-B-32")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device).eval()
        _clip_model, _clip_preprocess, _clip_tokenizer = model, preprocess, tokenizer
        logger.info("clip.model_loaded", device=device)
    except Exception as exc:
        logger.error("clip.load_failed", error=str(exc))
    return _clip_model, _clip_preprocess, _clip_tokenizer


class CLIPSearchEngine:
    """
    Moteur de recherche sémantique d'images via OpenCLIP.

    Usage :
        engine = CLIPSearchEngine(investigation_id="inv-abc")
        engine.index_images(["/tmp/a.jpg", "/tmp/b.jpg"])
        hits = engine.search_by_text("véhicule militaire près d'une frontière")
        hits = engine.search_by_image("/tmp/reference.jpg")
    """

    def __init__(self, investigation_id: str) -> None:
        self.investigation_id = investigation_id

    def _embed_image(self, image_path: str) -> Optional[list[float]]:
        import torch
        model, preprocess, _ = _get_clip()
        if model is None:
            return None
        try:
            from PIL import Image
            img = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0)
            device = next(model.parameters()).device
            with torch.no_grad():
                vec = model.encode_image(img.to(device))
                vec = vec / vec.norm(dim=-1, keepdim=True)
            return vec[0].cpu().tolist()
        except Exception as exc:
            logger.error("clip.embed_image_failed", path=image_path, error=str(exc))
            return None

    def _embed_text(self, text: str) -> Optional[list[float]]:
        import torch
        model, _, tokenizer = _get_clip()
        if model is None or tokenizer is None:
            return None
        try:
            tokens = tokenizer([text[:77]])
            device = next(model.parameters()).device
            with torch.no_grad():
                vec = model.encode_text(tokens.to(device))
                vec = vec / vec.norm(dim=-1, keepdim=True)
            return vec[0].cpu().tolist()
        except Exception as exc:
            logger.error("clip.embed_text_failed", error=str(exc))
            return None

    def index_images(
        self,
        image_paths: list[str],
        source_urls: Optional[dict[str, str]] = None,
        batch_size: int = 16,
    ) -> int:
        """Indexe une liste d'images dans Milvus CLIPVectors."""
        import torch
        try:
            from pymilvus import Collection, connections
            connections.connect("default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
            col = Collection(_CLIP_COLLECTION)
        except Exception as exc:
            logger.error("clip.milvus_connect_failed", error=str(exc))
            return 0

        indexed = 0
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i : i + batch_size]
            records = []
            for path in batch:
                if not Path(path).exists():
                    continue
                vec = self._embed_image(path)
                if vec is None:
                    continue
                img_hash = hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]
                records.append({
                    "image_hash":       img_hash,
                    "source_url":       (source_urls or {}).get(path, path)[:500],
                    "investigation_id": self.investigation_id,
                    "vector":           vec,
                })
            if records:
                try:
                    col.insert(records)
                    col.flush()
                    indexed += len(records)
                except Exception as exc:
                    logger.error("clip.insert_failed", error=str(exc))
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        logger.info("clip.indexed", count=indexed, investigation=self.investigation_id)
        return indexed

    def search_by_text(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.25,
    ) -> list[dict[str, Any]]:
        """Recherche d'images par description textuelle (text-to-image)."""
        vec = self._embed_text(query)
        return self._search(vec, top_k, min_score) if vec else []

    def search_by_image(
        self,
        image_path: str,
        top_k: int = 10,
        min_score: float = 0.85,
    ) -> list[dict[str, Any]]:
        """Recherche d'images similaires (image-to-image)."""
        vec = self._embed_image(image_path)
        return self._search(vec, top_k, min_score) if vec else []

    def _search(
        self,
        vector: list[float],
        top_k: int,
        min_score: float,
    ) -> list[dict[str, Any]]:
        try:
            from pymilvus import Collection, connections
            connections.connect("default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
            col = Collection(_CLIP_COLLECTION)
            results = col.search(
                data=[vector],
                anns_field="vector",
                param={"metric_type": "COSINE", "params": {"ef": settings.MILVUS_SEARCH_EF}},
                limit=top_k,
                expr=f'investigation_id == "{self.investigation_id}"',
                output_fields=["image_hash", "source_url"],
            )
            hits = []
            for res in results:
                for hit in res:
                    if hit.score >= min_score:
                        hits.append({
                            "source_url": hit.entity.get("source_url"),
                            "image_hash": hit.entity.get("image_hash"),
                            "score":      round(hit.score, 4),
                        })
            return hits
        except Exception as exc:
            logger.error("clip.search_failed", error=str(exc))
            return []
