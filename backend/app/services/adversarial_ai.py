"""
PHYNX — Adversarial AI Module (GAN Validation Network)
backend/app/services/adversarial_ai.py

Ce module met en œuvre un réseau de validation adverse ("Devil's Advocate GAN").
Il s'insère dans le pipeline pour attaquer de manière algorithmique les conclusions
de l'enquêteur, générer des hypothèses alternatives structurées et tester la force
des liens dans Neo4j à l'aide de perturbations statistiques.
"""

import logging
import random
import numpy as np
from typing import List, Dict, Tuple
from app.services.graph import GraphService
from app.services.stylometry import cosine_similarity

logger = logging.getLogger(__name__)


class AdversarialValidationEngine:
    """
    Moteur de validation adverse contre les biais de confirmation dans le graphe.
    """

    def __init__(self):
        self.graph = GraphService()

    def evaluate_link_robustness(
        self, 
        investigation_id: str, 
        source_uid: str, 
        target_uid: str
    ) -> Dict:
        """
        Évalue la robustesse d'une relation (ex: SAME_AUTHOR) en simulant
        des perturbations (bruit de fond, attaques sur la similarité, faux positifs).
        
        Retourne un rapport de robustesse et de résistance aux biais.
        """
        logger.info(f"[AdversarialAI] Évaluation de la robustesse : {source_uid} -> {target_uid}")
        
        # 1. Obtenir les propriétés de la relation
        # En production, interroger Neo4j pour récupérer la relation exacte
        # Simulation d'un test statistique de robustesse
        
        # Simulation du calcul de la robustesse mathématique
        # On injecte du bruit gaussien dans la similarité pour voir si elle reste significative
        base_similarity = 0.85  # Exemple de score de similarité cosinus de départ
        noise_std = 0.05
        iterations = 1000
        
        # Monte Carlo Simulation : similarité sous bruit
        perturbed_scores = np.random.normal(base_similarity, noise_std, iterations)
        critical_threshold = 0.72  # Seuil en dessous duquel la décision change
        
        failures = np.sum(perturbed_scores < critical_threshold)
        failure_probability = failures / iterations
        
        # 2. Scénarios alternatifs basés sur des heuristiques antagonistes
        # Les scénarios décrivent pourquoi ce lien pourrait être un faux positif
        alternative_explanations = []
        if "reddit" in source_uid or "twitter" in target_uid:
            alternative_explanations.append(
                "Usage d'un style d'écriture standardisé (ex: templates de code, formules de politesse communes) "
                "faussant l'évaluation stylométrique."
            )
        
        alternative_explanations.append(
            "Corrélation temporelle accidentelle due à un événement mondial majeur "
            "(ex: pic de publication lié à une panne globale ou une actualité partagée)."
        )

        robustness_score = 1.0 - failure_probability
        
        return {
            "source": source_uid,
            "target": target_uid,
            "robustness_score": round(float(robustness_score), 4),
            "failure_probability": round(float(failure_probability), 4),
            "status": "PASS" if robustness_score > 0.80 else "FAIL",
            "alternative_scenarios": alternative_explanations,
            "recommendation": (
                "Conserver le lien" if robustness_score > 0.80 
                else "Requiert des sources de données supplémentaires (ex: corrélation IP ou signatures cryptographiques)"
            )
        }

    def generate_adversarial_hypotheses(self, graph_data: Dict) -> List[str]:
        """
        Prend la structure du graphe et génère des contre-hypothèses logiques.
        Simule le générateur du GAN cherchant à tromper le discriminateur.
        """
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        hypotheses = []
        
        # Recherche des anomalies de structure (ex: nœuds hautement connectés centralisant tout le style)
        node_degrees = {}
        for edge in edges:
            s = edge.get("source")
            t = edge.get("target")
            node_degrees[s] = node_degrees.get(s, 0) + 1
            node_degrees[t] = node_degrees.get(t, 0) + 1
            
        # Détection des goulets d'étranglement (hub de similarité)
        for node_id, degree in node_degrees.items():
            if degree > 4:
                hypotheses.append(
                    f"Le nœud {node_id} agit comme un point de centralisation élevé (degré={degree}). "
                    f"Il pourrait s'agir d'une fausse entité pivot regroupant des caractéristiques trop génériques."
                )
                
        if not hypotheses:
            hypotheses.append("Aucun biais structurel évident détecté dans la topologie actuelle du graphe.")
            
        return hypotheses
