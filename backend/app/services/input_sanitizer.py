# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Input Sanitizer : Nettoyage des payloads avant injection dans le LLM
backend/app/services/input_sanitizer.py

Trois opérations :
  1. Suppression des caractères de contrôle et balises cachées
  2. Troncature intelligente (résumé si > MAX_TOKENS)
  3. Tagging de provenance [SCRAPED_DATA] dans le prompt
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# Caractères de contrôle dangereux (Unicode control chars sauf \n, \t, \r)
_CONTROL_CHARS_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f"    # ASCII control
    r"\x80-\x9f"                              # Latin-1 control
    r"\u200b-\u200f\u202a-\u202e"            # Zero-width + bidi override
    r"\u2060-\u2064\ufeff]",                  # Word joiner + BOM
    re.UNICODE,
)

# Balises HTML masquées (pour contrer les injections HTML dans le LLM context)
_HTML_TAGS_RE = re.compile(r"<[^>]{0,200}>", re.DOTALL)

# Token approximatif (1 token ≈ 4 chars pour les LLM)
_CHARS_PER_TOKEN = 4
# Max tokens injectés en contexte (laisse de la marge pour le prompt système)
_MAX_CONTEXT_TOKENS = 3000
_MAX_CONTEXT_CHARS = _MAX_CONTEXT_TOKENS * _CHARS_PER_TOKEN


def sanitize(
    text: str,
    source: str = "external",
    investigation_id: Optional[str] = None,
    max_chars: int = _MAX_CONTEXT_CHARS,
    tag_source: bool = True,
) -> str:
    """
    Nettoie un texte externe avant injection dans le contexte LLM.

    Args:
        text            : Texte brut à nettoyer
        source          : Origine du texte (ex: "darkweb", "telegram", "surface")
        investigation_id: ID d'investigation pour audit
        max_chars       : Limite de caractères après nettoyage
        tag_source      : Ajouter le tag [SCRAPED_DATA] de provenance

    Returns:
        str : Texte nettoyé et sûr pour injection LLM
    """
    if not text:
        return ""

    original_len = len(text)

    # 1. Normalisation Unicode (NFC) — supprime les sequences combinées
    text = unicodedata.normalize("NFC", text)

    # 2. Suppression des caractères de contrôle dangereux
    text = _CONTROL_CHARS_RE.sub(" ", text)

    # 3. Suppression des balises HTML
    text = _HTML_TAGS_RE.sub(" ", text)

    # 4. Suppression des espaces multiples
    text = re.sub(r"[ \t]{3,}", "  ", text)

    # 5. Troncature avec message d'avertissement
    if len(text) > max_chars:
        truncated = True
        text = text[:max_chars]
        # Couper proprement à la dernière phrase complète
        last_period = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
        if last_period > max_chars * 0.8:
            text = text[: last_period + 1]
        text += "\n[... TEXTE TRONQUÉ PAR ARGUS-INT POUR RAISONS DE SÉCURITÉ ...]"
    else:
        truncated = False

    # 6. Tagging de provenance (essentiel pour que le LLM traite ça comme donnée externe)
    if tag_source:
        source_tag = f"[SCRAPED_DATA::{source.upper()}]"
        text = f"{source_tag}\n{text}\n[/SCRAPED_DATA]"

    logger.debug(
        "input_sanitizer.processed",
        original_chars=original_len,
        sanitized_chars=len(text),
        truncated=truncated,
        source=source,
        investigation_id=investigation_id,
    )

    return text


def sanitize_batch(
    texts: list[str],
    source: str = "external",
    investigation_id: Optional[str] = None,
) -> list[str]:
    """Nettoie une liste de textes en batch."""
    return [sanitize(t, source, investigation_id) for t in texts]


def estimate_tokens(text: str) -> int:
    """Estimation rapide du nombre de tokens (1 token ≈ 4 chars)."""
    return len(text) // _CHARS_PER_TOKEN
