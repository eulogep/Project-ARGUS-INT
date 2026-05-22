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
ARGUS-INT — Tâche Celery pour l'Ancrage Blockchain et IPFS (Chain of Custody)
backend/app/tasks/custody.py

Gère l'exportation finale des rapports, l'ajout sur IPFS et l'ancrage de la preuve.
"""

import logging
from celery.utils.log import get_task_logger
from app.celery_app import celery_app
from app.services.ipfs_proof import IPFSProofService
from app.database import get_db_session_sync

logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.custody.archive_and_anchor_report",
    max_retries=3,
    default_retry_delay=60,
    queue="identity",
)
def archive_and_anchor_report(
    self,
    investigation_id: str,
    report_content_base64: str,
    filename: str,
) -> dict:
    """
    Récupère le contenu d'un rapport, le pousse sur IPFS local, 
    génère la preuve d'ancrage cryptographique et stocke la structure de preuve.
    """
    import base64
    logger.info(f"[Custody] Traitement de l'archive immuable pour l'investigation {investigation_id}")

    try:
        report_bytes = base64.b64decode(report_content_base64)
        
        # 1. Pousser vers le nœud IPFS local
        ipfs_service = IPFSProofService()
        cid, sha256_hash = ipfs_service.add_to_ipfs(report_bytes, filename)
        
        # 2. Créer l'ancrage (OTS / Arweave)
        proof = ipfs_service.anchor_proof(sha256_hash, cid)
        ipfs_service.close()

        # 3. Enregistrer les métadonnées de la preuve dans PostgreSQL
        with get_db_session_sync() as db:
            db.execute(
                """INSERT INTO archives 
                   (investigation_id, original_url, archive_url, sha256_hash, file_size_bytes, captured_at, diff_from_previous)
                   VALUES ($1, $2, $3, $4, $5, NOW(), $6)""",
                investigation_id,
                f"phynx://report/{investigation_id}",
                f"ipfs://{cid}",
                sha256_hash,
                len(report_bytes),
                f"Anchored via: {proof.get('provider')} | Tx: {proof.get('tx_hash', 'N/A')}"
            )
            
        logger.info(f"[Custody] Archive immuable stockée. CID: ipfs://{cid}")
        return {
            "success": True,
            "cid": cid,
            "sha256": sha256_hash,
            "anchored": proof["anchored"],
            "provider": proof["provider"]
        }

    except Exception as exc:
        logger.error(f"[Custody] Erreur archivage : {exc}", exc_info=True)
        raise self.retry(exc=exc)
