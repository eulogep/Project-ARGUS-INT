# ==============================================================================
# Project ARGUS-INT - Real-Time WebSockets Orchestrator
# ==============================================================================

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

logger = logging.getLogger(__name__)
router = APIRouter()

class ConnectionManager:
    """Manages active WebSockets connections, grouped by investigation ID."""
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, investigation_id: str):
        await websocket.accept()
        self.active_connections.setdefault(investigation_id, []).append(websocket)
        logger.info(f"[WebSocket] Connected client for investigation: {investigation_id}")
    
    def disconnect(self, websocket: WebSocket, investigation_id: str):
        if investigation_id in self.active_connections:
            if websocket in self.active_connections[investigation_id]:
                self.active_connections[investigation_id].remove(websocket)
            if not self.active_connections[investigation_id]:
                del self.active_connections[investigation_id]
        logger.info(f"[WebSocket] Disconnected client for investigation: {investigation_id}")
    
    async def broadcast(self, investigation_id: str, message: dict):
        if investigation_id in self.active_connections:
            for connection in self.active_connections[investigation_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"[WebSocket] Broadcast failed to a connection: {e}")

manager = ConnectionManager()

@router.websocket("/ws/graph/{investigation_id}")
async def websocket_graph_endpoint(
    websocket: WebSocket,
    investigation_id: str,
    token: str = Query(None) # Optionnel en mode No-Auth
):
    # Verify token logic here if auth is enabled
    await manager.connect(websocket, investigation_id)
    try:
        while True:
            # Handle heartbeat / ping messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, investigation_id)
    except Exception as e:
        logger.error(f"[WebSocket] Error during session: {e}")
        manager.disconnect(websocket, investigation_id)
