# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Panic Router (Endpoint caché d'auto-destruction)
backend/app/routers/panic.py

Permet de déclencher nuke.sh via un appel API authentifié par un token jetable.
Cet endpoint ne devrait PAS être documenté dans OpenAPI.
"""
from __future__ import annotations

import os
import subprocess
import structlog
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks

logger = structlog.get_logger(__name__)

# include_in_schema=False pour cacher cet endpoint de la doc Swagger/ReDoc
router = APIRouter(prefix="/api/v1/system", tags=["System"], include_in_schema=False)

def execute_nuke_script():
    """Exécute le script d'auto-destruction en arrière-plan."""
    nuke_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../scripts/nuke.sh"))
    if not os.path.exists(nuke_path):
        logger.error("panic.nuke_script_missing", path=nuke_path)
        return
        
    logger.critical("panic.EXECUTING_NUKE_SCRIPT")
    
    # Nous devons passer l'environnement pour que le script accepte de s'exécuter
    env = os.environ.copy()
    env["ARGUS_ENV"] = "production"
    env["CONFIRM_NUKE"] = "YES"
    
    try:
        # Exécution asynchrone non-bloquante
        subprocess.Popen(
            ["sudo", "bash", nuke_path],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as exc:
        logger.error("panic.nuke_execution_failed", error=str(exc))

@router.post("/panic")
async def trigger_panic_wipe(
    background_tasks: BackgroundTasks,
    x_panic_token: str = Header(..., description="Jeton cryptographique à usage unique")
):
    """
    DÉCLENCHE LE PANIC WIPE DE L'INFRASTRUCTURE.
    Cette action est IRREVERSIBLE et détruit le serveur.
    """
    
    # Le token devrait idéalement être validé contre une liste de hashs à usage unique
    # stockés sécuritairement ou générés par un OTP hardware (YubiKey).
    expected_token = os.getenv("PANIC_WIPE_TOKEN")
    
    if not expected_token:
        # Si le système n'est pas configuré pour le nuke, on échoue silencieusement ou avec erreur.
        logger.warning("panic.token_not_configured")
        raise HTTPException(status_code=403, detail="Forbidden")

    import hmac
    import secrets
    
    # Comparaison en temps constant pour éviter les attaques temporelles
    if not hmac.compare_digest(x_panic_token.encode(), expected_token.encode()):
        logger.warning("panic.invalid_token_attempt")
        raise HTTPException(status_code=403, detail="Forbidden")

    logger.critical("panic.TOKEN_ACCEPTED_INITIATING_WIPE")
    
    # Lancement du nuke en tâche de fond pour permettre à la requête HTTP de retourner immédiatement
    background_tasks.add_task(execute_nuke_script)
    
    return {"status": "Goodbye."}
