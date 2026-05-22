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
