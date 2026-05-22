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
PHYNX — Exemple de code : Module Identity (Holehe) + Tor Scraper
FastAPI + Celery + Neo4j — Flux complet asynchrone

Architecture :
  POST /api/v1/investigations → FastAPI → Redis Queue → Celery Worker → Neo4j
"""

# ============================================================
# backend/app/main.py — FastAPI Gateway
# ============================================================
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uuid
from datetime import datetime

from app.models import InvestigationRequest, InvestigationResponse, InvestigationStatus
from app.database import get_db_session, init_db
from app.celery_app import celery_app
from app.routers import graph, reports, modules, vision, humint, panic
from app.websocket import websocket_graph_endpoint
from app.middleware.ai_firewall import initialize_firewall, AIFirewallMiddleware
import os

# Application lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init Postgres connection pool & tables
    await init_db()
    # Initialisation de l'AI Firewall local (chargement DeBERTa)
    initialize_firewall()
    yield

# Initialize FastAPI app
app = FastAPI(
    title="ARGUS-INT Backend",
    description="Multi-Spectrum Intelligence Fusion Platform",
    version="0.5.0",
    lifespan=lifespan,
    docs_url="/api/docs" if os.getenv("ENV") != "production" else None,  # Disable Swagger in prod
    redoc_url="/api/redoc" if os.getenv("ENV") != "production" else None,
)

# Setup observability (logging + Prometheus metrics)
from app.observability.logging import setup_observability
setup_observability(app)

# Apply security middleware
from app.middleware.security import setup_security_middleware
setup_security_middleware(app)

# Apply AI Firewall Middleware to guard LLM contexts
app.add_middleware(AIFirewallMiddleware)


app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(modules.router, prefix="/api/v1/modules", tags=["modules"])
app.include_router(vision.router, tags=["Vision Pipeline"])
app.include_router(humint.router, tags=["HUMINT Operations"])
app.include_router(panic.router)


# Register WebSocket endpoint
app.add_api_websocket_route("/ws/graph/{investigation_id}", websocket_graph_endpoint)

@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "healthy", "version": "0.5.0"}

@app.get("/ready", tags=["system"])
async def readiness_check():
    # Add actual dependency checks here (DB, Neo4j, Redis)
    return {"status": "ready"}

# Root redirect to docs (dev only)
@app.get("/")
async def root():
    if os.getenv("ENV") != "production":
        return {"message": "ARGUS-INT Backend", "docs": "/api/docs"}
    return {"message": "ARGUS-INT Backend Operational"}


@app.post("/api/v1/investigations", response_model=InvestigationResponse, status_code=202)
async def create_investigation(request: InvestigationRequest):
    """
    Lance une investigation OSINT de manière asynchrone.
    Retourne immédiatement un investigation_id pour polling/WebSocket.
    """
    investigation_id = str(uuid.uuid4())

    # Persiste en base (statut PENDING)
    async with get_db_session() as db:
        await db.execute(
            """INSERT INTO investigations (id, target, target_type, depth, status, created_at)
               VALUES ($1, $2, $3, $4, 'PENDING', $5)""",
            investigation_id, request.target, request.target_type,
            request.depth, datetime.utcnow()
        )

    # Dispatch vers les workers Celery selon le type de cible
    task_group = _build_task_group(investigation_id, request)
    task_group.apply_async()

    return InvestigationResponse(
        investigation_id=investigation_id,
        status=InvestigationStatus.PENDING,
        message=f"Investigation lancée sur '{request.target}' (profondeur={request.depth})"
    )


def _build_task_group(investigation_id: str, request: InvestigationRequest):
    """
    Construit un groupe de tâches Celery selon le type de cible.
    Utilise chord() pour les étapes de corrélation post-collecte.
    """
    from celery import group, chord
    from app.tasks.identity import run_identity_search
    from app.tasks.breach import run_breach_search
    from app.tasks.darkweb import run_darkweb_search
    from app.tasks.correlation import run_graph_correlation

    collectors = []

    if request.target_type in ("email", "username", "phone"):
        collectors.append(
            run_identity_search.s(
                investigation_id=investigation_id,
                target=request.target,
                target_type=request.target_type,
                depth=request.depth
            )
        )

    if request.target_type in ("email", "username", "domain"):
        collectors.append(
            run_breach_search.s(
                investigation_id=investigation_id,
                target=request.target,
                depth=request.depth
            )
        )

    if request.depth >= 2:
        collectors.append(
            run_darkweb_search.s(
                investigation_id=investigation_id,
                target=request.target,
                depth=request.depth
            )
        )

    # chord : tous les collectors → puis corrélation Neo4j
    return chord(group(collectors))(
        run_graph_correlation.s(investigation_id=investigation_id)
    )


@app.get("/api/v1/investigations", response_model=list[InvestigationResponse])
async def list_investigations():
    async with get_db_session() as db:
        rows = await db.fetch(
            "SELECT id, target, target_type, depth, status, result_count, created_at FROM investigations ORDER BY created_at DESC"
        )
    return [
        InvestigationResponse(
            investigation_id=str(row["id"]),
            status=row["status"],
            result_count=row["result_count"],
            created_at=row["created_at"],
            message=f"Target: {row['target']}"
        ) for row in rows
    ]

@app.get("/api/v1/investigations/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation_status(investigation_id: str):
    async with get_db_session() as db:
        row = await db.fetchrow(
            "SELECT * FROM investigations WHERE id = $1", investigation_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="Investigation non trouvée")
    return InvestigationResponse(
        investigation_id=investigation_id,
        status=row["status"],
        result_count=row.get("result_count", 0)
    )
