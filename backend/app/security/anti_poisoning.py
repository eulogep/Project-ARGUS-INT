# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Anti-Poisoning pour Milvus
backend/app/security/anti_poisoning.py

Module d'analyse statistique des batchs de vecteurs avant insertion.
Détecte le Cluster Collapse (données dupliquées) et les Outliers (Isolation Forest)
pour prévenir la corruption de la mémoire vectorielle de l'essaim.
Latence cible : < 50ms par batch de 1000 vecteurs.
"""
from __future__ import annotations

from typing import Any, Dict, List
import structlog

logger = structlog.get_logger(__name__)

class AntiPoisoningEngine:
    """Moteur de détection de data poisoning pour les embeddings Milvus."""

    def __init__(self, contamination_rate: float = 0.05) -> None:
        """
        Args:
            contamination_rate: Taux d'anomalies attendu pour l'Isolation Forest.
        """
        self.contamination = contamination_rate

    def analyze_batch(self, vectors: List[List[float]]) -> Dict[str, Any]:
        """
        Analyse un batch de vecteurs (ex: 512d ou 768d).
        Retourne un dictionnaire avec le statut: 'clean', 'poisoned' ou 'suspicious'.
        """
        if len(vectors) < 10:
            return {"status": "clean", "reason": "batch too small for statistical analysis"}

        try:
            import numpy as np
            from sklearn.ensemble import IsolationForest
            
            arr = np.array(vectors, dtype=np.float32)
            # Normalisation L2 rapide
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            arr_norm = arr / (norms + 1e-9)

            # 1. Détection de Cluster Collapse (Similarité cosinus élevée sur un échantillon)
            # Pour respecter <50ms, on échantillonne max 200 vecteurs.
            sample_size = min(len(arr_norm), 200)
            if sample_size < len(arr_norm):
                idx = np.random.choice(len(arr_norm), sample_size, replace=False)
                sample = arr_norm[idx]
            else:
                sample = arr_norm

            # Matrice de similarité cosinus (dot product de vecteurs normalisés)
            sim_matrix = np.dot(sample, sample.T)
            # Ignorer la diagonale (similarité avec soi-même = 1.0)
            np.fill_diagonal(sim_matrix, 0)
            
            # Ratio de paires ayant une similarité > 0.95
            collapse_ratio = np.sum(sim_matrix > 0.95) / (sample_size * (sample_size - 1))
            
            if collapse_ratio > 0.30:
                logger.warning(
                    "anti_poisoning.cluster_collapse_detected", 
                    ratio=round(collapse_ratio, 3),
                    batch_size=len(vectors)
                )
                return {
                    "status": "poisoned", 
                    "reason": "cluster_collapse", 
                    "ratio": float(collapse_ratio)
                }

            # 2. Détection d'Outliers (Isolation Forest)
            iso = IsolationForest(
                contamination=self.contamination,
                n_jobs=-1,  # Utilise tous les coeurs CPU disponibles
                random_state=42
            )
            # -1 = outlier, 1 = inlier
            preds = iso.fit_predict(arr_norm)
            outlier_ratio = np.sum(preds == -1) / len(arr_norm)

            if outlier_ratio > 0.20:
                logger.warning(
                    "anti_poisoning.high_outliers_detected", 
                    ratio=round(outlier_ratio, 3),
                    batch_size=len(vectors)
                )
                return {
                    "status": "suspicious", 
                    "reason": "high_outlier_ratio", 
                    "ratio": float(outlier_ratio)
                }

            return {"status": "clean"}

        except ImportError:
            logger.error("anti_poisoning.missing_dependencies", module="numpy or scikit-learn")
            # En cas de manque de libs, on autorise pour ne pas bloquer, mais on logge.
            return {"status": "clean", "reason": "analysis bypassed (missing deps)"}
        except Exception as exc:
            logger.error("anti_poisoning.analysis_error", error=str(exc))
            return {"status": "clean", "reason": f"error: {str(exc)}"}
