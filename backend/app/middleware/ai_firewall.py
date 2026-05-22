# ==============================================================================
# Project ARGUS-INT - Multi-Spectrum Intelligence Fusion Platform
# Copyright (C) 2026 eulogep — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — AI Firewall : Protection contre les Prompt Injections Indirectes
backend/app/middleware/ai_firewall.py

Architecture à 3 couches :
  Layer 1 : Regex rapides (< 1ms) — catch patterns évidents
  Layer 2 : Heuristique linguistique (< 5ms) — changement de registre
  Layer 3 : DeBERTa classificateur local (< 50ms) — inférence ML précise

Usage :
  # En tant que middleware Celery/Service :
  sanitized = await firewall.check(text, source="darkweb", investigation_id="...")

  # En tant que middleware FastAPI :
  from app.middleware.ai_firewall import AIFirewallMiddleware
  app.add_middleware(AIFirewallMiddleware)
"""

from __future__ import annotations

import re
import time
import logging
from typing import Any, Optional

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import settings

logger: structlog.BoundLogger = structlog.get_logger(__name__)


# ==============================================================================
#  EXCEPTIONS
# ==============================================================================

class PromptInjectionDetected(Exception):
    """Levée quand une injection de prompt est détectée dans une entrée externe."""

    def __init__(
        self,
        text: str,
        score: int,
        layer: int,
        reason: str,
        investigation_id: Optional[str] = None,
    ) -> None:
        self.text_snippet = text[:200]
        self.score = score
        self.layer = layer
        self.reason = reason
        self.investigation_id = investigation_id
        super().__init__(
            f"[AI Firewall] Injection détectée — Layer {layer} | score={score} | {reason}"
        )


# ==============================================================================
#  LAYER 1 — PATTERNS REGEX
# ==============================================================================

# Patterns classiques d'injection directe et indirecte
_INJECTION_PATTERNS: list[tuple[str, int, str]] = [
    # (pattern, score_contribution, description)
    (r"ignore\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompts?|rules?|context)", 40, "instruction override"),
    (r"forget\s+(everything|all|your)\s*(instructions?|rules?|training|above)?", 35, "memory wipe"),
    (r"(you\s+are\s+now|act\s+as|pretend\s+(to\s+be|you\s+are)|roleplay\s+as)\s+.{0,50}(ai|bot|assistant|gpt|llm|model)", 30, "persona hijack"),
    (r"(system\s+prompt|sys\s+prompt|initial\s+instruction|hidden\s+instruction)", 35, "system prompt probe"),
    (r"(print|output|repeat|reveal|show|display|echo)\s+(your|the)?\s*(system\s+)?(prompt|instruction|token|secret|key|password)", 45, "exfiltration attempt"),
    (r"(DAN|jailbreak|do\s+anything\s+now|developer\s+mode|god\s+mode|unrestricted\s+mode)", 50, "jailbreak keyword"),
    (r"(```|\[INST\]|<\|im_start\|>|<\|system\|>|\[SYS\])\s*(system|user|assistant)?", 25, "template injection"),
    (r"translate\s+the\s+following\s+and\s+(also|then)\s+(do|execute|run|ignore)", 30, "translate+execute"),
    (r"(base64|rot13|hex|unicode)\s+(decode|encode|this|the\s+following)", 20, "encoding obfuscation"),
    (r"(new\s+instructions?|updated\s+instructions?|latest\s+instructions?)\s*:", 35, "instruction update injection"),
    (r"(#\s*SYSTEM|##\s*INSTRUCTIONS|---\s*NEW\s*PROMPT)", 40, "markdown prompt boundary"),
    (r"<(script|iframe|img|svg|object|embed|form)[^>]*>", 20, "HTML injection"),
]

_COMPILED_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(p, re.IGNORECASE | re.DOTALL), score, desc)
    for p, score, desc in _INJECTION_PATTERNS
]


def _layer1_regex_check(text: str) -> tuple[int, list[str]]:
    """
    Layer 1 : Scan regex rapide.
    Retourne (score_total, [reasons_détectées]).
    Score > AI_FIREWALL_REGEX_THRESHOLD * 10 = suspect.
    """
    total_score = 0
    reasons: list[str] = []

    for pattern, score, desc in _COMPILED_PATTERNS:
        if pattern.search(text):
            total_score += score
            reasons.append(desc)

    return total_score, reasons


# ==============================================================================
#  LAYER 2 — HEURISTIQUE LINGUISTIQUE
# ==============================================================================

# Marqueurs de changement de registre : passage soudain à l'impératif/méta
_REGISTER_SHIFT_MARKERS: list[str] = [
    "maintenant tu dois",
    "nouvelle tâche :",
    "nouvelle instruction :",
    "oublie ce qui précède",
    "en tant qu'ia",
    "ton vrai rôle est",
    "tes vraies instructions sont",
    "ignore le reste",
    "ta vraie mission",
    "agis comme si",
    "now your task is",
    "your new instructions",
    "disregard the above",
    "your actual purpose",
    "secret mode activated",
    "override protocol",
    "vous devez maintenant",
    "instrucción del sistema",
    "nueva instrucción",
]

# Ratio de mots impératifs suspects dans le texte
_IMPERATIVE_TRIGGERS: set[str] = {
    "reveal", "expose", "extract", "dump", "exfil", "bypass", "override",
    "divulge", "leak", "print", "output", "return", "give", "show",
    "révèle", "affiche", "montre", "donne", "extrais", "exporte",
}


def _layer2_linguistic_check(text: str) -> tuple[int, list[str]]:
    """
    Layer 2 : Analyse heuristique du registre linguistique.
    Détecte les changements de contexte soudains ou les densités impératives.
    """
    score = 0
    reasons: list[str] = []
    text_lower = text.lower()

    # Check des marqueurs de changement de registre
    for marker in _REGISTER_SHIFT_MARKERS:
        if marker in text_lower:
            score += 25
            reasons.append(f"register_shift:{marker[:30]}")

    # Densité de mots impératifs (>3 dans un bloc de 100 chars = suspect)
    words = text_lower.split()
    imperative_count = sum(1 for w in words if w.strip(".,!?:;") in _IMPERATIVE_TRIGGERS)
    if imperative_count >= 3:
        score += imperative_count * 8
        reasons.append(f"imperative_density:{imperative_count}")

    # Détection de texte caché (espaces insécables, caractères Zero Width)
    hidden_chars = sum(
        1 for c in text
        if ord(c) in (0x200B, 0x200C, 0x200D, 0xFEFF, 0x00A0, 0x2060)
    )
    if hidden_chars > 2:
        score += 30
        reasons.append(f"hidden_unicode:{hidden_chars}_chars")

    # Détection de blocs de longueur suspecte (> 500 chars sans espace = possible encodage)
    long_words = [w for w in words if len(w) > 500]
    if long_words:
        score += 25
        reasons.append("suspiciously_long_token")

    return score, reasons


# ==============================================================================
#  LAYER 3 — DEBERTA CLASSIFICATEUR LOCAL (SINGLETON)
# ==============================================================================

class _DeBERTaFirewall:
    """
    Singleton chargeant le modèle DeBERTa de détection d'injections.
    Modèle : ProtectAI/deberta-v3-base-prompt-injection
    Chargé depuis le cache local HuggingFace (/models/classifiers).
    Zéro appel réseau (HF_HUB_OFFLINE=1).
    """

    _instance: Optional[_DeBERTaFirewall] = None
    _pipeline: Any = None
    _loaded: bool = False
    _load_failed: bool = False

    def __new__(cls) -> "_DeBERTaFirewall":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self) -> bool:
        """Charge le modèle en mémoire. Appelé une seule fois au démarrage."""
        if self._loaded or self._load_failed:
            return self._loaded

        try:
            import os
            # Forcer le mode offline — aucun appel réseau
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"

            from transformers import pipeline

            model_path = settings.AI_FIREWALL_MODEL_PATH
            self._pipeline = pipeline(
                task="text-classification",
                model=model_path,
                tokenizer=model_path,
                device=-1,          # CPU uniquement (léger et rapide)
                max_length=512,
                truncation=True,
            )
            self._loaded = True
            logger.info(
                "ai_firewall.deberta_loaded",
                model=model_path,
            )
        except Exception as exc:
            self._load_failed = True
            logger.warning(
                "ai_firewall.deberta_load_failed",
                error=str(exc),
                fallback="layers_1_2_only",
            )
        return self._loaded

    def predict_injection_score(self, text: str) -> int:
        """
        Retourne un score 0-100 d'injection.
        0 = texte sûr, 100 = injection certaine.
        """
        if not self._loaded or self._pipeline is None:
            return 0

        try:
            # Tronquer à 450 tokens (sécurité contre les débordements)
            snippet = text[:2048]
            results = self._pipeline(snippet)
            # Le modèle retourne : [{"label": "INJECTION", "score": 0.97}]
            for result in results:
                label: str = result.get("label", "").upper()
                confidence: float = float(result.get("score", 0.0))
                if "INJECTION" in label or label == "LABEL_1":
                    return int(confidence * 100)
                else:
                    # Invert pour les labels "SAFE"
                    return int((1.0 - confidence) * 100)
        except Exception as exc:
            logger.warning("ai_firewall.deberta_predict_error", error=str(exc))
        return 0


# Module-level singleton
_deberta = _DeBERTaFirewall()


def initialize_firewall() -> None:
    """À appeler au démarrage de l'app FastAPI (lifespan)."""
    if settings.AI_FIREWALL_ENABLED:
        _deberta.load()


