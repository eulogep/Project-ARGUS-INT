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
