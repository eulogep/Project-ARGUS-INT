# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Message Drafter : Génération de messages HUMINT via LLM local
backend/app/cognitive/humint/message_drafter.py

Intègre : PersonaProfile + StylometryAdapter + AI Firewall (output guard)
HITL obligatoire : tout message passe par ApprovalQueue avant envoi.
"""
from __future__ import annotations

from typing import Optional

import structlog
from pydantic import BaseModel, Field

from app.config import settings
from app.services.input_sanitizer import sanitize

logger = structlog.get_logger(__name__)


class MessageDraft(BaseModel):
    """Brouillon de message HUMINT généré, en attente d'approbation."""
    investigation_id:  str
    persona_username:  str
    target_platform:   str
    target_context:    str        # Description du contexte cible (anonymisée)
    generated_message: str
    style_score:       float = 0.0  # Score de fidélité stylistique (0-1)
    opsec_validated:   bool = False
    raw_prompt:        str = ""     # Prompt utilisé (pour audit, non exposé en API)


_DRAFT_SYSTEM_PROMPT = """Tu es un opérateur de renseignement humain (HUMINT) expérimenté.
Tu génères des messages de contact authentiques et crédibles pour des opérations autorisées.

RÈGLES ABSOLUES :
1. Ne jamais révéler que tu es une IA ou un système automatisé.
2. Ne jamais mentionner l'investigation, les sources, ou les outils utilisés.
3. Le message doit paraître écrit par un humain réel avec le profil décrit.
4. Adapter le registre de langue au contexte de la plateforme.
5. Message court et naturel (50-150 mots maximum pour un premier contact)."""


async def draft_message(
    investigation_id: str,
    persona_username:  str,
    persona_background: str,
    target_platform:   str,
    objective:         str,
    target_context:    str,
    style_instructions: str = "",
    max_words:         int = 150,
) -> Optional[MessageDraft]:
    """
    Génère un message de pretexting via le LLM local.

    Args:
        investigation_id    : ID investigation (audit)
        persona_username    : Nom d'utilisateur du persona
        persona_background  : Bio du persona (contexte LLM)
        target_platform     : Plateforme ("telegram", "discord", "forum")
        objective           : Objectif du contact (ex: "établir un premier contact amical")
        target_context      : Description de la cible/communauté (sanitisée)
        style_instructions  : Instructions stylistiques (StylometryAdapter output)
        max_words           : Longueur maximale du message

    Returns:
        MessageDraft ou None si la génération échoue
    """
    # Double sanitisation entrée
    safe_context   = sanitize(target_context,    source="investigation", investigation_id=investigation_id)
    safe_objective = sanitize(objective,         source="investigation")
    safe_bg        = sanitize(persona_background, source="investigation")

    user_prompt = f"""## Ton identité
Pseudo : {persona_username}
Profil : {safe_bg[:300]}

## Contexte de la plateforme
{target_platform.upper()} — {safe_context[:400]}

## Objectif de ce message
{safe_objective[:200]}

{style_instructions[:600] if style_instructions else ""}

## Génère le message
Écris un message de {max_words} mots maximum. Naturel, humain, adapté au contexte.
Réponds UNIQUEMENT avec le message, sans introduction ni explication."""

    try:
        from openai import AsyncOpenAI
        if settings.INFERENCE_BACKEND == "vllm":
            client = AsyncOpenAI(base_url=settings.VLLM_LIGHT_URL, api_key="not-needed")
            model  = settings.VLLM_LIGHT_MODEL
        else:
            client = AsyncOpenAI(base_url=f"{settings.OLLAMA_BASE_URL}/v1", api_key="not-needed")
            model  = settings.OLLAMA_MODEL

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _DRAFT_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.85,
            max_tokens=350,
            timeout=settings.LLM_REQUEST_TIMEOUT_S,
        )
        message_text = (response.choices[0].message.content or "").strip()

        if not message_text or len(message_text) < 10:
            logger.warning("drafter.empty_response", investigation=investigation_id)
            return None

        # Validation OPSEC de la sortie (Output Guard)
        opsec_ok = _validate_output_opsec(message_text)

        draft = MessageDraft(
            investigation_id  = investigation_id,
            persona_username  = persona_username,
            target_platform   = target_platform,
            target_context    = safe_context[:300],
            generated_message = message_text,
            opsec_validated   = opsec_ok,
            raw_prompt        = user_prompt,  # Stocké pour audit interne uniquement
        )
        logger.info(
            "drafter.message_generated",
            investigation = investigation_id,
            platform      = target_platform,
            words         = len(message_text.split()),
            opsec_ok      = opsec_ok,
        )
        return draft

    except Exception as exc:
        logger.error("drafter.failed", investigation=investigation_id, error=str(exc))
        return None


def _validate_output_opsec(message: str) -> bool:
    """
    Vérifie que le message généré ne contient pas de fuite OPSEC.
    Retourne True si le message est sûr.
    """
    import re
    forbidden_patterns = [
        r"argus.?int",
        r"investigation",
        r"api.?key",
        r"system.?prompt",
        r"je suis une ia",
        r"i am an? ai",
        r"as an? (ai|language model|llm)",
        r"openai|anthropic|mistral|llama",
        r"127\.0\.0\.1|localhost",
        r"bearer [a-zA-Z0-9]{20,}",
    ]
    msg_lower = message.lower()
    for pattern in forbidden_patterns:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            logger.warning("drafter.opsec_leak_detected", pattern=pattern)
            return False
    return True
