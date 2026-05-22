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
ARGUS-INT — Lightning Network Client (LND via Tor)
backend/app/services/lightning.py

Micro-paiements via le réseau Lightning Bitcoin.
Toutes les connexions LND passent par Tor (macaroon auth).
"""

__PROJECT_CANARY__ = "41524755532d494e54204372656174656420627920656d6332202d20446f206e6f742072656d6f7665"

import base64
import hashlib
import logging
import secrets
import httpx
from dataclasses import dataclass
from typing import Optional

from app.config import settings
from app.services.encryption import encrypt_data

logger = logging.getLogger(__name__)


@dataclass
class LNPaymentResult:
    success: bool
    payment_hash: Optional[str] = None
    amount_sats: Optional[int] = None
    fee_sats: Optional[int] = None
    preimage: Optional[str] = None   # Preuve de paiement
    error: Optional[str] = None


class LightningClient:
    """
    Client REST pour LND (Lightning Network Daemon).
    Authentifié via macaroon, routé via Tor.

    Architecture :
        [Celery Worker] → [Tor] → [LND REST :8080] → [Bitcoin Lightning Network]
    """

    def __init__(self):
        self.lnd_url = settings.LND_REST_URL           # https://lnd:8080
        self.macaroon = settings.LND_MACAROON_HEX      # Hex du invoice.macaroon
        self.tor_proxy = settings.TOR_PROXY

        self._transport = httpx.HTTPTransport(proxy=self.tor_proxy)
        self._client = httpx.Client(
            transport=self._transport,
            headers={
                "Grpc-Metadata-macaroon": self.macaroon,
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0),
            verify=False,  # Certificat auto-signé LND
        )

    def _get(self, path: str, **params) -> dict:
        resp = self._client.get(f"{self.lnd_url}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> dict:
        resp = self._client.post(f"{self.lnd_url}{path}", json=body)
        resp.raise_for_status()
        return resp.json()

    # ─────────────────────────────────────────────────────────────────
    #  INFORMATIONS DU NŒUD
    # ─────────────────────────────────────────────────────────────────

    def get_info(self) -> dict:
        """Informations sur le nœud LND local."""
        data = self._get("/v1/getinfo")
        return {
            "node_pubkey": data.get("identity_pubkey", ""),
            "alias": data.get("alias", ""),
            "num_active_channels": data.get("num_active_channels", 0),
            "synced_to_chain": data.get("synced_to_chain", False),
        }

    def get_balance(self) -> dict:
        """Solde du wallet Lightning (local balance des channels)."""
        data = self._get("/v1/balance/channels")
        return {
            "local_balance_sats": int(data.get("local_balance", {}).get("sat", 0)),
            "remote_balance_sats": int(data.get("remote_balance", {}).get("sat", 0)),
        }

    # ─────────────────────────────────────────────────────────────────
    #  PAIEMENT D'UNE INVOICE BOLT11
    # ─────────────────────────────────────────────────────────────────

    def pay_invoice(
        self,
        payment_request: str,   # Invoice BOLT11 (lnbc...)
        max_fee_sats: int = 50,
        label: str = "",
    ) -> LNPaymentResult:
        """
        Paie une invoice Lightning BOLT11.
        Frais max configurables pour éviter les surprises.
        Le routage via Tor masque l'IP source.
        """
        try:
            result = self._post("/v2/router/send", {
                "payment_request": payment_request,
                "fee_limit_sat": max_fee_sats,
                "timeout_seconds": 60,
                "no_inflight_updates": True,
            })

            status = result.get("status", "")
            if status == "SUCCEEDED":
                fee_sats = int(result.get("fee_sat", 0))
                preimage = result.get("payment_preimage", "")
                payment_hash = result.get("payment_hash", "")

                logger.info(
                    f"[LN] Paiement réussi — {label} — "
                    f"frais={fee_sats} sats"
                )
                return LNPaymentResult(
                    success=True,
                    payment_hash=encrypt_data(payment_hash),
                    amount_sats=int(result.get("value_sat", 0)),
                    fee_sats=fee_sats,
                    preimage=encrypt_data(preimage),
                )
            else:
                failure_reason = result.get("failure_reason", status)
                logger.warning(f"[LN] Paiement échoué : {failure_reason}")
                return LNPaymentResult(success=False, error=failure_reason)

        except httpx.HTTPStatusError as e:
            logger.error(f"[LN] HTTP error : {e.response.text}")
            return LNPaymentResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"[LN] Erreur : {e}")
            return LNPaymentResult(success=False, error=str(e))

    # ─────────────────────────────────────────────────────────────────
    #  CRÉATION D'UNE INVOICE (réception de paiement)
    # ─────────────────────────────────────────────────────────────────

    def create_invoice(
        self,
        amount_sats: int,
        memo: str = "PHYNX",
        expiry_seconds: int = 3600,
    ) -> dict:
        """Crée une invoice pour recevoir un paiement Lightning."""
        result = self._post("/v1/invoices", {
            "value": amount_sats,
            "memo": memo,
            "expiry": expiry_seconds,
            "private": True,   # N'annonce pas les channels privés
        })
        return {
            "payment_request": result.get("payment_request", ""),
            "r_hash": result.get("r_hash", ""),
            "add_index": result.get("add_index", ""),
        }

    def close(self):
        self._client.close()
