# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Stylometry Adapter : Adaptation du style d'écriture au contexte cible
backend/app/cognitive/humint/stylometry_adapter.py

Analyse le corpus de textes de la cible via DeBERTa/sentence-transformers
et génère des instructions de style pour le LLM (System Prompt enrichi).
"""
from __future__ import annotations

from typing import Optional

import structlog

from app.services.stylometry import extract_style_profile, StyleProfile

logger = structlog.get_logger(__name__)


def build_style_instructions(
    target_texts: list[str],
    min_text_length: int = 50,
) -> str:
    """
    Analyse le style d'écriture d'une cible et génère des instructions LLM.

    Args:
        target_texts    : Liste de textes écrits par la cible
        min_text_length : Longueur minimale pour inclure un texte

    Returns:
        str : Instructions de style à injecter dans le system prompt LLM
    """
    valid_texts = [t for t in target_texts if len(t.strip()) >= min_text_length]
    if not valid_texts:
        return _default_style_instructions()

    # Extraction des profils stylistiques
    profiles: list[StyleProfile] = []
    for text in valid_texts[:20]:  # Limiter à 20 samples
        try:
            profile = extract_style_profile(text)
            profiles.append(profile)
        except Exception as exc:
            logger.warning("style_adapter.profile_failed", error=str(exc))

    if not profiles:
        return _default_style_instructions()

    # Agrégation des métriques
    avg_word_len = sum(p.avg_word_length for p in profiles) / len(profiles)
    avg_sent_len = sum(p.avg_sentence_length for p in profiles) / len(profiles)
    avg_punct_density = sum(p.punctuation_density for p in profiles) / len(profiles)
    avg_caps = sum(p.caps_ratio for p in profiles) / len(profiles)
    avg_ellipsis = sum(p.ellipsis_freq for p in profiles) / len(profiles)
    avg_question = sum(p.question_ratio for p in profiles) / len(profiles)
    avg_exclamation = sum(p.exclamation_ratio for p in profiles) / len(profiles)
    total_emojis = sum(p.emoji_count for p in profiles)

    # Construction des instructions de style
    instructions: list[str] = ["## Instructions de Style à Reproduire Exactement"]

    # Longueur des phrases
    if avg_sent_len < 8:
        instructions.append("- Phrases très courtes et directes (moins de 8 mots en moyenne).")
    elif avg_sent_len > 20:
        instructions.append("- Phrases longues et élaborées (plus de 20 mots en moyenne).")
    else:
        instructions.append(f"- Phrases de longueur moyenne ({avg_sent_len:.0f} mots environ).")

    # Ponctuation
    if avg_punct_density > 0.08:
        instructions.append("- Ponctuation dense — utiliser beaucoup de virgules et points-virgules.")
    elif avg_punct_density < 0.03:
        instructions.append("- Peu de ponctuation — style télégraphique, minimaliste.")

    # Ellipses
    if avg_ellipsis > 0.3:
        instructions.append("- Utiliser fréquemment les '...' pour marquer l'hésitation ou la continuation.")

    # Questions
    if avg_question > 0.5:
        instructions.append("- Style interrogatif dominant — inclure des questions rhétoriques.")

    # Exclamations
    if avg_exclamation > 0.4:
        instructions.append("- Registre expressif/émotionnel — utiliser des exclamations '!'.")

    # Majuscules
    if avg_caps > 0.15:
        instructions.append("- Usage fréquent de MAJUSCULES pour l'emphase.")

    # Emojis
    if total_emojis > len(profiles) * 2:
        instructions.append("- Incorporer des emojis dans les messages (style jeune/informel).")

    # Phrases typiques détectées
    all_bigrams: list[str] = []
    for p in profiles:
        all_bigrams.extend(p.top_bigrams[:3])
    if all_bigrams:
        # Ne montrer que les bigrams de lettres (pas de ponctuation)
        word_bigrams = [b for b in all_bigrams if b.replace(" ", "").isalpha() and len(b) > 3][:5]
        if word_bigrams:
            instructions.append(f"- Patterns linguistiques fréquents : {', '.join(set(word_bigrams))}")

    instructions.append("\n## Contrainte Absolue")
    instructions.append("Ne jamais mentionner d'informations réelles sur l'investigation ou ses sources.")
    instructions.append("Rester dans le persona défini. Ne jamais sortir du rôle.")

    result = "\n".join(instructions)
    logger.debug("style_adapter.built", profiles=len(profiles), instructions_len=len(result))
    return result


def _default_style_instructions() -> str:
    return """## Instructions de Style
- Style naturel et conversationnel adapté à la plateforme cible.
- Éviter le langage trop formel ou académique.
- Ne jamais mentionner l'investigation ou ses sources.
- Rester dans le persona défini."""


def adapt_message_to_style(
    draft: str,
    style_instructions: str,
) -> str:
    """
    Retourne un prompt enrichi qui demande au LLM de réécrire
    le brouillon en respectant les contraintes de style.
    """
    return f"""{style_instructions}

## Brouillon à adapter
{draft}

## Tâche
Réécris ce message en respectant EXACTEMENT les instructions de style ci-dessus.
Conserve le sens et l'objectif du message, mais adapte le registre et la forme.
Réponds uniquement avec le message réécrit, sans commentaires."""
