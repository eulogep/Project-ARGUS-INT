# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — HUMINT Executor : Envoi de messages APPROVED via ProxyRouter
backend/app/services/execution/humint_executor.py

OPSEC : Jamais d'envoi direct. Toujours via ProxyRouter.
Circuit breaker : 3 échecs proxy → ERROR + notification opérateur.
Log complet : investigation_id, proxy_used, target_platform, timestamp.
"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.services.execution.proxy_router import ProxyBackend, ProxyRouter

logger = structlog.get_logger(__name__)

# Singleton ProxyRouter
_router = ProxyRouter()


class HumintExecutionError(Exception):
    """Erreur non-récupérable lors de l'exécution HUMINT."""


class HumintExecutor:
    """
    Exécute l'envoi de messages HUMINT APPROVED via le ProxyRouter.

    Supporte :
      - HTTP POST (API Telegram, Discord webhooks)
      - SMTP (email via serveur SMTP over Tor)
      - Simulation (dry-run pour tests)
    """

    def __init__(self, investigation_id: str) -> None:
        self.investigation_id = investigation_id
        self._router = _router

    async def send_approved(
        self,
        msg_id: str,
        approved_by: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Point d'entrée principal : récupère le message APPROVED et l'envoie.

        Args:
            msg_id      : UUID du message dans humint_approvals
            approved_by : Identifiant de l'opérateur qui a approuvé
            dry_run     : Si True, simule l'envoi sans trafic réel

        Returns:
            dict avec status, proxy_used, timestamp
        """
        from app.cognitive.humint.approval_queue import ApprovalQueue
        msg = await ApprovalQueue.get_by_id(msg_id)
        if not msg:
            raise HumintExecutionError(f"Message {msg_id} introuvable")
        if msg["status"] != "APPROVED":
            raise HumintExecutionError(f"Message {msg_id} n'est pas en statut APPROVED (actuel: {msg['status']})")

        platform = msg["target_platform"]
        message_text = msg["generated_message"]

        logger.info(
            "humint_executor.sending",
            msg_id=msg_id,
            platform=platform,
            investigation=self.investigation_id,
            dry_run=dry_run,
        )

        # Sélection du backend proxy selon la plateforme
        backend = self._select_proxy_backend(platform)
        proxy_label = "dry-run" if dry_run else self._get_active_proxy_label(backend)

        if dry_run:
            result = self._simulate_send(platform, message_text)
        else:
            result = await self._execute_send(platform, message_text, backend, msg_id)

        if result["success"]:
            await ApprovalQueue.mark_sent(msg_id, proxy_label)
        else:
            await ApprovalQueue.mark_failed(msg_id, result.get("error", "unknown"))

        logger.info(
            "humint_executor.result",
            msg_id=msg_id,
            success=result["success"],
            proxy=proxy_label,
            investigation=self.investigation_id,
        )
        return {
            "msg_id":       msg_id,
            "success":      result["success"],
            "proxy_used":   proxy_label,
            "platform":     platform,
            "timestamp":    time.time(),
            "error":        result.get("error"),
            "dry_run":      dry_run,
        }

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
    )
    async def _execute_send(
        self,
        platform: str,
        message: str,
        backend: ProxyBackend,
        msg_id: str,
    ) -> dict[str, Any]:
        """Exécution réelle de l'envoi selon la plateforme."""
        try:
            if self._router.is_circuit_open():
                raise HumintExecutionError("Circuit breaker ouvert — envoi impossible")

            if platform == "telegram":
                return await self._send_telegram(message, backend)
            elif platform == "http_post":
                return await self._send_http_post(message, backend)
            elif platform == "email":
                return await self._send_email(message, backend)
            else:
                # Plateforme non implémentée → log + skip
                logger.warning("humint_executor.platform_not_implemented", platform=platform)
                return {"success": False, "error": f"platform {platform} not implemented"}
        except HumintExecutionError:
            raise
        except Exception as exc:
            self._router.record_proxy_result(self._get_active_proxy_label(backend), False)
            raise

    async def _send_telegram(self, message: str, backend: ProxyBackend) -> dict[str, Any]:
        """Envoi via l'API Telegram Bot (route via Tor)."""
        # NOTE : Le bot token est configuré par l'opérateur et n'est jamais hardcodé
        import os
        bot_token = os.getenv("HUMINT_TELEGRAM_BOT_TOKEN", "")
        chat_id   = os.getenv("HUMINT_TELEGRAM_CHAT_ID", "")
        if not bot_token or not chat_id:
            return {"success": False, "error": "Telegram credentials not configured"}
        try:
            async with self._router.get_client(backend) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                )
                if resp.status_code == 200:
                    self._router.record_proxy_result(self._get_active_proxy_label(backend), True)
                    return {"success": True, "response": resp.json()}
                return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _send_http_post(self, message: str, backend: ProxyBackend) -> dict[str, Any]:
        """Envoi HTTP POST générique (forum, API custom)."""
        import os
        endpoint = os.getenv("HUMINT_HTTP_ENDPOINT", "")
        if not endpoint:
            return {"success": False, "error": "HTTP endpoint not configured"}
        try:
            async with self._router.get_client(backend) as client:
                resp = await client.post(endpoint, json={"content": message})
                success = 200 <= resp.status_code < 300
                self._router.record_proxy_result(self._get_active_proxy_label(backend), success)
                return {"success": success, "status_code": resp.status_code}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _send_email(self, message: str, backend: ProxyBackend) -> dict[str, Any]:
        """Envoi SMTP over Tor (smtplib via proxy SOCKS5)."""
        import os
        import smtplib
        smtp_host = os.getenv("HUMINT_SMTP_HOST", "")
        smtp_port = int(os.getenv("HUMINT_SMTP_PORT", "587"))
        smtp_user = os.getenv("HUMINT_SMTP_USER", "")
        smtp_pass = os.getenv("HUMINT_SMTP_PASS", "")
        to_addr   = os.getenv("HUMINT_SMTP_TO", "")
        if not all([smtp_host, smtp_user, to_addr]):
            return {"success": False, "error": "SMTP credentials not configured"}
        try:
            import socks
            socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
            socks.wrapmodule(smtplib)
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, to_addr, f"Subject: Contact\n\n{message}")
            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    @staticmethod
    def _simulate_send(platform: str, message: str) -> dict[str, Any]:
        """Simulation d'envoi pour les tests (dry_run=True)."""
        logger.info("humint_executor.dry_run", platform=platform, msg_preview=message[:50])
        return {"success": True, "simulated": True}

    @staticmethod
    def _select_proxy_backend(platform: str) -> ProxyBackend:
        """Choisit le backend proxy selon la plateforme."""
        if platform in ("darkweb", "onion"):
            return ProxyBackend.TOR
        if platform in ("telegram", "discord", "forum"):
            return ProxyBackend.RESIDENTIAL  # Plus crédible qu'une IP Tor
        return ProxyBackend.TOR  # Fallback sécurisé

    @staticmethod
    def _get_active_proxy_label(backend: ProxyBackend) -> str:
        return backend.value
