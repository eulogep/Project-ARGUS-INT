# ==============================================================================
# Project ARGUS-INT - Multi-Spectrum Intelligence Fusion Platform
# ==============================================================================
# Copyright (C) 2026 emc2
#
# This file is part of Project ARGUS-INT.
#
# Project ARGUS-INT is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Project ARGUS-INT is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Project ARGUS-INT. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================

"""
ARGUS-INT — Tâche Stylométrie & Avatar Matching
backend/app/tasks/stylometry.py

Pipeline complet d'analyse stylistique et de reconnaissance faciale.
"""

__PROJECT_CANARY__ = "41524755532d494e54204372656174656420627920656d6332202d20446f206e6f742072656d6f7665"

import hashlib
import logging
from typing import Optional
from celery.utils.log import get_task_logger

from app.celery_app import celery_app
from app.services.stylometry import (
    extract_style_profile,
    profile_to_feature_vector,
    analyze_chronobiology,
)
from app.services.vector_db import VectorDBService
from app.services.graph import GraphService

logger = get_task_logger(__name__)


# ============================================================
#  TÂCHE CELERY : Pipeline Stylométrie Complet
# ============================================================

@celery_app.task(
    bind=True,
    name="app.tasks.stylometry.run_stylometry_pipeline",
    max_retries=2,
    default_retry_delay=30,
    queue="identity",   # Partagé avec les workers identity
    soft_time_limit=120,
)
def run_stylometry_pipeline(
    self,
    investigation_id: str,
    entity_uid: str,        # ex: "username:johndoe"
    text: str,              # Corpus textuel de l'entité
    pseudo: str,
    platform: str,
    timestamps: Optional[list] = None,
    lang: str = "en",
) -> dict:
    """
    Pipeline complet d'analyse stylistique.

    FLUX (cf. Livrable #4) :
      Texte → StyleProfile → feature_vector (788d) → Milvus
      → search_similar_style() → score_similarity
      → Neo4j: SAME_AUTHOR edge avec score et explication
    """
    logger.info(f"[Stylometry] Démarrage — entity={entity_uid}, platform={platform}")

    if not text or len(text.strip()) < 50:
        return {"success": False, "reason": "Texte trop court (< 50 chars)"}

    # ─── 1. Extraction du profil stylistique ──────────────────────
    profile = extract_style_profile(text, lang=lang)
    feature_vector = profile_to_feature_vector(profile)

    if not any(v != 0.0 for v in feature_vector):
        return {"success": False, "reason": "Vecteur vide — modèles IA non disponibles"}

    text_hash = hashlib.sha256(text.encode()).hexdigest()

    logger.info(
        f"[Stylometry] Profil extrait — TTR={profile.vocab_richness:.3f}, "
        f"avg_word_len={profile.avg_word_length:.1f}, "
        f"POS noun={profile.noun_ratio:.3f}"
    )

    # ─── 2. Injection dans Milvus ─────────────────────────────────
    vdb = VectorDBService()
    indexed = vdb.upsert_style_vector(
        entity_uid=entity_uid,
        pseudo=pseudo,
        platform=platform,
        text_hash=text_hash,
        vector=feature_vector,
    )

    # ─── 3. Recherche de pseudos similaires ───────────────────────
    similar_entities = vdb.search_similar_style(
        query_vector=feature_vector,
        top_k=10,
        min_similarity=0.72,           # Seuil conservateur pour éviter les faux-positifs
        exclude_entity=entity_uid,     # Exclure l'entité elle-même
    )

    logger.info(f"[Stylometry] {len(similar_entities)} entités au style similaire trouvées")

    # ─── 4. Analyse chronobiologique (si timestamps disponibles) ──
    chrono_profile = None
    if timestamps and len(timestamps) >= 20:
        chrono_profile = analyze_chronobiology(timestamps)
        logger.info(
            f"[Stylometry] Chronobiologie — tz_estimée={chrono_profile.estimated_timezone}, "
            f"pattern={chrono_profile.work_pattern}"
        )

    # ─── 5. Injection des résultats dans Neo4j ────────────────────
    graph = GraphService()
    _inject_stylometry_graph(
        graph=graph,
        investigation_id=investigation_id,
        entity_uid=entity_uid,
        profile=profile,
        similar_entities=similar_entities,
        chrono_profile=chrono_profile,
    )

    return {
        "success": True,
        "entity_uid": entity_uid,
        "platform": platform,
        "vector_indexed": indexed,
        "style_metrics": {
            "vocab_richness": round(profile.vocab_richness, 3),
            "avg_word_length": round(profile.avg_word_length, 2),
            "avg_sentence_length": round(profile.avg_sentence_length, 1),
            "noun_ratio": round(profile.noun_ratio, 3),
        },
        "similar_entities_count": len(similar_entities),
        "similar_entities": similar_entities[:5],
        "chronobiology": {
            "estimated_timezone": chrono_profile.estimated_timezone if chrono_profile else None,
            "work_pattern": chrono_profile.work_pattern if chrono_profile else None,
            "confidence": chrono_profile.confidence if chrono_profile else 0.0,
        } if chrono_profile else None,
    }


