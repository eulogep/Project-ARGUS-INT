"""
PHYNX — Stylometry Service : Vectorisation & Attribution d'Auteur
backend/app/services/stylometry.py

Pipeline :
  Texte brut → Feature Extraction → Embedding HuggingFace → Milvus
  + Score de similarité inter-pseudos → Neo4j

Modèles utilisés (tous locaux, zéro cloud) :
  - Embeddings sémantiques : sentence-transformers/paraphrase-multilingual-mpnet-base-v2
  - Analyse lexicale : spaCy (fr_core_news_lg + en_core_web_lg)
  - POS tagging / fréquences pour stylométrie classique
"""
import re
import logging
import statistics
import string
from collections import Counter
from typing import Optional
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)

# ─── Chargement paresseux des modèles lourds ───────────────────────────
_sentence_model = None
_spacy_models: dict = {}


def _get_sentence_model():
    """Charge le modèle d'embedding une seule fois (singleton)."""
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_model = SentenceTransformer(
                "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
            )
            logger.info("[Stylometry] Modèle sentence-transformers chargé")
        except ImportError:
            logger.warning("[Stylometry] sentence-transformers non installé")
    return _sentence_model


def _get_spacy(lang: str = "en"):
    """Charge spaCy pour la langue donnée."""
    global _spacy_models
    if lang not in _spacy_models:
        try:
            import spacy
            model_name = "fr_core_news_lg" if lang == "fr" else "en_core_web_lg"
            _spacy_models[lang] = spacy.load(model_name)
        except Exception as e:
            logger.warning(f"[Stylometry] spaCy ({lang}) indisponible : {e}")
            _spacy_models[lang] = None
    return _spacy_models[lang]


# ============================================================
#  FEATURE EXTRACTION
# ============================================================

@dataclass
class StyleProfile:
    """Vecteur stylistique complet d'un texte."""
    # Métriques lexicales
    avg_word_length: float = 0.0
    vocab_richness: float = 0.0       # Type-Token Ratio
    hapax_ratio: float = 0.0          # Mots uniques / total
    avg_sentence_length: float = 0.0
    punctuation_density: float = 0.0

    # Patterns caractéristiques
    ellipsis_freq: float = 0.0        # Fréquence des "..."
    caps_ratio: float = 0.0           # Ratio majuscules
    emoji_count: int = 0
    question_ratio: float = 0.0
    exclamation_ratio: float = 0.0

    # Distribution POS (Part-of-Speech)
    noun_ratio: float = 0.0
    verb_ratio: float = 0.0
    adj_ratio: float = 0.0
    adv_ratio: float = 0.0

    # N-grammes de caractères les plus fréquents (fingerprint)
    top_bigrams: list = field(default_factory=list)
    top_trigrams: list = field(default_factory=list)

    # Erreurs récurrentes (très discriminantes)
    common_misspellings: list = field(default_factory=list)

    # Vecteur dense (embedding sémantique 768d)
    embedding: Optional[list] = None


def extract_style_profile(text: str, lang: str = "en") -> StyleProfile:
    """
    Extrait un profil stylistique complet d'un texte.
    Combine métriques classiques (Burrows' Delta) et embeddings neuronaux.
    """
    if not text or len(text.strip()) < 50:
        return StyleProfile()

    profile = StyleProfile()
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    chars = list(text)

    # ─── Métriques lexicales ───────────────────────────────────────
    if words:
        word_lengths = [len(w.strip(string.punctuation)) for w in words if w]
        profile.avg_word_length = statistics.mean(word_lengths) if word_lengths else 0

        word_lower = [w.lower().strip(string.punctuation) for w in words]
        word_counts = Counter(word_lower)
        total_words = len(word_lower)

        profile.vocab_richness = len(word_counts) / total_words if total_words else 0
        hapax = sum(1 for c in word_counts.values() if c == 1)
        profile.hapax_ratio = hapax / total_words if total_words else 0

    if sentences:
        sent_lengths = [len(s.split()) for s in sentences]
        profile.avg_sentence_length = statistics.mean(sent_lengths) if sent_lengths else 0

    # ─── Ponctuation et patterns ───────────────────────────────────
    total_chars = len(chars)
    if total_chars:
        punct_chars = sum(1 for c in chars if c in string.punctuation)
        profile.punctuation_density = punct_chars / total_chars
        profile.caps_ratio = sum(1 for c in chars if c.isupper()) / total_chars

    profile.ellipsis_freq = text.count("...") / len(sentences) if sentences else 0
    profile.question_ratio = text.count("?") / len(sentences) if sentences else 0
    profile.exclamation_ratio = text.count("!") / len(sentences) if sentences else 0

    # ─── Emojis ────────────────────────────────────────────────────
    import unicodedata
    profile.emoji_count = sum(
        1 for c in text
        if unicodedata.category(c) in ("So", "Sm") or ord(c) > 0x1F300
    )

    # ─── N-grammes de caractères ────────────────────────────────────
    text_lower = text.lower()
    bigrams = [text_lower[i:i+2] for i in range(len(text_lower)-1)]
    trigrams = [text_lower[i:i+3] for i in range(len(text_lower)-2)]
    profile.top_bigrams = [bg for bg, _ in Counter(bigrams).most_common(10)]
    profile.top_trigrams = [tg for tg, _ in Counter(trigrams).most_common(10)]

    # ─── POS Tagging via spaCy ──────────────────────────────────────
    nlp = _get_spacy(lang)
    if nlp:
        doc = nlp(text[:5000])  # Limite pour les perfs
        total_tokens = len([t for t in doc if not t.is_space])
        if total_tokens:
            pos_counts = Counter(t.pos_ for t in doc if not t.is_space)
            profile.noun_ratio  = pos_counts.get("NOUN", 0) / total_tokens
            profile.verb_ratio  = pos_counts.get("VERB", 0) / total_tokens
            profile.adj_ratio   = pos_counts.get("ADJ", 0)  / total_tokens
            profile.adv_ratio   = pos_counts.get("ADV", 0)  / total_tokens

    # ─── Embedding dense (768 dimensions) ──────────────────────────
    model = _get_sentence_model()
    if model:
        embedding = model.encode(text[:512], normalize_embeddings=True)
        profile.embedding = embedding.tolist()

    return profile


