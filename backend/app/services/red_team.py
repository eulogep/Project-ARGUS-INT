# ==============================================================================
# Project ARGUS-INT - Multi-Spectrum Intelligence Fusion Platform
# ==============================================================================
# Copyright (C) 2026 eulogep
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
ARGUS-INT — Red Teaming AI Service (Anti-Bias Analysis)
backend/app/services/red_team.py

Analyse cognitive de l'enquête pour détruire les biais de confirmation de l'opérateur.
S'appuie sur le LLM local (Ollama) et le graphe Neo4j.
"""

import logging
import httpx
from typing import List, Dict
from app.config import settings
from app.services.graph import GraphService

logger = logging.getLogger(__name__)


class RedTeamingService:
    """
    Analyseur cognitif anti-biais basé sur l'IA souveraine locale.
    """

    def __init__(self):
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.graph = GraphService()

    def challenge_investigation(self, investigation_id: str) -> str:
        """
        Analyse le graphe complet d'une investigation et génère un rapport
        de red-teaming cognitif visant à pointer les failles logiques.
        """
        logger.info(f"[RedTeam] Début de l'analyse anti-biais pour {investigation_id}")
        
        # 1. Récupérer toutes les entités et relations du graphe
        graph_data = self.graph.export_investigation_graph(investigation_id)
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        if not nodes:
            return "Aucune entité trouvée dans le graphe pour cette investigation. Impossible de challenger."

        # 2. Formater les données du graphe pour le LLM
        graph_summary = self._serialize_graph_for_llm(nodes, edges)

        # 3. Construire le prompt de Red Teaming
        prompt = f"""Tu es un analyste CTI Senior spécialiste de la méthodologie ACH (Analysis of Competing Hypotheses).
Ton objectif est de détruire les biais de confirmation de l'enquêteur en challengeant rigoureusement le graphe de liens ci-dessous.

Voici les faits et liens détectés dans l'enquête :
{graph_summary}

Analyse critique requise :
1. **Biais de confirmation détectés** : Quels liens reposent sur trop peu de preuves ou des sources non fiables ? (ex: similarité stylistique faible, IP partagée sans confirmation, etc.)
2. **Faiblesses logiques et maillons faibles** : Identifie les relations clés qui, si elles s'avéraient fausses, détruiraient toute la théorie de l'enquête.
3. **Hypothèses alternatives (L'avocat du diable)** : Propose au moins deux autres explications plausibles pour expliquer ce regroupement de comptes/adresses (ex: VPN partagé, faux nez, usurpation d'identité volontaire).
4. **Questions clés non résolues** : Quelles vérifications cruciales l'enquêteur doit-il faire pour confirmer ou réfuter ces hypothèses ?

Sois extrêmement rigoureux, analytique, direct et sans concession. Rédige en français sous forme de rapport professionnel structuré.
"""

        # 4. Requête Ollama local
        try:
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.4,
                        "num_predict": 1024
                    }
                },
                timeout=180.0
            )
            response.raise_for_status()
            report = response.json().get("response", "Aucun rapport généré par le LLM.")
            
            # Enregistrer le rapport de Red Teaming dans la base relationnelle
            self._save_red_team_report(investigation_id, report)
            
            logger.info(f"[RedTeam] Analyse terminée avec succès pour {investigation_id}")
            return report
            
        except Exception as e:
            logger.error(f"[RedTeam] Échec de la génération du rapport Ollama : {e}")
            return f"Erreur lors de la génération du rapport anti-biais : {e}"

    def _serialize_graph_for_llm(self, nodes: List[Dict], edges: List[Dict]) -> str:
        """
        Sérialise de manière compacte et claire le graphe sous forme textuelle.
        """
        lines = ["--- ENTITÉS ---"]
        for node in nodes:
            node_id = node.get("id")
            label = node.get("label")
            props = node.get("data", {})
            # Cacher les données brutes hautement sensibles
            props_filtered = {k: v for k, v in props.items() if not k.endswith("_enc") and k != "uid"}
            lines.append(f"- [{label}] {node_id} ({props_filtered})")

        lines.append("\n--- RELATIONS ---")
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            rel_type = edge.get("type")
            props = edge.get("data", {})
            lines.append(f"- {source} -[:{rel_type} {props}]-> {target}")

        return "\n".join(lines)

    def _save_red_team_report(self, investigation_id: str, report: str):
        """Met à jour l'investigation dans Postgres avec le rapport anti-biais."""
        from app.database import get_db_session_sync
        try:
            with get_db_session_sync() as db:
                db.execute(
                    """UPDATE investigations 
                       SET red_team_critique = $1 
                       WHERE id = $2""",
                    report, investigation_id
                )
        except Exception as e:
            logger.warning(f"[RedTeam] Impossible d'enregistrer le rapport en base : {e}")
