# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Deception & Honeytokens (Canaris Internes)
backend/app/security/deception.py

Mécanismes de Honeytokens pour la détection d'intrusion.
Ces tokens sont placés dans le code ou l'environnement et surveillés.
S'ils sont utilisés par un attaquant, l'alerte est donnée.
"""
from __future__ import annotations

import os
import uuid
from typing import Any
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

class Honeytoken(BaseModel):
    id: str
    token_type: str
    value: str
    description: str
    triggered: bool = False

class DeceptionEngine:
    """Moteur de gestion des Honeytokens."""

    def __init__(self):
        # Liste statique de canaris configurés
        # Dans un environnement réel, ces tokens seraient générés dynamiquement et persistés.
        self._canaries: dict[str, Honeytoken] = {}
        self._initialize_static_canaries()

    def _initialize_static_canaries(self):
        """Initialise des canaris fictifs."""
        
        # 1. Fake API Key AWS
        aws_token = Honeytoken(
            id=str(uuid.uuid4()),
            token_type="aws_access_key",
            value=os.getenv("FAKE_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE"),
            description="Fake AWS credentials left in env"
        )
        self._canaries[aws_token.value] = aws_token
        
        # 2. Fake JWT Secret
        jwt_token = Honeytoken(
            id=str(uuid.uuid4()),
            token_type="jwt_secret",
            value=os.getenv("FAKE_JWT_SECRET", "super-secret-key-12345"),
            description="Fake JWT Secret"
        )
        self._canaries[jwt_token.value] = jwt_token

    def register_canary(self, token: Honeytoken):
        self._canaries[token.value] = token
        logger.info("deception.canary_registered", type=token.token_type)

    def check_value(self, value: str) -> bool:
        """
        Vérifie si une valeur soumise correspond à un canari.
        À appeler dans les middlewares de sécurité (vérification de header Authorization, etc.)
        Renvoie True si un canari a été déclenché.
        """
        if value in self._canaries:
            canary = self._canaries[value]
            self._trigger_alert(canary)
            return True
        return False
        
    def _trigger_alert(self, canary: Honeytoken):
        """Déclenche une alerte critique."""
        if not canary.triggered:
            canary.triggered = True
            logger.critical(
                "deception.CANARY_TRIGGERED",
                canary_id=canary.id,
                type=canary.token_type,
                desc=canary.description,
                message="HONEYTOKEN ACCESSED! L'infrastructure est probablement compromise."
            )
            # Ici on pourrait déclencher l'Automated Lockdown (désactivation de l'API).

# Instance globale
deception_engine = DeceptionEngine()
