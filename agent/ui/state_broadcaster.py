import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Any


class AgentStateBroadcaster:
    def __init__(self):
        self.listeners: dict[str, list[Callable]] = defaultdict(list)
        self.current_state = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to agent state updates"""
        with self._lock:
            self.listeners[event_type].append(callback)

    def broadcast(self, event_type: str, data: dict[str, Any]):
        """Broadcast state update to all listeners"""
        with self._lock:
            self.current_state[event_type] = data
            for callback in self.listeners[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"TUI callback error: {e}")


# Global broadcaster instance
broadcaster = AgentStateBroadcaster()
