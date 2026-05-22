# ==============================================================================
# Project ARGUS-INT - Multi-Spectrum Intelligence Fusion Platform
# ==============================================================================
# Copyright (C) 2026 eulogep
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
ARGUS-INT — IPFS & Anchoring Service (Chain of Custody)
backend/app/services/ipfs_proof.py

Garantit l'intégrité légale et l'opposabilité des rapports et captures (Chain of Custody).
"""

import logging
import hashlib
import httpx
from typing import Optional, Tuple
from app.config import settings
from app.services.encryption import encrypt_data

logger = logging.getLogger(__name__)


class IPFSProofService:
    """
    Gère le stockage décentralisé sur IPFS et l'ancrage de preuves d'intégrité.
    """

    def __init__(self):
        self.ipfs_api_url = settings.IPFS_API_URL  # http://ipfs:5001/api/v0
        self.tor_proxy = settings.TOR_PROXY
        
        # Client HTTP pour le nœud local IPFS (pas besoin de Tor car local)
        self._ipfs_client = httpx.Client(timeout=60.0)
        
        # Client HTTP avec Tor forcé pour les appels d'ancrage externes (ex: Arweave, OpenTimestamps)
        self._tor_transport = httpx.HTTPTransport(proxy=self.tor_proxy)
        self._external_client = httpx.Client(transport=self._tor_transport, timeout=30.0)

    def add_to_ipfs(self, file_content: bytes, filename: str) -> Tuple[str, str]:
        """
        Envoie le document vers IPFS et calcule son hash SHA-256 local.
        Retourne : (CID_IPFS, SHA256_HASH)
        """
        sha256_hash = hashlib.sha256(file_content).hexdigest()
        
        try:
            # IPFS add via l'API HTTP du démon local (Kubo / go-ipfs)
            files = {"file": (filename, file_content)}
            response = self._ipfs_client.post(
                f"{self.ipfs_api_url}/add",
                files=files
            )
            response.raise_for_status()
            result = response.json()
            cid = result.get("Hash")
            
            logger.info(f"[IPFS] Fichier ajouté avec succès. CID: {cid} | SHA256: {sha256_hash}")
            return cid, sha256_hash
            
        except Exception as e:
            logger.error(f"[IPFS] Erreur lors de l'ajout à IPFS : {e}")
            raise RuntimeError(f"Échec du téléversement IPFS : {e}")

    def anchor_proof(self, sha256_hash: str, cid: str) -> dict:
        """
        Ancre le hash SHA-256 et le CID IPFS sur une preuve immuable.
        Utilise OpenTimestamps par défaut (ancrage gratuit Bitcoin) ou Arweave.
        """
        logger.info(f"[Anchoring] Début de l'ancrage pour le hash : {sha256_hash}")
        
        proof_details = {
            "anchored": False,
            "tx_hash": None,
            "provider": None,
            "error": None
        }

        # Option A : Ancrage via OpenTimestamps (timestamp décentralisé sur Bitcoin)
        # Méthode robuste pour la Chain of Custody
        try:
            # En production, on peut utiliser la lib `opentimestamps`
            # Ici nous simulons l'appel via un calendrier OTS public (via Tor)
            ots_payload = {
                "hash": sha256_hash,
                "cid": cid
            }
            # Appel à un serveur de calendrier OpenTimestamps tiers via Tor
            response = self._external_client.post(
                "https://alice.btc.calendar.opentimestamps.org/digest",
                headers={"Content-Type": "application/octet-stream"},
                content=bytes.fromhex(sha256_hash)
            )
            if response.status_code in (200, 201):
                proof_details["anchored"] = True
                proof_details["provider"] = "OpenTimestamps (Bitcoin)"
                logger.info(f"[Anchoring] Preuve ancrée avec succès sur OpenTimestamps.")
                return proof_details
        except Exception as e:
            logger.warning(f"[Anchoring] Échec OpenTimestamps : {e}. Tentative de repli sur Arweave...")

        # Option B : Repli sur Arweave (Stockage permanent et horodaté)
        try:
            # Envoi du hash/preuve vers le réseau permanent Arweave
            # Le hash est passé en tag
            arweave_data = {
                "document_sha256": sha256_hash,
                "ipfs_cid": cid,
                "timestamp": response.headers.get("Date", "")
            }
            # Simulation via passerelle Arweave (via Tor)
            # En prod, requiert un wallet Arweave chargé
            response = self._external_client.post(
                "https://arweave.net/tx",
                json=arweave_data
            )
            # Arweave nécessite des frais (tokens AR), ceci est un fallback conceptuel
            if response.status_code in (200, 201):
                tx_id = response.json().get("id")
                proof_details["anchored"] = True
                proof_details["tx_hash"] = encrypt_data(tx_id)
                proof_details["provider"] = "Arweave"
                logger.info(f"[Anchoring] Preuve ancrée sur Arweave. Tx ID chiffré.")
                return proof_details
        except Exception as e:
            logger.error(f"[Anchoring] Échec de l'ancrage de secours Arweave : {e}")
            proof_details["error"] = str(e)

        return proof_details

    def close(self):
        self._ipfs_client.close()
        self._external_client.close()
