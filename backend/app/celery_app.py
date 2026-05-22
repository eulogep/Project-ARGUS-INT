"""
PHYNX — Celery App Configuration
backend/app/celery_app.py
"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "phynx",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.identity",
        "app.tasks.breach",
        "app.tasks.darkweb",
        "app.tasks.geoint",
        "app.tasks.techrecon",
        "app.tasks.correlation",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.identity.*": {"queue": "identity"},
        "app.tasks.breach.*":   {"queue": "breach"},
        "app.tasks.darkweb.*":  {"queue": "darkweb"},
        "app.tasks.geoint.*":   {"queue": "geoint"},
        "app.tasks.techrecon.*":{"queue": "techrecon"},
    },
    task_soft_time_limit=300,   # 5 min par tâche
    task_time_limit=600,        # hard kill à 10 min
    worker_prefetch_multiplier=1,
    task_acks_late=True,        # Ack après succès seulement
)
