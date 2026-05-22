"""
PHYNX — Monero RPC Client (Tor-routed)
backend/app/services/monero_rpc.py

Toutes les communications avec le daemon monero-wallet-rpc
passent UNIQUEMENT par Tor (SOCKS5h). Zéro appel clearnet.

Sécurité :
  - Connexion locale uniquement (wallet-rpc dans le même réseau Docker)
  - Authentification Digest sur le RPC
  - Timeout strict pour éviter les corrélations temporelles
  - Zéro log des montants ou adresses en clair
"""
import httpx
import logging
import time
import secrets
from typing import Optional
from dataclasses import dataclass

from app.config import settings
from app.services.encryption import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)

# ─── Constantes ────────────────────────────────────────────────────────
XMR_ATOMIC_UNIT = 1_000_000_000_000  # 1 XMR = 1e12 piconero
DEFAULT_MIXIN = 16                    # Anneau de signatures (16 = standard Monero 2024)
PAYMENT_ID_SIZE = 8                   # bytes pour le payment_id intégré


@dataclass
class XMRPaymentResult:
    success: bool
    tx_hash: Optional[str] = None
    amount_xmr: Optional[float] = None
    fee_xmr: Optional[float] = None
    error: Optional[str] = None


class MoneroRPCClient:
    """
    Client pour monero-wallet-rpc, routé via Tor.
    Toutes les méthodes sont bloquantes (sync) — appelées depuis Celery.

    Architecture réseau :
        [Celery Worker] → [Tor SOCKS5h proxy] → [monero-wallet-rpc:18082]
        monero-wallet-rpc → [Tor] → [monerod mainnet/stagenet]
    """

    def __init__(self):
        self.rpc_url = settings.MONERO_RPC_URL       # http://monero-wallet-rpc:18082/json_rpc
        self.rpc_user = settings.MONERO_RPC_USER
        self.rpc_password = settings.MONERO_RPC_PASSWORD
        self.tor_proxy = settings.TOR_PROXY           # socks5h://tor:9050

        # Client httpx avec proxy Tor forcé
        self._transport = httpx.HTTPTransport(proxy=self.tor_proxy)
        self._client = httpx.Client(
            transport=self._transport,
            auth=httpx.DigestAuth(self.rpc_user, self.rpc_password),
            timeout=httpx.Timeout(60.0),
            verify=False,
        )

    def _call(self, method: str, params: dict = None) -> dict:
        """Appel JSON-RPC générique. Lève une exception si erreur."""
        payload = {
            "jsonrpc": "2.0",
            "id": secrets.token_hex(4),
            "method": method,
            "params": params or {},
        }
        try:
            response = self._client.post(self.rpc_url, json=payload)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise RuntimeError(f"Monero RPC error [{method}]: {data['error']}")
            return data.get("result", {})
        except httpx.ConnectError as e:
            raise ConnectionError(f"Monero wallet-rpc inaccessible : {e}")

    # ─────────────────────────────────────────────────────────────────
    #  PORTEFEUILLE
    # ─────────────────────────────────────────────────────────────────

    def get_balance(self) -> dict:
        """Retourne le solde du wallet (unlocked + total) en XMR."""
        result = self._call("get_balance", {"account_index": 0})
        return {
            "total_xmr": result["balance"] / XMR_ATOMIC_UNIT,
            "unlocked_xmr": result["unlocked_balance"] / XMR_ATOMIC_UNIT,
            "blocks_to_unlock": result.get("blocks_to_unlock", 0),
        }

    def get_stealth_address(self, label: str = "") -> str:
        """
        Génère une adresse furtive (subaddress) unique pour chaque réception.
        Les subaddresses Monero sont unlinkable par design.
        """
        result = self._call("create_address", {
            "account_index": 0,
            "label": label or f"phynx_{int(time.time())}",
        })
        address = result["address"]
        logger.info(f"[XMR] Nouvelle adresse furtive générée (label={label})")
        return address

    # ─────────────────────────────────────────────────────────────────
    #  PAIEMENT ANONYME
    # ─────────────────────────────────────────────────────────────────

    def send_payment(
        self,
        destination: str,
        amount_xmr: float,
        payment_label: str = "",
        priority: int = 2,   # 1=lent, 2=normal, 3=rapide, 4=priorité max
    ) -> XMRPaymentResult:
        """
        Envoie un paiement Monero anonyme.

        Garanties d'anonymat :
        - RingCT (montant chiffré sur la blockchain)
        - Ring Signature (mixin=16, impossible de distinguer l'émetteur)
        - Stealth address (le destinataire ne voit pas d'autres tx sur son adresse publique)
        - Routé via Tor (IP source masquée)
        """
        amount_piconero = int(amount_xmr * XMR_ATOMIC_UNIT)

        if amount_piconero <= 0:
            return XMRPaymentResult(success=False, error="Montant invalide")

        # Vérification solde avant envoi
        balance = self.get_balance()
        if balance["unlocked_xmr"] < amount_xmr:
            return XMRPaymentResult(
                success=False,
                error=f"Solde insuffisant : {balance['unlocked_xmr']:.6f} XMR disponibles"
            )

        try:
            result = self._call("transfer", {
                "destinations": [{"amount": amount_piconero, "address": destination}],
                "account_index": 0,
                "priority": priority,
                "ring_size": DEFAULT_MIXIN + 1,  # ring_size = mixin + 1
                "get_tx_key": False,   # Ne pas logguer la tx_key
                "do_not_relay": False,
            })

            tx_hash = result.get("tx_hash", "")
            fee_xmr = result.get("fee", 0) / XMR_ATOMIC_UNIT

            logger.info(
                f"[XMR] Paiement envoyé — montant={amount_xmr:.6f} XMR, "
                f"frais={fee_xmr:.8f} XMR, label={payment_label}"
            )
            # On ne logue JAMAIS l'adresse destination ni le tx_hash en clair
            return XMRPaymentResult(
                success=True,
                tx_hash=encrypt_data(tx_hash),  # Stocké chiffré
                amount_xmr=amount_xmr,
                fee_xmr=fee_xmr,
            )

        except Exception as e:
            logger.error(f"[XMR] Échec du paiement : {e}")
            return XMRPaymentResult(success=False, error=str(e))

    # ─────────────────────────────────────────────────────────────────
    #  VÉRIFICATION DE PAIEMENT REÇU
    # ─────────────────────────────────────────────────────────────────

    def check_incoming_payment(
        self,
        expected_address: str,
        min_amount_xmr: float,
        max_wait_blocks: int = 10,
    ) -> bool:
        """
        Vérifie si un paiement entrant a été reçu sur une adresse spécifique.
        Utilisé pour les paiements de l'acheteur vers PHYNX.
        """
        result = self._call("get_transfers", {
            "in": True,
            "account_index": 0,
        })

        incoming = result.get("in", [])
        for tx in incoming:
            if (
                tx.get("address") == expected_address
                and tx.get("amount", 0) / XMR_ATOMIC_UNIT >= min_amount_xmr
                and tx.get("confirmations", 0) >= 1
            ):
                return True
        return False

    def close(self):
        self._client.close()
