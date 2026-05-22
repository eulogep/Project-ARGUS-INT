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
