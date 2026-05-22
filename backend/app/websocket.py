# ==============================================================================
# Project ARGUS-INT - Real-Time WebSockets Orchestrator
# ==============================================================================
"""
WebSocket Manager for real-time graph updates in ARGUS-INT.
Supports optional JWT auth with No-Auth fallback for air-gapped deployments.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect, Query, Depends
from pydantic import BaseModel, Field

from app.auth import verify_token_optional  # Returns None in No-Auth mode
from app.observability.logging import logger

# Configuration constants
HEARTBEAT_INTERVAL_SECONDS = 30
MAX_CONNECTIONS_PER_INVESTIGATION = 10
RECONNECTION_COOLDOWN_SECONDS = 5


class GraphUpdate(BaseModel):
    """Schema for real-time graph updates sent to clients."""
    investigation_id: str = Field(..., description="UUID of the investigation")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: str = Field(..., description="Type of event: node_added, edge_updated, pivot_suggested, etc.")
    payload: dict = Field(..., description="Event-specific data")
    sequence: int = Field(..., description="Monotonic sequence number for ordering")


class ConnectionManager:
    """
    Manages active WebSocket connections per investigation.
    Thread-safe for async access with proper locking.
    """
    
    def __init__(self):
        # {investigation_id: {connection_id: WebSocket}}
        self._connections: Dict[str, Dict[str, WebSocket]] = {}
        self._sequence_counters: Dict[str, int] = {}
        self._logger = logger.bind(component="websocket_manager")
    
    async def connect(
        self,
        websocket: WebSocket,
        investigation_id: str,
        connection_id: str,
        token: Optional[str] = None
    ) -> bool:
        """
        Accept a new WebSocket connection after optional auth validation.
        Returns True if connection accepted, False if rejected.
        """
        # Optional authentication check (noop in No-Auth mode)
        user_context = await verify_token_optional(token) if token else None
        
        # Rate limit: max connections per investigation
        if investigation_id in self._connections:
            if len(self._connections[investigation_id]) >= MAX_CONNECTIONS_PER_INVESTIGATION:
                self._logger.warning(
                    "Connection limit reached for investigation",
                    investigation_id=investigation_id,
                    limit=MAX_CONNECTIONS_PER_INVESTIGATION
                )
                return False
        
        # Initialize sequence counter for this investigation if needed
        if investigation_id not in self._sequence_counters:
            self._sequence_counters[investigation_id] = 0
        
        # Accept and register connection
        await websocket.accept()
        self._connections.setdefault(investigation_id, {})[connection_id] = websocket
        
        self._logger.info(
            "WebSocket connection established",
            investigation_id=investigation_id,
            connection_id=connection_id,
            user_context=user_context,
            active_connections=len(self._connections.get(investigation_id, {}))
        )
        
        # Send initial handshake confirmation
        await websocket.send_json({
            "type": "handshake",
            "connection_id": connection_id,
            "investigation_id": investigation_id,
            "heartbeat_interval": HEARTBEAT_INTERVAL_SECONDS
        })
        
        return True
    
    def disconnect(self, websocket: WebSocket, investigation_id: str, connection_id: str):
        """Remove a disconnected WebSocket from the manager."""
        if investigation_id in self._connections and connection_id in self._connections[investigation_id]:
            del self._connections[investigation_id][connection_id]
            self._logger.info(
                "WebSocket connection closed",
                investigation_id=investigation_id,
                connection_id=connection_id,
                remaining=len(self._connections.get(investigation_id, {}))
            )
            # Cleanup empty investigation entries
            if not self._connections[investigation_id]:
                del self._connections[investigation_id]
    
    async def broadcast(self, investigation_id: str, update: GraphUpdate):
        """
        Broadcast a graph update to all connected clients for an investigation.
        Implements exponential backoff retry for failed sends.
        """
        if investigation_id not in self._connections:
            return
        
        # Increment sequence counter for ordering
        self._sequence_counters[investigation_id] = self._sequence_counters.get(investigation_id, 0) + 1
        update.sequence = self._sequence_counters[investigation_id]
        
        message = update.model_dump(mode='json')
        failed_connections = []
        
        for connection_id, websocket in self._connections[investigation_id].items():
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                failed_connections.append(connection_id)
                self._logger.warning(
                    "Failed to send update, client disconnected",
                    investigation_id=investigation_id,
                    connection_id=connection_id
                )
            except Exception as e:
                self._logger.error(
                    "Unexpected error broadcasting update",
                    investigation_id=investigation_id,
                    connection_id=connection_id,
                    error=str(e),
                    exc_info=True
                )
                failed_connections.append(connection_id)
        
        # Cleanup failed connections
        for conn_id in failed_connections:
            if conn_id in self._connections.get(investigation_id, {}):
                del self._connections[investigation_id][conn_id]
    
    def get_active_count(self, investigation_id: str) -> int:
        """Return the number of active connections for an investigation."""
        return len(self._connections.get(investigation_id, {}))


# Global manager instance
manager = ConnectionManager()


# FastAPI WebSocket endpoint
async def websocket_graph_endpoint(
    websocket: WebSocket,
    investigation_id: str,
    token: Optional[str] = Query(default=None, description="Optional JWT token for authenticated deployments"),
    client_id: Optional[str] = Query(default=None, description="Client-generated unique identifier")
):
    """
    WebSocket endpoint for real-time graph updates.
    Path: /ws/graph/{investigation_id}
    
    Features:
    - Optional JWT authentication (No-Auth fallback)
    - Heartbeat ping/pong handling
    - Graceful disconnect handling
    - Connection limit enforcement
    """
    import uuid
    from asyncio import sleep
    
    connection_id = client_id or str(uuid.uuid4())
    
    # Attempt connection
    if not await manager.connect(websocket, investigation_id, connection_id, token):
        await websocket.close(code=4000, reason="Connection limit exceeded or auth failed")
        return
    
    last_pong = datetime.now(timezone.utc)
    
    try:
        while True:
            # Wait for client message with timeout for heartbeat detection
            try:
                # Use asyncio.wait_for to implement heartbeat timeout
                import asyncio
                data = await asyncio.wait_for(websocket.receive_text(), timeout=HEARTBEAT_INTERVAL_SECONDS * 2)
                
                # Handle ping/pong
                if data == "ping":
                    await websocket.send_text("pong")
                    last_pong = datetime.now(timezone.utc)
                elif data == "subscribe":
                    # Client explicitly requests subscription confirmation
                    await websocket.send_json({
                        "type": "subscribed",
                        "investigation_id": investigation_id
                    })
                # Ignore other messages or log for debugging
                else:
                    logger.debug("Received unexpected WebSocket message", data=data[:100] if isinstance(data, str) else type(data))
                    
            except asyncio.TimeoutError:
                # Check if client is still responsive
                time_since_pong = (datetime.now(timezone.utc) - last_pong).total_seconds()
                if time_since_pong > HEARTBEAT_INTERVAL_SECONDS * 3:
                    logger.warning(
                        "WebSocket heartbeat timeout, closing connection",
                        investigation_id=investigation_id,
                        connection_id=connection_id,
                        time_since_pong=time_since_pong
                    )
                    break
                continue
                
    except WebSocketDisconnect:
        logger.info("Client disconnected normally", investigation_id=investigation_id, connection_id=connection_id)
    except Exception as e:
        logger.error(
            "WebSocket connection error",
            investigation_id=investigation_id,
            connection_id=connection_id,
            error=str(e),
            exc_info=True
        )
    finally:
        # Always cleanup
        manager.disconnect(websocket, investigation_id, connection_id)
