# ==============================================================================
# Project ARGUS-INT - Graph Router (FastAPI)
# ==============================================================================

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.services.graph import GraphService

router = APIRouter()
graph_service = GraphService()

@router.get("/export")
async def export_graph(investigation_id: Optional[str] = Query(None, description="ID de l'investigation à filtrer")):
    """
    Exporte le graphe d'une investigation sous forme topologique compatible D3 Canvas.
    """
    try:
        # If no investigation_id, return empty list or general test data
        if not investigation_id:
            # For demonstration in full screen explorer, return global test structure
            return graph_service.export_investigation_graph("global-explorer")
            
        data = graph_service.export_investigation_graph(investigation_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'extraction du graphe: {e}")

@router.get("/pivots")
async def get_pivots(uid: str = Query(..., description="UID du nœud sélectionné")):
    """
    Suggère des entités d'ancrage (pivots) proches à investiguer.
    """
    try:
        suggestions = graph_service.get_pivot_suggestions(uid)
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de suggestion de pivots: {e}")
