# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — HUMINT Persona Generator
backend/app/cognitive/humint/persona_generator.py

Génère des profils complets (bio, historique, style) adaptés au contexte cible.
Utilise le LLM local (vLLM ou Ollama) — zéro API cloud.
HITL : Les personas ne sont jamais déployés sans approbation.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import structlog
from pydantic import BaseModel, Field

from app.config import settings
from app.services.input_sanitizer import sanitize

logger = structlog.get_logger(__name__)


class PersonaProfile(BaseModel):
    """Profil complet d'un persona HUMINT."""
    username:       str
    display_name:   str
    age:            int
    nationality:    str
    background:     str           # Bio courte (2-3 phrases)
    interests:      list[str]     # Centres d'intérêt liés au contexte cible
    writing_style:  str           # Description du style d'écriture
    vocabulary_level: str         # "casual", "technical", "academic", "street"
    typical_phrases: list[str]    # 3-5 expressions caractéristiques
    platform_history: str         # Historique fictif sur la plateforme
    opsec_notes:    str           # Contraintes OPSEC (ce que le persona NE sait PAS)
    investigation_id: str
    created_for_platform: str


_PERSONA_PROMPT = """Tu es un expert en opérations de renseignement humain (HUMINT).
Génère un persona fictif crédible pour infiltrer la cible suivante.

## Contexte cible
Plateforme : {platform}
Description : {context}
Style de la cible : {target_style}

## Instructions
- Le persona doit être COHÉRENT avec la culture de la plateforme
- Inclure des intérêts AUTHENTIQUES liés au contexte (pas trop alignés avec la cible pour éviter la suspicion)
- Le style d'écriture doit correspondre au profil démographique
- Les contraintes OPSEC doivent lister ce que le persona NE peut PAS révéler

Réponds UNIQUEMENT en JSON valide avec les champs :
username, display_name, age, nationality, background, interests (list),
writing_style, vocabulary_level, typical_phrases (list), platform_history, opsec_notes

[CONTEXTE GÉNÉRÉ POUR USAGE AUTORISÉ UNIQUEMENT — SYSTÈME ARGUS-INT]"""


async def generate_persona(
    investigation_id: str,
    platform: str,
    context: str,
    target_style: str = "casual",
) -> Optional[PersonaProfile]:
    """
    Génère un persona HUMINT via le LLM local.

    Args:
        investigation_id : ID d'investigation (traçabilité)
        platform         : Plateforme cible ("telegram", "discord", "forum_darkweb")
        context          : Description du contexte cible (sanitisé avant injection)
        target_style     : Style d'écriture de la cible (pour adaptation)

    Returns:
        PersonaProfile ou None si la génération échoue
    """
    # Sanitisation du contexte avant injection LLM
    safe_context = sanitize(context, source="investigation", investigation_id=investigation_id)
    safe_style = sanitize(target_style, source="investigation")

    prompt = _PERSONA_PROMPT.format(
        platform=platform,
        context=safe_context[:500],
        target_style=safe_style[:200],
    )

    try:
        from openai import AsyncOpenAI
        # Utilise vLLM (OpenAI-compatible) ou Ollama selon la config
        if settings.INFERENCE_BACKEND == "vllm":
            client = AsyncOpenAI(base_url=settings.VLLM_LIGHT_URL, api_key="not-needed")
            model = settings.VLLM_LIGHT_MODEL
        else:
            client = AsyncOpenAI(base_url=f"{settings.OLLAMA_BASE_URL}/v1", api_key="not-needed")
            model = settings.OLLAMA_MODEL

        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=800,
            timeout=settings.LLM_REQUEST_TIMEOUT_S,
        )
        raw_json = response.choices[0].message.content or "{}"
        # Extraction robuste du JSON (le LLM peut ajouter du texte avant/après)
        start = raw_json.find("{")
        end = raw_json.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("Pas de JSON trouvé dans la réponse LLM")
        data: dict[str, Any] = json.loads(raw_json[start:end])
        persona = PersonaProfile(
            **data,
            investigation_id=investigation_id,
            created_for_platform=platform,
        )
        logger.info(
            "persona.generated",
            investigation=investigation_id,
            platform=platform,
            username=persona.username,
        )
        return persona
    except Exception as exc:
        logger.error("persona.generation_failed", investigation=investigation_id, error=str(exc))
        return None
