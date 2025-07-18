import threading
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import datetime
from typing import Any

from dashboard.models import AgentEvent


class AgentStateBroadcaster:
    def __init__(self) -> None:
        self.listeners: dict[str, list[Callable]] = defaultdict(list)
        self.current_state: dict[str, Any] = {}
        self.event_cache: deque[AgentEvent] = deque(maxlen=500)  # Ring buffer for dashboard
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe to agent state updates"""
        with self._lock:
            self.listeners[event_type].append(callback)

    def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Broadcast state update to all listeners"""
        with self._lock:
            self.current_state[event_type] = data

            # Create standardized event for dashboard
            event = AgentEvent(type=event_type, data=data)

            # Cache for dashboard reconnects
            self.event_cache.append(event)

            # Notify all subscribers (TUI + WebSocket clients)
            for callback in self.listeners[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Broadcast error: {e}")

    def get_recent_events(self, since: datetime | None = None) -> list[AgentEvent]:
        """Get recent events for dashboard reconnection"""
        if since:
            return [e for e in self.event_cache if e.timestamp > since]
        return list(self.event_cache)


# Global broadcaster instance
broadcaster = AgentStateBroadcaster()
