# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — OCR Intelligence Pipeline : PaddleOCR + extraction structurée
backend/app/services/vision/ocr_intel.py

Extrait : texte brut, plaques d'immatriculation, données de documents (ID, passeport),
coordonnées GPS dans les métadonnées EXIF, et structures tabulaires.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

_PADDLEOCR_MODEL_DIR = os.getenv("PADDLEOCR_HOME", "/models/vision/paddleocr")

# Patterns d'extraction structurée
_PLATE_RE = re.compile(
    r'\b([A-Z]{1,3}[-\s]?\d{2,4}[-\s]?[A-Z]{0,3}|'  # Européen/FR
    r'\d{1,3}[A-Z]{1,3}\d{3,4}|'                      # Format mixte
    r'[A-Z]{2}\d{2}[A-Z]{3})\b',                       # UK
    re.IGNORECASE,
)
_DATE_RE = re.compile(r'\b(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})\b')
_COORDS_RE = re.compile(r'(\d{1,3}°\d{1,2}[\'′]\d{1,2}(?:\.\d+)?[\"″]?\s*[NSEW])')
_ID_KEYWORDS = {"surname", "given", "nom", "prénom", "date of birth", "nationality", "passport", "expires"}


class OCRResult:
    """Résultat structuré d'une analyse OCR."""

    def __init__(
        self,
        raw_text: str,
        confidence: float,
        image_path: str,
    ) -> None:
        self.raw_text = raw_text
        self.confidence = round(confidence, 3)
        self.image_path = image_path
        self.plates: list[str] = []
        self.dates: list[str] = []
        self.coordinates: list[str] = []
        self.document_fields: dict[str, str] = {}
        self.is_document: bool = False
        self._extract_structures()

    def _extract_structures(self) -> None:
        text_lower = self.raw_text.lower()
        self.plates = _PLATE_RE.findall(self.raw_text)
        self.dates = _DATE_RE.findall(self.raw_text)
        self.coordinates = _COORDS_RE.findall(self.raw_text)
        # Détection de document officiel
        keyword_hits = sum(1 for kw in _ID_KEYWORDS if kw in text_lower)
        self.is_document = keyword_hits >= 2
        # Extraction basique de champs document (ligne après keyword)
        if self.is_document:
            lines = self.raw_text.splitlines()
            for i, line in enumerate(lines):
                for kw in _ID_KEYWORDS:
                    if kw in line.lower() and i + 1 < len(lines):
                        value = lines[i + 1].strip()
                        if value and len(value) < 80:
                            self.document_fields[kw] = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_text":       self.raw_text[:2000],
            "confidence":     self.confidence,
            "image_path":     self.image_path,
            "plates":         self.plates,
            "dates":          self.dates,
            "coordinates":    self.coordinates,
            "is_document":    self.is_document,
            "document_fields": self.document_fields,
        }


class OCRIntelPipeline:
    """
    Pipeline PaddleOCR enrichi pour l'extraction d'intelligence depuis des images.

    Usage :
        pipeline = OCRIntelPipeline()
        result = pipeline.analyze("/tmp/id_card.jpg")
        batch = pipeline.analyze_batch(["/tmp/a.jpg", "/tmp/b.jpg"])
    """

    _instance: Optional["OCRIntelPipeline"] = None
    _ocr: Any = None

    def __new__(cls) -> "OCRIntelPipeline":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_ocr(self) -> Any:
        if self._ocr is not None:
            return self._ocr
        try:
            from paddleocr import PaddleOCR
            os.environ["PADDLEOCR_HOME"] = _PADDLEOCR_MODEL_DIR
            # det+rec+cls : détection de lignes + reconnaissance + classification orientation
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",          # Multi-lang via separate model
                use_gpu=False,      # OCR sur CPU (économise GPU pour vision)
                show_log=False,
                det_model_dir=f"{_PADDLEOCR_MODEL_DIR}/whl/det/en",
                rec_model_dir=f"{_PADDLEOCR_MODEL_DIR}/whl/rec/en",
                cls_model_dir=f"{_PADDLEOCR_MODEL_DIR}/whl/cls",
            )
            logger.info("ocr.paddleocr_loaded")
        except Exception as exc:
            logger.error("ocr.load_failed", error=str(exc))
            self._ocr = None
        return self._ocr

    def analyze(self, image_path: str) -> Optional[OCRResult]:
        """Analyse une image et extrait le texte + structures intelligentes."""
        if not Path(image_path).exists():
            logger.warning("ocr.image_not_found", path=image_path)
            return None
        ocr = self._get_ocr()
        if ocr is None:
            return None
        try:
            # Aussi extraire les métadonnées EXIF pour coords GPS
            exif_coords = self._extract_exif_gps(image_path)
            result = ocr.ocr(image_path, cls=True)
            if not result or not result[0]:
                return OCRResult("", 0.0, image_path)
            texts: list[str] = []
            confidences: list[float] = []
            for line in result[0]:
                if line and len(line) >= 2:
                    text_conf = line[1]
                    if isinstance(text_conf, (list, tuple)) and len(text_conf) == 2:
                        texts.append(str(text_conf[0]))
                        confidences.append(float(text_conf[1]))
            full_text = "\n".join(texts)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            ocr_result = OCRResult(full_text, avg_conf, image_path)
            # Ajouter les coords EXIF si présentes
            if exif_coords:
                ocr_result.coordinates.extend(exif_coords)
            logger.debug("ocr.analyzed", path=image_path, chars=len(full_text), is_doc=ocr_result.is_document)
            return ocr_result
        except Exception as exc:
            logger.error("ocr.analyze_failed", path=image_path, error=str(exc))
            return None

    def analyze_batch(
        self,
        image_paths: list[str],
        batch_size: int = 10,
    ) -> dict[str, Optional[OCRResult]]:
        """Traitement batch."""
        results: dict[str, Optional[OCRResult]] = {}
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i : i + batch_size]
            for path in batch:
                results[path] = self.analyze(path)
        return results

    @staticmethod
    def _extract_exif_gps(image_path: str) -> list[str]:
        """Extrait les coordonnées GPS depuis les métadonnées EXIF."""
        try:
            import exifread
            with open(image_path, "rb") as f:
                tags = exifread.process_file(f, stop_tag="GPS GPSLongitude", details=False)
            coords: list[str] = []
            lat = tags.get("GPS GPSLatitude")
            lon = tags.get("GPS GPSLongitude")
            lat_ref = tags.get("GPS GPSLatitudeRef")
            lon_ref = tags.get("GPS GPSLongitudeRef")
            if lat and lon:
                coords.append(f"EXIF_GPS:{lat} {lat_ref} / {lon} {lon_ref}")
            return coords
        except Exception:
            return []
