# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Object Detector : YOLOv8 GEOINT/IMINT
backend/app/services/vision/detector.py

Détecte : véhicules militaires, armes, uniformes, infrastructures critiques.
Modèle chargé depuis /models/vision/yolov8/ (air-gapped, zéro téléchargement).
Singleton pour éviter le rechargement GPU entre tâches.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

# Classes d'intérêt OSINT/GEOINT (sous-ensemble YOLOv8)
CLASSES_OF_INTEREST: dict[int, str] = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    # Classes custom du modèle fine-tuné militaire (IDs > 79)
    80: "military_vehicle",
    81: "weapon",
    82: "uniform",
    83: "checkpoint",
    84: "drone",
}

_MODEL_PATH_ENV = os.getenv("YOLO_MODEL_PATH", "/models/vision/yolov8/yolov8x.pt")


class DetectionResult:
    """Résultat structuré d'une détection."""
    __slots__ = ("class_id", "class_name", "confidence", "bbox", "is_sensitive")

    def __init__(
        self,
        class_id: int,
        class_name: str,
        confidence: float,
        bbox: list[float],
    ) -> None:
        self.class_id = class_id
        self.class_name = class_name
        self.confidence = round(confidence, 4)
        self.bbox = bbox  # [x1, y1, x2, y2] normalisé
        self.is_sensitive = class_id >= 80  # Classes militaires/armement

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_id":    self.class_id,
            "class_name":  self.class_name,
            "confidence":  self.confidence,
            "bbox":        self.bbox,
            "is_sensitive": self.is_sensitive,
        }


class ObjectDetector:
    """
    Singleton YOLOv8 pour la détection d'objets GEOINT/IMINT.

    Usage :
        detector = ObjectDetector.get_instance()
        results = detector.detect("/tmp/img.jpg", min_confidence=0.4)
    """

    _instance: Optional["ObjectDetector"] = None
    _model: Any = None

    def __new__(cls) -> "ObjectDetector":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ObjectDetector":
        if cls._instance is None:
            cls()
            cls._instance._load_model()
        elif cls._model is None:
            cls._instance._load_model()
        return cls._instance

    def _load_model(self) -> None:
        """Charge YOLOv8 depuis le cache local. Fallback CPU si pas de GPU."""
        try:
            from ultralytics import YOLO
            import torch
            os.environ["YOLO_OFFLINE"] = "1"  # Désactive les vérifications de mise à jour
            model_path = _MODEL_PATH_ENV
            if not Path(model_path).exists():
                logger.warning("detector.model_not_found", path=model_path)
                model_path = "yolov8n.pt"  # Fallback nano depuis cache ultralytics
            self._model = YOLO(model_path)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model.to(device)
            logger.info("detector.model_loaded", path=model_path, device=device)
        except Exception as exc:
            logger.error("detector.load_failed", error=str(exc))
            self._model = None

    def detect(
        self,
        image_path: str,
        min_confidence: float = 0.35,
        classes: Optional[list[int]] = None,
    ) -> list[DetectionResult]:
        """
        Détecte les objets dans une image.

        Args:
            image_path     : Chemin vers l'image (local)
            min_confidence : Seuil de confiance minimum
            classes        : Liste de class_ids à filtrer (None = tout)

        Returns:
            list[DetectionResult] trié par confiance décroissante
        """
        if self._model is None:
            logger.warning("detector.model_unavailable")
            return []
        try:
            import torch
            results = self._model(
                image_path,
                conf=min_confidence,
                classes=classes,
                verbose=False,
            )
            detections: list[DetectionResult] = []
            for r in results:
                boxes = r.boxes
                if boxes is None:
                    continue
                for box in boxes:
                    cid = int(box.cls.item())
                    conf = float(box.conf.item())
                    xyxyn = box.xyxyn[0].tolist()  # normalisé [0,1]
                    class_name = CLASSES_OF_INTEREST.get(cid, r.names.get(cid, f"class_{cid}"))
                    detections.append(DetectionResult(cid, class_name, conf, xyxyn))
            detections.sort(key=lambda d: d.confidence, reverse=True)
            # Libération VRAM après inférence
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.debug("detector.inference_done", image=image_path, count=len(detections))
            return detections
        except Exception as exc:
            logger.error("detector.inference_failed", image=image_path, error=str(exc))
            return []

    def detect_batch(
        self,
        image_paths: list[str],
        min_confidence: float = 0.35,
        batch_size: int = 8,
    ) -> dict[str, list[DetectionResult]]:
        """
        Traitement par lots pour de grands volumes d'images.

        Returns:
            dict {image_path: [DetectionResult, ...]}
        """
        results: dict[str, list[DetectionResult]] = {}
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i : i + batch_size]
            for path in batch:
                if Path(path).exists():
                    results[path] = self.detect(path, min_confidence)
                else:
                    logger.warning("detector.batch_missing", path=path)
                    results[path] = []
        return results
