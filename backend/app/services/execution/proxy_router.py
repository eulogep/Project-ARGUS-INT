# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Proxy Router : Interface unifiée pour le trafic sortant HUMINT
backend/app/services/execution/proxy_router.py

OPSEC Règle d'Or : Aucune connexion sortante sans proxy.
Backends supportés : Tor (SOCKS5h), SOCKS5 custom, HTTP proxy, Proxy résidentiel rotatif.
Circuit breaker intégré (3 échecs → ERROR + notification opérateur).
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = structlog.get_logger(__name__)


class ProxyBackend(str, Enum):
    TOR        = "tor"
    SOCKS5     = "socks5"
    HTTP       = "http"
    RESIDENTIAL = "residential"


@dataclass
class ProxyConfig:
    backend:  ProxyBackend
    url:      str                   # ex: "socks5h://localhost:9050"
    label:    str = ""
    failures: int = 0
    last_used: float = 0.0
    is_healthy: bool = True

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= 3:
            self.is_healthy = False
            logger.warning("proxy_router.proxy_disabled", label=self.label, failures=self.failures)

    def record_success(self) -> None:
        self.failures = 0
        self.is_healthy = True
        self.last_used = time.time()


class ProxyRouter:
    """
    Routeur de proxy avec circuit breaker et rotation automatique.

    Usage :
        router = ProxyRouter()
        async with router.get_client(backend=ProxyBackend.TOR) as client:
            response = await client.get("http://example.com")
    """

    def __init__(self) -> None:
        self._proxies: list[ProxyConfig] = self._load_proxy_configs()
        self._circuit_open: bool = False
        self._circuit_open_since: float = 0.0
        self._circuit_timeout: float = 300.0  # 5 min avant réouverture

    def _load_proxy_configs(self) -> list[ProxyConfig]:
        configs: list[ProxyConfig] = []
        # Tor (toujours disponible si configuré)
        if settings.TOR_PROXY:
            configs.append(ProxyConfig(
                backend=ProxyBackend.TOR,
                url=settings.TOR_PROXY,
                label="tor-primary",
            ))
        # Proxies SOCKS5 supplémentaires depuis la config
        for proxy_dict in (settings.PROXY_LIST or []):
            url = proxy_dict.get("url", "")
            provider = proxy_dict.get("provider", "custom")
            if url:
                backend = ProxyBackend.RESIDENTIAL if "residential" in provider else ProxyBackend.SOCKS5
                configs.append(ProxyConfig(backend=backend, url=url, label=f"{provider}"))
        if not configs:
            logger.warning("proxy_router.no_proxies_configured")
        return configs

    def _get_healthy_proxy(
        self,
        preferred_backend: Optional[ProxyBackend] = None,
    ) -> Optional[ProxyConfig]:
        """Sélectionne un proxy sain, en favorisant le backend préféré."""
        healthy = [p for p in self._proxies if p.is_healthy]
        if not healthy:
            return None
        if preferred_backend:
            preferred = [p for p in healthy if p.backend == preferred_backend]
            if preferred:
                return random.choice(preferred)
        # Round-robin pondéré par ancienneté d'utilisation
        return min(healthy, key=lambda p: p.last_used)

    def is_circuit_open(self) -> bool:
        """Vérifie si le circuit breaker est ouvert (tous les proxies HS)."""
        if self._circuit_open:
            # Tentative de fermeture après timeout
            if time.time() - self._circuit_open_since > self._circuit_timeout:
                self._circuit_open = False
                for proxy in self._proxies:
                    proxy.failures = 0
                    proxy.is_healthy = True
                logger.info("proxy_router.circuit_reset")
        return self._circuit_open

    def get_client(
        self,
        backend: ProxyBackend = ProxyBackend.TOR,
        timeout: float = 30.0,
    ) -> httpx.AsyncClient:
        """
        Retourne un client httpx configuré avec le proxy sélectionné.
        Peut être utilisé comme context manager async.

        Raises:
            RuntimeError : si aucun proxy sain n'est disponible (circuit ouvert)
        """
        if self.is_circuit_open():
            raise RuntimeError("[ProxyRouter] Circuit ouvert — tous les proxies sont hors service")

        proxy = self._get_healthy_proxy(backend)
        if proxy is None:
            self._circuit_open = True
            self._circuit_open_since = time.time()
            raise RuntimeError("[ProxyRouter] Aucun proxy sain disponible — circuit ouvert")

        proxy.last_used = time.time()
        logger.debug("proxy_router.selected", label=proxy.label, backend=proxy.backend.value)

        return httpx.AsyncClient(
            proxies={"all://": proxy.url},
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            verify=False,  # Tor ne nécessite pas de validation SSL
        )

    async def check_connectivity(self, test_url: str = "http://check.torproject.org/api/ip") -> dict[str, Any]:
        """Vérifie la connectivité de tous les proxies sains."""
        results: dict[str, Any] = {}
        for proxy in self._proxies:
            if not proxy.is_healthy:
                results[proxy.label] = {"status": "disabled", "failures": proxy.failures}
                continue
            try:
                async with httpx.AsyncClient(
                    proxies={"all://": proxy.url},
                    timeout=httpx.Timeout(15.0),
                ) as client:
                    resp = await client.get(test_url)
                    data = resp.json()
                    proxy.record_success()
                    results[proxy.label] = {"status": "ok", "ip": data.get("IP", "unknown")}
            except Exception as exc:
                proxy.record_failure()
                results[proxy.label] = {"status": "failed", "error": str(exc)}
        return results

    def record_proxy_result(
        self,
        proxy_label: str,
        success: bool,
    ) -> None:
        """Enregistre le résultat d'une tentative d'envoi pour le circuit breaker."""
        for proxy in self._proxies:
            if proxy.label == proxy_label:
                if success:
                    proxy.record_success()
                else:
                    proxy.record_failure()
                    # Vérifier si tous les proxies sont HS
                    if not any(p.is_healthy for p in self._proxies):
                        self._circuit_open = True
                        self._circuit_open_since = time.time()
                        logger.error("proxy_router.circuit_opened")
                break
