# ==============================================================================
# Project ARGUS-INT - Multi-Spectrum Intelligence Fusion Platform
# ==============================================================================
# Copyright (C) 2026 emc2
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
ARGUS-INT — ProxyPool : Gestion intelligente des proxies
backend/app/services/proxy.py

Rotation et vérification des proxies (SOCKS5, HTTP, Tor, résidentiels).
"""

import asyncio
import random
import time
import httpx
import logging
from dataclasses import dataclass, field
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

TEST_URL = "https://api.ipify.org?format=json"
TEST_TIMEOUT = 10.0


@dataclass
class Proxy:
    url: str               # ex: socks5://user:pass@host:port
    provider: str          # "residential", "datacenter", "tor"
    is_healthy: bool = True
    fail_count: int = 0
    last_checked: float = field(default_factory=time.time)
    last_ip: Optional[str] = None

    def mark_failed(self):
        self.fail_count += 1
        if self.fail_count >= 3:
            self.is_healthy = False
            logger.warning(f"[ProxyPool] Proxy désactivé après 3 échecs : {self.url[:30]}...")

    def mark_success(self, ip: str):
        self.fail_count = 0
        self.is_healthy = True
        self.last_ip = ip
        self.last_checked = time.time()


class ProxyPool:
    """
    Pool de proxies avec rotation intelligente et health-check automatique.
    Intègre Tor comme proxy de fallback.
    """
    _proxies: list[Proxy] = []
    _initialized: bool = False

    def __init__(self):
        if not ProxyPool._initialized:
            self._load_proxies()
            ProxyPool._initialized = True

    def _load_proxies(self):
        """Charge la liste de proxies depuis la config / fichier."""
        proxy_list = settings.PROXY_LIST or []

        ProxyPool._proxies = [
            Proxy(url=p["url"], provider=p.get("provider", "datacenter"))
            for p in proxy_list
        ]

        # Ajoute Tor comme proxy toujours disponible
        ProxyPool._proxies.append(
            Proxy(url=settings.TOR_PROXY, provider="tor", is_healthy=True)
        )

        logger.info(f"[ProxyPool] {len(ProxyPool._proxies)} proxies chargés")

    async def get_proxy(self) -> Optional[str]:
        """
        Retourne un proxy sain de manière aléatoire.
        Priorité : résidentiels > datacenter > Tor
        """
        healthy = [p for p in ProxyPool._proxies if p.is_healthy]

        if not healthy:
            logger.warning("[ProxyPool] Aucun proxy sain — utilisation de Tor")
            return settings.TOR_PROXY

        # Pondération par type
        weights = []
        for p in healthy:
            if p.provider == "residential":
                weights.append(10)
            elif p.provider == "datacenter":
                weights.append(5)
            else:  # tor
                weights.append(1)

        selected = random.choices(healthy, weights=weights, k=1)[0]
        return selected.url

    async def health_check(self):
        """
        Vérifie la santé de tous les proxies.
        À lancer périodiquement (Celery Beat toutes les 5 min).
        """
        logger.info("[ProxyPool] Health-check démarré")

        async def check_one(proxy: Proxy):
            try:
                async with httpx.AsyncClient(
                    proxy=proxy.url,
                    timeout=httpx.Timeout(TEST_TIMEOUT),
                    verify=False
                ) as client:
                    response = await client.get(TEST_URL)
                    ip = response.json().get("ip", "unknown")
                    proxy.mark_success(ip)
            except Exception:
                proxy.mark_failed()

        await asyncio.gather(*[check_one(p) for p in ProxyPool._proxies])

        healthy_count = sum(1 for p in ProxyPool._proxies if p.is_healthy)
        logger.info(f"[ProxyPool] Health-check terminé : {healthy_count}/{len(ProxyPool._proxies)} proxies sains")

    def get_stats(self) -> dict:
        """Retourne les statistiques du pool."""
        return {
            "total": len(ProxyPool._proxies),
            "healthy": sum(1 for p in ProxyPool._proxies if p.is_healthy),
            "by_provider": {
                provider: sum(1 for p in ProxyPool._proxies if p.provider == provider and p.is_healthy)
                for provider in {"residential", "datacenter", "tor"}
            }
        }
