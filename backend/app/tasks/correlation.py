"""
PHYNX — Tâche de corrélation finale
backend/app/tasks/correlation.py

Exécutée après le chord Celery (tous les collectors terminés).
Lance l'analyse sémantique LLM locale et génère les suggestions de pivots.
"""
import logging
import httpx
from app.celery_app import celery_app
from app.services.graph import GraphService
from app.database import get_db_session_sync
from app.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.correlation.run_graph_correlation",
    queue="identity",  # Exécuté sur le worker principal
    max_retries=2,
)
def run_graph_correlation(self, collector_results: list, investigation_id: str) -> dict:
    """
    Callback final du chord Celery.
    Reçoit les résultats de tous les collectors et lance la corrélation.

    1. Analyse sémantique via LLM local (Ollama)
    2. Détection d'entités supplémentaires (NER)
    3. Calcul des scores de pivot Neo4j
    4. Génération du résumé d'investigation
    5. Mise à jour du statut en base
    """
    logger.info(f"[Correlation] Démarrage post-collecte — investigation={investigation_id}")

    total_results = sum(
        r.get("raw_count", 0) for r in (collector_results or []) if isinstance(r, dict)
    )

    graph = GraphService()

    # ─── Extraction du nœud cible principal ──────────────────────────
    pivots = []
    with graph.driver.session() as session:
        result = session.run(
            "MATCH (n {investigation_id: $inv_id}) RETURN n.uid as uid LIMIT 1",
            inv_id=investigation_id
        )
        record = result.single()
        if record:
            pivots = graph.get_pivot_suggestions(record["uid"], max_depth=2)

    # ─── Analyse LLM locale (Ollama) ─────────────────────────────────
    llm_summary = _run_llm_analysis(investigation_id, collector_results)

    # ─── Export graphe complet ────────────────────────────────────────
    graph_export = graph.export_investigation_graph(investigation_id)

    # ─── Mise à jour PostgreSQL ───────────────────────────────────────
    with get_db_session_sync() as db:
        db.execute(
            """UPDATE investigations
               SET status = 'COMPLETED',
                   result_count = $1,
                   pivot_suggestions = $2,
                   llm_summary = $3,
                   completed_at = NOW()
               WHERE id = $4""",
            total_results,
            str(pivots),
            llm_summary,
            investigation_id
        )

    logger.info(
        f"[Correlation] Investigation {investigation_id} terminée — "
        f"{total_results} résultats, {len(pivots)} pivots suggérés"
    )

    return {
        "investigation_id": investigation_id,
        "total_results": total_results,
        "graph_stats": {
            "nodes": len(graph_export.get("nodes", [])),
            "edges": len(graph_export.get("edges", [])),
        },
        "pivots": pivots[:5],
        "llm_summary": llm_summary,
    }


def _run_llm_analysis(investigation_id: str, collector_results: list) -> str:
    """
    Appelle Ollama (LLM local souverain) pour une analyse sémantique.
    Aucune donnée ne quitte l'infrastructure locale.
    """
    try:
        # Prépare le contexte pour le LLM
        context_parts = []
        for result in (collector_results or []):
            if not isinstance(result, dict):
                continue
            if result.get("profiles"):
                context_parts.append(
                    f"Profils trouvés : {len(result['profiles'])} plateformes — "
                    + ", ".join(p.get("platform", "") for p in result["profiles"][:10])
                )
            if result.get("email_services"):
                context_parts.append(
                    f"Services email : "
                    + ", ".join(s.get("service", "") for s in result["email_services"][:10])
                )
            if result.get("mentions"):
                context_parts.append(
                    f"Mentions Dark Web : {len(result['mentions'])} résultats"
                )

        context = "\n".join(context_parts) if context_parts else "Aucun résultat collecté."

        prompt = f"""Tu es un analyste CTI expert. Analyse ces données OSINT et fournis :
1. Un résumé de l'empreinte numérique détectée (2-3 phrases)
2. Les points d'intérêt majeurs
3. Les risques ou signaux d'alerte identifiés
4. 3 recommandations de pivots d'investigation

Données collectées :
{context}

Réponse concise et factuelle en français :"""

        response = httpx.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 512,
                }
            },
            timeout=120.0
        )
        response.raise_for_status()
        return response.json().get("response", "Analyse LLM indisponible.")

    except Exception as e:
        logger.warning(f"[LLM] Ollama indisponible : {e}")
        return f"Analyse automatique : {len(collector_results or [])} modules exécutés."