# ============================================================
#  INJECTION NEO4J
# ============================================================

def _inject_stylometry_graph(
    graph: GraphService,
    investigation_id: str,
    entity_uid: str,
    profile,
    similar_entities: list[dict],
    chrono_profile=None,
) -> None:
    """
    Met à jour le graphe Neo4j avec les résultats stylistiques.

    Nœuds mis à jour :
      - L'entité cible reçoit ses métriques stylistiques comme propriétés
    Relations créées :
      - (entity_a)-[:SAME_AUTHOR {similarity, confidence_label, method}]->(entity_b)
      - Si score >= 0.82 : relation STRONG_SAME_AUTHOR (pivot prioritaire)
    """
    # Mise à jour du nœud cible avec les métriques
    style_props = {
        "uid": entity_uid,
        "style_vocab_richness":  round(profile.vocab_richness, 4),
        "style_avg_word_length": round(profile.avg_word_length, 2),
        "style_avg_sent_length": round(profile.avg_sentence_length, 1),
        "style_noun_ratio":      round(profile.noun_ratio, 3),
        "style_ellipsis_freq":   round(profile.ellipsis_freq, 4),
        "style_caps_ratio":      round(profile.caps_ratio, 4),
        "investigation_id": investigation_id,
    }
    if chrono_profile:
        style_props["chrono_timezone"]    = chrono_profile.estimated_timezone or ""
        style_props["chrono_work_pattern"] = chrono_profile.work_pattern
        style_props["chrono_confidence"]   = round(chrono_profile.confidence, 2)
        style_props["chrono_active_hours"] = str(chrono_profile.active_hours)

    graph.upsert_node(label="SocialProfile", properties=style_props)

    # Relations SAME_AUTHOR
    for match in similar_entities:
        similarity = match["similarity"]
        rel_type = "STRONG_SAME_AUTHOR" if similarity >= 0.82 else "POSSIBLE_SAME_AUTHOR"

        graph.upsert_relation(
            from_uid=entity_uid,
            to_uid=match["entity_uid"],
            relation_type=rel_type,
            properties={
                "method":           "stylometry_vector_cosine",
                "similarity_score": similarity,
                "confidence_label": match["confidence_label"],
                "source":           "stylometry_module",
                # Explication lisible pour l'enquêteur
                "explanation": (
                    f"Similarité cosinus {similarity:.1%} sur embedding stylistique 788d. "
                    f"Plateformes : {match.get('platform', '?')}"
                ),
            }
        )
        logger.info(
            f"[Stylometry] Lien {rel_type} : {entity_uid} → {match['entity_uid']} "
            f"(score={similarity:.3f})"
        )


# ============================================================
#  TÂCHE : Cross-Platform Avatar Matching
# ============================================================

@celery_app.task(
    bind=True,
    name="app.tasks.stylometry.run_avatar_matching",
    max_retries=2,
    queue="geoint",
    soft_time_limit=60,
)
def run_avatar_matching(
    self,
    investigation_id: str,
    entity_uid: str,
    image_path: str,
    source_url: str,
    platform: str,
) -> dict:
    """
    Extrait l'embedding facial d'une photo de profil et
    recherche les avatars similaires cross-platform dans Milvus.

    Détecte : recadrage, filtres, modifications légères d'une même photo.
    """
    from app.services.vector_db import extract_face_embedding, VectorDBService
    import hashlib, os

    logger.info(f"[AvatarMatch] Analyse image — entity={entity_uid}, source={source_url}")

    # Extraction de l'embedding facial
    face_vector = extract_face_embedding(image_path)
    if not face_vector:
        return {"success": False, "reason": "Aucun visage détecté dans l'image"}

    # Hash de l'image
    with open(image_path, "rb") as f:
        image_hash = hashlib.sha256(f.read()).hexdigest()

    # Indexation dans Milvus
    vdb = VectorDBService()
    vdb.upsert_face_vector(
        entity_uid=entity_uid,
        image_hash=image_hash,
        source_url=source_url,
        platform=platform,
        vector=face_vector,
    )

    # Recherche de visages similaires
    similar_faces = vdb.search_similar_face(
        query_vector=face_vector,
        top_k=5,
        min_similarity=0.75,
    )

    logger.info(f"[AvatarMatch] {len(similar_faces)} correspondances faciales trouvées")

    # Injection Neo4j
    if similar_faces:
        graph = GraphService()
        for match in similar_faces:
            graph.upsert_relation(
                from_uid=entity_uid,
                to_uid=match["entity_uid"],
                relation_type="SAME_FACE",
                properties={
                    "method":     "arcface_insightface",
                    "similarity": match["similarity"],
                    "source_platform":  platform,
                    "matched_platform": match["platform"],
                    "source": "avatar_matching_module",
                    "explanation": (
                        f"Similarité faciale ArcFace {match['similarity']:.1%}. "
                        f"Plateformes : {platform} ↔ {match['platform']}"
                    ),
                }
            )

    return {
        "success": True,
        "entity_uid": entity_uid,
        "platform": platform,
        "similar_faces_count": len(similar_faces),
        "matches": similar_faces,
    }
