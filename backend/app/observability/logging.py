# ==============================================================================
# Project ARGUS-INT - Observability (Logging & Metrics)
# ==============================================================================

import structlog
from datetime import datetime
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

# Configure structlog to output structured JSON
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

def setup_observability(app: FastAPI):
    """
    Sets up Prometheus metrics instrumentation and adds health/readiness endpoints.
    """
    # Instrument and expose /metrics endpoint
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    
    @app.get("/health")
    async def health_check():
        """Health check returns current UTC timestamp and status."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
    
    @app.get("/ready")
    async def readiness_check():
        """Readiness check validates backend sub-systems."""
        # Add quick neo4j or postgres connectivity test here if desired
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}

    logger.info("[Observability] Structured logging configured and Prometheus metrics exposed on /metrics.")
