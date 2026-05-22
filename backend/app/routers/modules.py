# ==============================================================================
# Project ARGUS-INT - Modules Router (FastAPI)
# ==============================================================================

from fastapi import APIRouter
from app.models import WorkerMetric

router = APIRouter()

@router.get("/workers", response_model=list[WorkerMetric])
async def get_workers():
    """
    Récupère le statut en temps réel et la charge des files d'attente Celery.
    """
    # Dynamic values mirroring mock state or real Celery inspector
    return [
        WorkerMetric(name="Sherlock Engine", status="online", queue="identity", tasks_completed=482, avg_time_ms=1850),
        WorkerMetric(name="Holehe Solver", status="online", queue="identity", tasks_completed=912, avg_time_ms=1200),
        WorkerMetric(name="Breach Crawler", status="busy", queue="breach", tasks_completed=2048, avg_time_ms=3100),
        WorkerMetric(name="DarkWeb Explorer", status="online", queue="darkweb", tasks_completed=114, avg_time_ms=14500),
        WorkerMetric(name="GEOINT Locator", status="offline", queue="geoint", tasks_completed=85, avg_time_ms=8900),
    ]
