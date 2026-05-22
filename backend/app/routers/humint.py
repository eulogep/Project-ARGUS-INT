# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — API Router pour le pretexting et l'exécution HUMINT
backend/app/routers/humint.py
"""
from __future__ import annotations

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import structlog

from app.cognitive.humint.persona_generator import generate_persona, PersonaProfile
from app.cognitive.humint.stylometry_adapter import build_style_instructions
from app.cognitive.humint.message_drafter import draft_message
from app.cognitive.humint.approval_queue import ApprovalQueue
from app.services.execution.humint_executor import HumintExecutor
from app.services.execution.noise_generator import NoiseGenerator

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/humint", tags=["HUMINT Operations"])

# ==============================================================================
#  MODÈLES DE DONNÉES
# ==============================================================================

class DraftRequest(BaseModel):
    investigation_id: str
    agent_id: str
    persona_username: str
    persona_background: str
    target_platform: str
    objective: str
    target_context: str
    target_corpus: Optional[List[str]] = Field(default=None, description="Corpus de textes cibles pour adaptation stylométrique")

class ApproveRequest(BaseModel):
    approved_by: str = Field(..., description="Nom/ID de l'opérateur effectuant la validation")
    dry_run: bool = Field(default=False, description="Si True, simule l'envoi pour test (dry-run)")
    generate_noise: bool = Field(default=True, description="Si True, génère du trafic réseau de bruit avant l'action")

class RejectRequest(BaseModel):
    rejected_by: str
    reason: str

class PersonaRequest(BaseModel):
    investigation_id: str
    platform: str
    context: str
    target_style: str = "casual"

# ==============================================================================
#  ENDPOINTS
# ==============================================================================

@router.post("/persona")
async def api_generate_persona(request: PersonaRequest) -> dict[str, Any]:
    """
    Génère un profil de persona complet et cohérent pour infiltrer une cible spécifique.
    """
    logger.info("api.humint.persona.generate", investigation=request.investigation_id, platform=request.platform)
    persona = await generate_persona(
        investigation_id=request.investigation_id,
        platform=request.platform,
        context=request.context,
        target_style=request.target_style
    )
    if not persona:
        raise HTTPException(status_code=500, detail="Échec de génération du persona par le LLM")
    return {"status": "success", "persona": persona.model_dump()}

@router.post("/draft")
async def create_draft(request: DraftRequest) -> dict[str, Any]:
    """
    Génère un brouillon de message HUMINT et le place dans la file d'attente d'approbation (PostgreSQL).
    Si un target_corpus est fourni, adapte stylométriquement le registre de langue.
    """
    logger.info("api.humint.draft", investigation=request.investigation_id, agent=request.agent_id)
    
    style_instructions = ""
    if request.target_corpus:
        style_instructions = build_style_instructions(request.target_corpus)
        
    draft = await draft_message(
        investigation_id=request.investigation_id,
        persona_username=request.persona_username,
        persona_background=request.persona_background,
        target_platform=request.target_platform,
        objective=request.objective,
        target_context=request.target_context,
        style_instructions=style_instructions
    )
    
    if not draft:
        raise HTTPException(status_code=500, detail="Échec de la génération du message")
        
    msg_id = await ApprovalQueue.enqueue(
        investigation_id=request.investigation_id,
        agent_id=request.agent_id,
        persona_name=request.persona_username,
        target_platform=request.target_platform,
        target_context=request.target_context,
        generated_message=draft.generated_message,
        style_score=draft.style_score
    )
    
    return {
        "status": "pending_approval",
        "message_id": msg_id,
        "draft": draft.model_dump(exclude={"raw_prompt"})
    }

@router.get("/pending")
async def list_pending_messages(investigation_id: Optional[str] = Query(default=None)) -> List[dict[str, Any]]:
    """
    Récupère la liste des messages de pretexting en attente d'approbation humaine.
    """
    return await ApprovalQueue.get_pending(investigation_id)

@router.post("/{id}/approve")
async def approve_message(id: str, request: ApproveRequest) -> dict[str, Any]:
    """
    HITL - Valide un message et déclenche son envoi via ProxyRouter (Tor/SOCKS5).
    """
    logger.info("api.humint.approve", msg_id=id, operator=request.approved_by, dry_run=request.dry_run)
    
    # 1. Vérifier si le message existe et est PENDING
    msg = await ApprovalQueue.get_by_id(id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message non trouvé")
        
    if msg["status"] != "PENDING":
        raise HTTPException(status_code=400, detail=f"Le message n'est pas en statut PENDING (actuel: {msg['status']})")

    # 2. Approuver le message en base
    success = await ApprovalQueue.approve(id, request.approved_by)
    if not success:
        raise HTTPException(status_code=500, detail="Impossible de mettre à jour le statut du message")
        
    # 3. Optionnel : Générer du trafic réseau de bruit pour couverture
    if request.generate_noise and not request.dry_run:
        noise = NoiseGenerator()
        # Envoie un burst asynchrone pour ne pas ralentir la réponse de validation de l'opérateur
        import asyncio
        asyncio.create_task(noise.run_noise_burst(count=3, before_action=True))

    # 4. Déclencher l'exécuteur réseau
    executor = HumintExecutor(investigation_id=msg["investigation_id"])
    result = await executor.send_approved(
        msg_id=id,
        approved_by=request.approved_by,
        dry_run=request.dry_run
    )
    
    return {
        "message_id": id,
        "execution_result": result
    }

@router.post("/{id}/reject")
async def reject_message(id: str, request: RejectRequest) -> dict[str, Any]:
    """
    Rejette et annule définitivement un message de pretexting en attente.
    """
    logger.info("api.humint.reject", msg_id=id, operator=request.rejected_by)
    success = await ApprovalQueue.reject(id, request.rejected_by, request.reason)
    if not success:
        raise HTTPException(status_code=400, detail="Impossible de rejeter ce message")
    return {"status": "rejected", "message_id": id}
