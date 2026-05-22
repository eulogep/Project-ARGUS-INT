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
# Project ARGUS-INT - Pydantic Schemas & Enumerations
# ==============================================================================

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class InvestigationStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COLLECTING = "COLLECTING"
    CORRELATING = "CORRELATING"
    COMPLETED = "COMPLETED"
    DONE = "DONE"
    FAILED = "FAILED"

class InvestigationRequest(BaseModel):
    target: str = Field(..., description="Cible d'investigation (Email, IP, Domain, etc.)")
    target_type: str = Field(..., description="Type de cible (email, username, domain, ip, wallet)")
    depth: int = Field(1, ge=1, le=3, description="Profondeur de l'analyse (1-3)")

class InvestigationResponse(BaseModel):
    investigation_id: str
    status: InvestigationStatus
    message: Optional[str] = None
    result_count: int = 0
    created_at: Optional[datetime] = None

class WorkerMetric(BaseModel):
    name: str
    status: str
    queue: str
    tasks_completed: int
    avg_time_ms: int
