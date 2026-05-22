# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Noise Generator : Trafic de fond OPSEC
backend/app/services/execution/noise_generator.py

Génère du trafic réseau fictif pour noyer les actions HUMINT réelles.
Principes :
  - Variabilité temporelle (jitter aléatoire)
  - Destinations anodines (sites publics légaux)
  - Volume calibré pour ne pas surcharger le proxy
"""
from __future__ import annotations

import asyncio
import random
import time
from typing import Optional

import structlog

from app.services.execution.proxy_router import ProxyBackend, ProxyRouter

logger = structlog.get_logger(__name__)

# URLs anodines pour le trafic de bruit (sites publics, legaux)
_NOISE_TARGETS = [
    "https://www.wikipedia.org",
    "https://news.ycombinator.com",
    "https://stackoverflow.com",
    "https://github.com/trending",
    "https://reddit.com/r/technology",
    "https://archive.org",
]


class NoiseGenerator:
    """
    Génère du trafic de fond via le ProxyRouter pour masquer les actions HUMINT.

    Usage :
        ng = NoiseGenerator(proxy_router)
        await ng.run_noise_burst(before_action=True, count=5)
    """

    def __init__(self, proxy_router: Optional[ProxyRouter] = None) -> None:
        self._router = proxy_router or ProxyRouter()

    async def _make_noise_request(self) -> None:
        """Effectue une requête GET aléatoire vers une URL anodine."""
        target = random.choice(_NOISE_TARGETS)
        try:
            async with self._router.get_client(ProxyBackend.TOR, timeout=10.0) as client:
                await client.get(target, headers={"User-Agent": self._random_ua()})
            logger.debug("noise.request_ok", target=target)
        except Exception:
            pass  # Les erreurs de bruit sont silencieuses

    async def run_noise_burst(
        self,
        count: int = 5,
        min_jitter: float = 0.5,
        max_jitter: float = 3.0,
        before_action: bool = False,
    ) -> None:
        """
        Génère un burst de N requêtes de bruit.

        Args:
            count        : Nombre de requêtes à générer
            min_jitter   : Délai minimum entre requêtes (secondes)
            max_jitter   : Délai maximum entre requêtes (secondes)
            before_action: Si True, ajoute un délai final avant l'action réelle
        """
        logger.debug("noise.burst_start", count=count, before_action=before_action)
        for _ in range(count):
            await self._make_noise_request()
            jitter = random.uniform(min_jitter, max_jitter)
            await asyncio.sleep(jitter)
        if before_action:
            # Délai final aléatoire 2-8 secondes avant l'action réelle
            await asyncio.sleep(random.uniform(2.0, 8.0))
        logger.debug("noise.burst_done", count=count)

    @staticmethod
    def _random_ua() -> str:
        """Génère un User-Agent plausible aléatoire."""
        browsers = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 Safari/604.1",
            "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        ]
        return random.choice(browsers)
