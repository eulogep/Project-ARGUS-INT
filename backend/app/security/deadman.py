# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Dead Man's Switch
backend/app/security/deadman.py

Service tournant en tâche de fond pour surveiller la réception d'un heartbeat.
Si le heartbeat n'est pas reçu dans le délai imparti (48h par défaut),
le système déclenche le script d'auto-destruction (nuke.sh).
Résiste aux redémarrages (état dans Redis).
"""
from __future__ import annotations

import os
import time
import asyncio
import subprocess
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# Par défaut : 48 heures (converti en secondes)
DEADMAN_TIMEOUT_SEC = int(os.getenv("DEADMAN_TIMEOUT_HOURS", "48")) * 3600

class DeadManSwitch:
    """Surveillance du Heartbeat pour déclenchement du Panic Wipe."""

    def __init__(self) -> None:
        self.last_heartbeat_key = "argus:security:deadman:last_heartbeat"

    async def get_redis(self) -> Any:
        import redis.asyncio as redis
        return redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=0,
            decode_responses=True
        )

    async def record_heartbeat(self) -> None:
        """Enregistre le heartbeat actuel dans Redis."""
        now = time.time()
        try:
            r = await self.get_redis()
            await r.set(self.last_heartbeat_key, str(now))
            logger.info("deadman.heartbeat_recorded", timestamp=now)
        except Exception as exc:
            logger.error("deadman.redis_error", error=str(exc))

    async def get_last_heartbeat(self) -> float:
        """Récupère le timestamp du dernier heartbeat."""
        try:
            r = await self.get_redis()
            val = await r.get(self.last_heartbeat_key)
            if val:
                return float(val)
        except Exception as exc:
            logger.error("deadman.redis_error", error=str(exc))
        
        # Si aucun heartbeat n'est trouvé, on initialise à 'maintenant'
        # pour éviter un déclenchement immédiat au premier démarrage.
        now = time.time()
        await self.record_heartbeat()
        return now

    async def monitor_loop(self) -> None:
        """Boucle de surveillance asynchrone (à exécuter dans un thread/task séparé)."""
        logger.info("deadman.monitoring_started", timeout_hours=DEADMAN_TIMEOUT_SEC / 3600)
        while True:
            try:
                last_hb = await self.get_last_heartbeat()
                elapsed = time.time() - last_hb
                
                if elapsed > DEADMAN_TIMEOUT_SEC:
                    logger.critical(
                        "deadman.TIMEOUT_EXCEEDED", 
                        elapsed_hours=elapsed / 3600,
                        timeout_hours=DEADMAN_TIMEOUT_SEC / 3600,
                        action="TRIGGER_NUKE"
                    )
                    self._trigger_nuke()
                    break # On sort de la boucle après déclenchement
                    
            except Exception as exc:
                logger.error("deadman.monitor_error", error=str(exc))
                
            # Vérification toutes les heures
            await asyncio.sleep(3600)

    def _trigger_nuke(self) -> None:
        """Déclenche le Panic Wipe via appel subprocess du script nuke.sh."""
        nuke_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../scripts/nuke.sh"))
        if not os.path.exists(nuke_path):
            logger.error("deadman.nuke_script_missing", path=nuke_path)
            return

        env = os.environ.copy()
        env["ARGUS_ENV"] = "production"
        env["CONFIRM_NUKE"] = "YES"

        try:
            logger.critical("deadman.EXECUTING_PANIC_WIPE")
            subprocess.Popen(
                ["sudo", "bash", nuke_path],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as exc:
            logger.error("deadman.nuke_execution_failed", error=str(exc))

deadman_switch = DeadManSwitch()