# ==============================================================================
#  MOTEUR PRINCIPAL
# ==============================================================================

class AIFirewall:
    """
    Point d'entrée principal du firewall.
    Peut être utilisé :
      - En service Python direct (Celery tasks, services)
      - En middleware FastAPI (AIFirewallMiddleware)
    """

    def __init__(self) -> None:
        self.enabled = settings.AI_FIREWALL_ENABLED
        self.threshold = settings.AI_FIREWALL_THRESHOLD

    async def check(
        self,
        text: str,
        source: str = "unknown",
        investigation_id: Optional[str] = None,
        raise_on_detection: bool = True,
    ) -> dict[str, Any]:
        """
        Vérifie le texte contre les 3 layers.

        Returns:
            {
                "safe": bool,
                "total_score": int,         # 0-100
                "triggered_layer": int|None,
                "reasons": list[str],
                "processing_ms": float,
            }

        Raises:
            PromptInjectionDetected: si raise_on_detection=True et score >= threshold
        """
        if not self.enabled or not text or not text.strip():
            return {"safe": True, "total_score": 0, "triggered_layer": None, "reasons": [], "processing_ms": 0.0}

        t_start = time.perf_counter()
        all_reasons: list[str] = []
        total_score = 0

        # ── Layer 1 : Regex ────────────────────────────────────────────────
        l1_score, l1_reasons = _layer1_regex_check(text)
        total_score += l1_score
        all_reasons.extend(l1_reasons)

        if total_score >= self.threshold:
            processing_ms = (time.perf_counter() - t_start) * 1000
            await self._log_event(text, total_score, 1, l1_reasons, source, investigation_id)
            if raise_on_detection:
                raise PromptInjectionDetected(text, total_score, 1, str(l1_reasons), investigation_id)
            return {"safe": False, "total_score": total_score, "triggered_layer": 1, "reasons": all_reasons, "processing_ms": processing_ms}

        # ── Layer 2 : Linguistique ─────────────────────────────────────────
        l2_score, l2_reasons = _layer2_linguistic_check(text)
        total_score += l2_score
        all_reasons.extend(l2_reasons)

        if total_score >= self.threshold:
            processing_ms = (time.perf_counter() - t_start) * 1000
            await self._log_event(text, total_score, 2, all_reasons, source, investigation_id)
            if raise_on_detection:
                raise PromptInjectionDetected(text, total_score, 2, str(all_reasons), investigation_id)
            return {"safe": False, "total_score": total_score, "triggered_layer": 2, "reasons": all_reasons, "processing_ms": processing_ms}

        # ── Layer 3 : DeBERTa ML ───────────────────────────────────────────
        l3_score = _deberta.predict_injection_score(text)
        # Combinaison pondérée : layer3 est le plus fiable
        combined_score = int(total_score * 0.3 + l3_score * 0.7)

        processing_ms = (time.perf_counter() - t_start) * 1000
        is_safe = combined_score < self.threshold

        if not is_safe:
            all_reasons.append(f"deberta_score:{l3_score}")
            await self._log_event(text, combined_score, 3, all_reasons, source, investigation_id)
            if raise_on_detection:
                raise PromptInjectionDetected(text, combined_score, 3, str(all_reasons), investigation_id)

        logger.debug(
            "ai_firewall.check_complete",
            safe=is_safe,
            score=combined_score,
            l1=l1_score,
            l2=l2_score,
            l3=l3_score,
            ms=round(processing_ms, 2),
            source=source,
        )
        return {
            "safe": is_safe,
            "total_score": combined_score,
            "triggered_layer": None if is_safe else 3,
            "reasons": all_reasons,
            "processing_ms": round(processing_ms, 2),
        }

    async def _log_event(
        self,
        text: str,
        score: int,
        layer: int,
        reasons: list[str],
        source: str,
        investigation_id: Optional[str],
    ) -> None:
        """Persiste l'événement de sécurité dans PostgreSQL (non-bloquant)."""
        try:
            from app.database import get_db_session
            import json
            async with get_db_session() as db:
                await db.execute(
                    """
                    INSERT INTO ai_security_events
                        (investigation_id, source, score, triggered_layer, reasons, text_snippet)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    investigation_id,
                    source,
                    score,
                    layer,
                    json.dumps(reasons),
                    text[:500],
                )
        except Exception as exc:
            # Ne jamais bloquer le flow principal pour un log raté
            logger.error("ai_firewall.log_event_failed", error=str(exc))

    def check_sync(
        self,
        text: str,
        source: str = "unknown",
        investigation_id: Optional[str] = None,
        raise_on_detection: bool = True,
    ) -> dict[str, Any]:
        """
        Version synchrone pour les workers Celery.
        Utilise uniquement Layer 1 + 2 (pas d'I/O async nécessaire).
        """
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.check(text, source, investigation_id, raise_on_detection)
            )
        finally:
            loop.close()


# ==============================================================================
#  MIDDLEWARE FASTAPI
# ==============================================================================

class AIFirewallMiddleware(BaseHTTPMiddleware):
    """
    Middleware FastAPI qui inspecte les corps de requêtes POST/PUT.
    S'applique aux routes qui ingèrent du texte externe.
    """

    PROTECTED_PATHS: set[str] = {
        "/api/v1/cognitive/",
        "/api/v1/investigations",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Vérification uniquement sur les endpoints protégés
        path = request.url.path
        if not any(path.startswith(p) for p in self.PROTECTED_PATHS):
            return await call_next(request)

        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body_bytes = await request.body()
                body_str = body_bytes.decode("utf-8", errors="replace")

                firewall = AIFirewall()
                result = await firewall.check(
                    body_str,
                    source=f"api:{path}",
                    raise_on_detection=True,
                )
                logger.debug("ai_firewall.middleware_pass", path=path, score=result["total_score"])
            except PromptInjectionDetected as exc:
                logger.warning(
                    "ai_firewall.middleware_blocked",
                    path=path,
                    score=exc.score,
                    layer=exc.layer,
                    reasons=exc.reason,
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "prompt_injection_detected",
                        "detail": "La requête contient des patterns suspects et a été bloquée.",
                        "score": exc.score,
                        "layer": exc.layer,
                    },
                )

        return await call_next(request)


# ==============================================================================
#  DÉCORATEUR CELERY
# ==============================================================================

def firewall_protected(source: str = "external"):
    """
    Décorateur pour les tâches Celery traitant du texte externe.

    Usage :
        @firewall_protected(source="darkweb")
        def process_scraped_text(text: str, investigation_id: str) -> dict:
            ...
    """
    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Cherche un argument 'text' ou 'content' dans kwargs/args
            text_to_check = kwargs.get("text") or kwargs.get("content") or ""
            if not text_to_check and args:
                text_to_check = str(args[0]) if args else ""

            inv_id = kwargs.get("investigation_id")

            firewall = AIFirewall()
            result = firewall.check_sync(
                text=text_to_check,
                source=source,
                investigation_id=inv_id,
                raise_on_detection=True,
            )
            if not result["safe"]:
                # Log et retourne un résultat vide plutôt que crasher
                logger.warning(
                    "ai_firewall.celery_task_blocked",
                    func=func.__name__,
                    score=result["total_score"],
                )
                return {"blocked": True, "reason": "prompt_injection_detected"}

            return func(*args, **kwargs)

        return wrapper
    return decorator


# Singleton partagé
ai_firewall = AIFirewall()
