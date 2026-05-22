# ==============================================================================
# Project ARGUS-INT - Reports Router (FastAPI)
# ==============================================================================

from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/")
async def get_reports():
    """
    Récupère la liste des rapports générés.
    """
    return []
