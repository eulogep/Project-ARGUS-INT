# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Heartbeat Router
backend/app/routers/heartbeat.py

Endpoint pour recevoir le signal de vie du Dead Man's Switch.
Protégé contre les Replay Attacks via HMAC-SHA256, timestamp et nonce.
"""
from __future__ import annotations

import os
import time
import hmac
from fastapi import APIRouter, Header, HTTPException, Body
from pydantic import BaseModel, Field
import structlog

from app.security.deadman import deadman_switch

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/system", tags=["System"], include_in_schema=False)

class HeartbeatPayload(BaseModel):
    nonce: str = Field(..., description="Valeur aléatoire unique pour prévenir le replay")
    timestamp: int = Field(..., description="Timestamp UNIX de l'envoi")

@router.post("/heartbeat")
async def receive_heartbeat(
    payload: HeartbeatPayload = Body(...),
    x_signature: str = Header(..., description="Signature HMAC-SHA256(nonce:timestamp, secret)")
) -> dict[str, str]:
    """Reçoit un ping pour réinitialiser le timer du Dead Man's Switch."""
    
    secret = os.getenv("DEADMAN_SECRET_KEY")
    if not secret:
        logger.error("heartbeat.secret_not_configured")
        raise HTTPException(status_code=500, detail="Dead Man's Switch not configured")

    # 1. Vérification temporelle (fenêtre de 5 minutes max)
    now = int(time.time())
    if abs(now - payload.timestamp) > 300:
        logger.warning("heartbeat.replay_timestamp_rejected", nonce=payload.nonce, delta=now - payload.timestamp)
        raise HTTPException(status_code=403, detail="Timestamp expired or too far in future")

    # 2. Vérification du Nonce via Redis pour empêcher la réutilisation
    try:
        r = await deadman_switch.get_redis()
        nonce_key = f"argus:security:deadman:nonce:{payload.nonce}"
        # On utilise setnx (set if not exists) et on expire dans 600s
        is_new = await r.set(nonce_key, "1", ex=600, nx=True)
        if not is_new:
            logger.warning("heartbeat.nonce_reused", nonce=payload.nonce)
            raise HTTPException(status_code=403, detail="Nonce already used")
    except Exception as exc:
        logger.error("heartbeat.redis_error", error=str(exc))
        raise HTTPException(status_code=500, detail="Internal state error")

    # 3. Vérification cryptographique de la signature (Constant Time)
    msg = f"{payload.nonce}:{payload.timestamp}".encode('utf-8')
    expected_sig = hmac.new(secret.encode('utf-8'), msg, "sha256").hexdigest()
    
    if not hmac.compare_digest(x_signature, expected_sig):
        logger.warning("heartbeat.invalid_signature", nonce=payload.nonce)
        raise HTTPException(status_code=403, detail="Invalid signature")

    # 4. Enregistrement
    await deadman_switch.record_heartbeat()
    
    return {"status": "alive", "acknowledged": True}
