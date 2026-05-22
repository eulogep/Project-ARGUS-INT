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
from app.routers import graph, reports, modules

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="PHYNX OSINT Framework",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(modules.router, prefix="/api/v1/modules", tags=["modules"])


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
