# ==============================================================================
# Project ARGUS-INT — SPDX-License-Identifier: AGPL-3.0-or-later
# ==============================================================================
"""
ARGUS-INT — Agent State Machine (Python pur, Pydantic + Redis)
backend/app/cognitive/state_machine.py
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = structlog.get_logger(__name__)


class AgentState(str, Enum):
    IDLE          = "IDLE"
    PLANNING      = "PLANNING"
    COLLECTING    = "COLLECTING"
    ANALYZING     = "ANALYZING"
    WAITING_HUMAN = "WAITING_HUMAN"
    REPORTING     = "REPORTING"
    COMPLETED     = "COMPLETED"
    ERROR         = "ERROR"


_ALLOWED_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.IDLE:          {AgentState.PLANNING, AgentState.ERROR},
    AgentState.PLANNING:      {AgentState.COLLECTING, AgentState.WAITING_HUMAN, AgentState.ERROR},
    AgentState.COLLECTING:    {AgentState.ANALYZING, AgentState.WAITING_HUMAN, AgentState.ERROR},
    AgentState.ANALYZING:     {AgentState.REPORTING, AgentState.COLLECTING, AgentState.WAITING_HUMAN, AgentState.ERROR},
    AgentState.WAITING_HUMAN: {AgentState.COLLECTING, AgentState.ANALYZING, AgentState.REPORTING, AgentState.ERROR},
    AgentState.REPORTING:     {AgentState.COMPLETED, AgentState.ERROR},
    AgentState.COMPLETED:     set(),
    AgentState.ERROR:         {AgentState.IDLE},
}


class StateTransitionEvent(BaseModel):
    agent_id: str
    investigation_id: str
    from_state: AgentState
    to_state: AgentState
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentSnapshot(BaseModel):
    """Snapshot sérialisable persisté dans Redis."""
    agent_id: str
    agent_role: str
    investigation_id: str
    state: AgentState = AgentState.IDLE
    previous_state: Optional[AgentState] = None
    state_entered_at: float = Field(default_factory=time.time)
    created_at: float = Field(default_factory=time.time)
    error_message: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)
    transition_count: int = 0
    audit_log: list[dict[str, Any]] = Field(default_factory=list)


class InvalidTransitionError(Exception):
    pass


class AgentStateMachine:
    """
    Machine à états pour un agent ARGUS-INT.
    Zéro dépendance LangGraph/LangChain — Python pur.
    """

    def __init__(
        self,
        agent_id: str,
        agent_role: str,
        investigation_id: str,
        redis_client: Any,
        websocket_manager: Optional[Any] = None,
    ) -> None:
        self.agent_id = agent_id
        self.agent_role = agent_role
        self.investigation_id = investigation_id
        self._redis = redis_client
        self._ws_manager = websocket_manager
        self._redis_key = f"argus:agent:{agent_id}:state"
        self._snapshot: Optional[AgentSnapshot] = None

    async def initialize(self, context: Optional[dict[str, Any]] = None) -> AgentSnapshot:
        existing = await self.load_state()
        if existing:
            self._snapshot = existing
            logger.info("state_machine.resumed", agent_id=self.agent_id, state=existing.state.value)
        else:
            self._snapshot = AgentSnapshot(
                agent_id=self.agent_id,
                agent_role=self.agent_role,
                investigation_id=self.investigation_id,
                context=context or {},
            )
            await self.save_state()
            logger.info("state_machine.initialized", agent_id=self.agent_id, role=self.agent_role)
        return self._snapshot

    @property
    def current_state(self) -> AgentState:
        return self._snapshot.state if self._snapshot else AgentState.IDLE

    def is_terminal(self) -> bool:
        return self.current_state in (AgentState.COMPLETED, AgentState.ERROR)

    def has_timed_out(self) -> bool:
        if self._snapshot is None or self.is_terminal():
            return False
        return (time.time() - self._snapshot.state_entered_at) > settings.AGENT_STATE_TIMEOUT_S

    async def transition_to(
        self,
        new_state: AgentState,
        reason: str = "",
        metadata: Optional[dict[str, Any]] = None,
        context_update: Optional[dict[str, Any]] = None,
    ) -> StateTransitionEvent:
        if self._snapshot is None:
            await self.initialize()
        assert self._snapshot is not None

        current = self._snapshot.state
        if new_state not in _ALLOWED_TRANSITIONS.get(current, set()):
            raise InvalidTransitionError(
                f"Transition interdite : {current.value} → {new_state.value}"
            )

        old_state = current
        self._snapshot.previous_state = old_state
        self._snapshot.state = new_state
        self._snapshot.state_entered_at = time.time()
        self._snapshot.transition_count += 1

        if context_update:
            self._snapshot.context.update(context_update)
        if new_state == AgentState.ERROR and reason:
            self._snapshot.error_message = reason

        self._snapshot.audit_log.append({
            "from": old_state.value,
            "to": new_state.value,
            "reason": reason,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        if len(self._snapshot.audit_log) > 100:
            self._snapshot.audit_log = self._snapshot.audit_log[-100:]

        await self.save_state()

        event = StateTransitionEvent(
            agent_id=self.agent_id,
            investigation_id=self.investigation_id,
            from_state=old_state,
            to_state=new_state,
            reason=reason,
            metadata=metadata or {},
        )
        await self._emit_event(event)

        logger.info(
            "state_machine.transition",
            agent_id=self.agent_id,
            from_state=old_state.value,
            to_state=new_state.value,
            reason=reason,
        )
        return event

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.1, min=0.1, max=1))
    async def save_state(self) -> None:
        if self._snapshot is None:
            return
        await self._redis.set(
            self._redis_key,
            self._snapshot.model_dump_json(),
            ex=settings.AGENT_MEMORY_TTL_S,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.1, min=0.1, max=1))
    async def load_state(self) -> Optional[AgentSnapshot]:
        try:
            raw = await self._redis.get(self._redis_key)
            if raw:
                return AgentSnapshot.model_validate_json(raw)
        except Exception as exc:
            logger.error("state_machine.load_failed", agent_id=self.agent_id, error=str(exc))
        return None

    async def delete_state(self) -> None:
        await self._redis.delete(self._redis_key)

    async def _emit_event(self, event: StateTransitionEvent) -> None:
        if self._ws_manager is None:
            return
        try:
            await self._ws_manager.broadcast(
                investigation_id=self.investigation_id,
                message={"type": "agent_state_change", "payload": event.model_dump(mode="json")},
            )
        except Exception as exc:
            logger.warning("state_machine.ws_emit_failed", agent_id=self.agent_id, error=str(exc))

    def update_context(self, key: str, value: Any) -> None:
        if self._snapshot:
            self._snapshot.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        if self._snapshot:
            return self._snapshot.context.get(key, default)
        return default

    def __repr__(self) -> str:
        state = self._snapshot.state.value if self._snapshot else "uninitialized"
        return f"AgentStateMachine(id={self.agent_id}, role={self.agent_role}, state={state})"


async def create_agent_state_machine(
    agent_role: str,
    investigation_id: str,
    redis_client: Any,
    websocket_manager: Optional[Any] = None,
    context: Optional[dict[str, Any]] = None,
) -> AgentStateMachine:
    agent_id = f"{agent_role[:4]}-{str(uuid4())[:8]}"
    sm = AgentStateMachine(agent_id, agent_role, investigation_id, redis_client, websocket_manager)
    await sm.initialize(context=context)
    return sm