def profile_to_feature_vector(profile: StyleProfile) -> list[float]:
    """
    Convertit un StyleProfile en vecteur numérique pour Milvus.
    Vecteur final = embedding dense (768d) + features scalaires (20d) = 788d.
    """
    scalar_features = [
        profile.avg_word_length / 10.0,      # Normalisé
        profile.vocab_richness,
        profile.hapax_ratio,
        profile.avg_sentence_length / 50.0,
        profile.punctuation_density,
        profile.ellipsis_freq,
        profile.caps_ratio,
        profile.emoji_count / 10.0,
        profile.question_ratio,
        profile.exclamation_ratio,
        profile.noun_ratio,
        profile.verb_ratio,
        profile.adj_ratio,
        profile.adv_ratio,
        len(profile.top_bigrams) / 10.0,
        len(profile.top_trigrams) / 10.0,
        len(profile.common_misspellings) / 5.0,
        0.0, 0.0, 0.0,  # Réservé pour features futures
    ]

    if profile.embedding:
        return profile.embedding + scalar_features
    return [0.0] * 768 + scalar_features


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Calcule la similarité cosinus entre deux vecteurs."""
    a = np.array(vec_a)
    b = np.array(vec_b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ============================================================
#  CHRONOBIOLOGIE
# ============================================================

@dataclass
class ChronobiologyProfile:
    """Profil temporel déduit des publications."""
    active_hours: list[int] = field(default_factory=list)      # Heures UTC actives
    active_days: list[str] = field(default_factory=list)        # Jours actifs
    estimated_timezone: Optional[str] = None
    sleep_window_start: Optional[int] = None  # Heure UTC début du silence
    sleep_window_end: Optional[int] = None    # Heure UTC fin du silence
    work_pattern: str = "unknown"             # "9-5", "nocturnal", "irregular"
    confidence: float = 0.0


def analyze_chronobiology(timestamps: list) -> ChronobiologyProfile:
    """
    Analyse temporelle des publications pour déduire :
    - Fuseau horaire réel (pic d'activité vs silence nocturne)
    - Jours de repos (faible activité → indice culturel/religieux)
    - Pattern de vie (travailleur de nuit, développeur, etc.)

    timestamps : liste de datetime objects ou timestamps Unix
    """
    from datetime import datetime, timezone
    import pytz

    if not timestamps or len(timestamps) < 20:
        return ChronobiologyProfile(confidence=0.0)

    profile = ChronobiologyProfile()

    # Convertir en objets datetime UTC
    dts = []
    for ts in timestamps:
        if isinstance(ts, (int, float)):
            dts.append(datetime.fromtimestamp(ts, tz=timezone.utc))
        elif hasattr(ts, 'hour'):
            dts.append(ts)

    # Heures d'activité UTC
    hour_counts = Counter(dt.hour for dt in dts)
    day_counts = Counter(dt.strftime("%A") for dt in dts)

    profile.active_hours = sorted(hour_counts.keys())
    profile.active_days = [d for d, _ in day_counts.most_common(5)]

    # Détection de la fenêtre de silence (sommeil)
    all_hours = list(range(24))
    inactive_hours = [h for h in all_hours if hour_counts.get(h, 0) == 0]
    if inactive_hours:
        # Trouver le bloc continu le plus long = fenêtre de sommeil
        blocks = []
        current_block = [inactive_hours[0]]
        for h in inactive_hours[1:]:
            if h == current_block[-1] + 1:
                current_block.append(h)
            else:
                blocks.append(current_block)
                current_block = [h]
        blocks.append(current_block)
        longest_block = max(blocks, key=len)
        profile.sleep_window_start = longest_block[0]
        profile.sleep_window_end = longest_block[-1]

        # Estimation du fuseau : milieu du sommeil ≈ 3h du matin locale
        # → décalage = (heure_milieu_UTC + 3) % 24
        sleep_mid = (longest_block[0] + longest_block[-1]) // 2
        offset_hours = (3 - sleep_mid) % 24
        sign = "+" if offset_hours <= 12 else "-"
        abs_offset = offset_hours if offset_hours <= 12 else 24 - offset_hours
        profile.estimated_timezone = f"UTC{sign}{abs_offset}"

    # Pattern de travail
    peak_hour = hour_counts.most_common(1)[0][0] if hour_counts else 12
    if 9 <= peak_hour <= 18:
        profile.work_pattern = "9-5_worker"
    elif 22 <= peak_hour or peak_hour <= 4:
        profile.work_pattern = "nocturnal"
    else:
        profile.work_pattern = "irregular"

    profile.confidence = min(len(timestamps) / 100.0, 1.0)
    return profile
