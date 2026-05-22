# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — HUMINT Approval Queue : File d'attente HITL
backend/app/cognitive/humint/approval_queue.py

Gère le cycle de vie des messages HUMINT :
  PENDING → APPROVED → SENT (via proxy)
  PENDING → REJECTED
  APPROVED → FAILED (si l'envoi échoue)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class ApprovalQueue:
    """Interface CRUD pour la table humint_approvals (PostgreSQL)."""

    @staticmethod
    async def enqueue(
        investigation_id: str,
        agent_id: str,
        persona_name: str,
        target_platform: str,
        target_context: str,
        generated_message: str,
        style_score: float = 0.0,
    ) -> str:
        """
        Ajoute un message en file d'attente PENDING.
        Retourne l'UUID du message créé.
        """
        msg_id = str(uuid4())
        try:
            from app.database import get_db_session
            async with get_db_session() as db:
                await db.execute(
                    """
                    INSERT INTO humint_approvals
                        (id, agent_id, investigation_id, persona_name,
                         target_platform, target_context, generated_message,
                         style_score, status, created_at)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'PENDING',$9)
                    """,
                    msg_id, agent_id, investigation_id, persona_name,
                    target_platform, target_context[:500],
                    generated_message, style_score,
                    datetime.now(timezone.utc),
                )
            logger.info(
                "approval_queue.enqueued",
                msg_id=msg_id,
                investigation=investigation_id,
                platform=target_platform,
            )
        except Exception as exc:
            logger.error("approval_queue.enqueue_failed", error=str(exc))
            raise
        return msg_id

    @staticmethod
    async def get_pending(investigation_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Liste les messages PENDING (filtrés par investigation si précisé)."""
        try:
            from app.database import get_db_session
            async with get_db_session() as db:
                if investigation_id:
                    rows = await db.fetch(
                        """
                        SELECT id, agent_id, investigation_id, persona_name,
                               target_platform, target_context, generated_message,
                               style_score, created_at
                        FROM humint_approvals
                        WHERE status = 'PENDING' AND investigation_id = $1
                        ORDER BY created_at DESC
                        """,
                        investigation_id,
                    )
                else:
                    rows = await db.fetch(
                        """
                        SELECT id, agent_id, investigation_id, persona_name,
                               target_platform, target_context, generated_message,
                               style_score, created_at
                        FROM humint_approvals
                        WHERE status = 'PENDING'
                        ORDER BY created_at DESC
                        LIMIT 100
                        """,
                    )
                return [dict(r) for r in rows]
        except Exception as exc:
            logger.error("approval_queue.get_pending_failed", error=str(exc))
            return []

    @staticmethod
    async def approve(
        msg_id: str,
        approved_by: str,
    ) -> bool:
        """
        Approuve un message → statut APPROVED.
        Déclenche l'exécution via HumintExecutor (appelé par le router).
        """
        try:
            from app.database import get_db_session
            async with get_db_session() as db:
                result = await db.execute(
                    """
                    UPDATE humint_approvals
                    SET status='APPROVED', approved_by=$2, approved_at=$3
                    WHERE id=$1 AND status='PENDING'
                    """,
                    msg_id, approved_by, datetime.now(timezone.utc),
                )
                if result == "UPDATE 0":
                    logger.warning("approval_queue.approve_not_found", msg_id=msg_id)
                    return False
            logger.info("approval_queue.approved", msg_id=msg_id, by=approved_by)
            return True
        except Exception as exc:
            logger.error("approval_queue.approve_failed", msg_id=msg_id, error=str(exc))
            return False

    @staticmethod
    async def reject(
        msg_id: str,
        rejected_by: str,
        reason: str,
    ) -> bool:
        """Rejette un message PENDING."""
        try:
            from app.database import get_db_session
            async with get_db_session() as db:
                await db.execute(
                    """
                    UPDATE humint_approvals
                    SET status='REJECTED', approved_by=$2,
                        approved_at=$3, rejection_reason=$4
                    WHERE id=$1 AND status='PENDING'
                    """,
                    msg_id, rejected_by, datetime.now(timezone.utc), reason,
                )
            logger.info("approval_queue.rejected", msg_id=msg_id, by=rejected_by)
            return True
        except Exception as exc:
            logger.error("approval_queue.reject_failed", msg_id=msg_id, error=str(exc))
            return False

    @staticmethod
    async def mark_sent(msg_id: str, proxy_used: str) -> None:
        """Marque un message comme SENT après envoi réussi via proxy."""
        try:
            from app.database import get_db_session
            async with get_db_session() as db:
                await db.execute(
                    "UPDATE humint_approvals SET status='SENT', sent_via_proxy=TRUE WHERE id=$1",
                    msg_id,
                )
            logger.info("approval_queue.sent", msg_id=msg_id, proxy=proxy_used)
        except Exception as exc:
            logger.error("approval_queue.mark_sent_failed", msg_id=msg_id, error=str(exc))

    @staticmethod
    async def mark_failed(msg_id: str, reason: str) -> None:
        """Marque un message comme FAILED."""
        try:
            from app.database import get_db_session
            async with get_db_session() as db:
                await db.execute(
                    "UPDATE humint_approvals SET status='FAILED', rejection_reason=$2 WHERE id=$1",
                    msg_id, reason,
                )
            logger.warning("approval_queue.failed", msg_id=msg_id, reason=reason)
        except Exception as exc:
            logger.error("approval_queue.mark_failed_error", msg_id=msg_id, error=str(exc))

    @staticmethod
    async def get_by_id(msg_id: str) -> Optional[dict[str, Any]]:
        """Récupère un message par son ID."""
        try:
            from app.database import get_db_session
            async with get_db_session() as db:
                row = await db.fetchrow(
                    "SELECT * FROM humint_approvals WHERE id=$1",
                    msg_id,
                )
                return dict(row) if row else None
        except Exception as exc:
            logger.error("approval_queue.get_failed", msg_id=msg_id, error=str(exc))
            return None
