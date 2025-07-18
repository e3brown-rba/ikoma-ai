from functools import lru_cache
from typing import Any

from agent.checkpointer import IkomaCheckpointer
from agent.ui.state_broadcaster import broadcaster
from tools.vector_store import get_vector_store

from .models import AgentEvent


def get_broadcaster() -> Any:
    """Dependency to inject the state broadcaster"""
    return broadcaster


def get_stores() -> dict[str, Any]:
    """Dependency to inject existing stores"""
    return {
        "checkpointer": IkomaCheckpointer("agent/memory/conversations.sqlite"),
        "vector_store": get_vector_store(),
    }


class WebSocketManager:
    """WebSocket connection manager for dashboard"""

    def __init__(self) -> None:
        self.active_connections: list[Any] = []

    async def connect(self, websocket: Any) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: Any) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_event(self, event: AgentEvent) -> None:
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(event.model_dump_json())
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.remove(conn)


@lru_cache(maxsize=1)
def get_websocket_manager() -> WebSocketManager:
    """Singleton WebSocket manager for dashboard"""
    return WebSocketManager()
