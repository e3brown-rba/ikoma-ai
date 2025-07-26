import asyncio
import json
import threading
import time
from datetime import datetime
from queue import Empty, Queue
from typing import Any


class SSEConnectionManager:
    def __init__(self) -> None:
        self.connections: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 30  # seconds

        # Thread-safe event queue for broadcasting from threads
        self._event_queue: Queue = Queue()
        self._shutdown = False
        self._event_thread = threading.Thread(target=self._process_events, daemon=False)
        self._event_thread.start()

    def _process_events(self) -> None:
        """Process events from the queue in a separate thread."""
        while not self._shutdown:
            try:
                event = self._event_queue.get(timeout=1.0)
                # Store event for later processing when event loop is available
                if not hasattr(self, "_pending_events"):
                    self._pending_events = []
                self._pending_events.append(event)
            except Empty:
                # Timeout is expected, continue
                continue
            except Exception as e:
                print(f"Error processing event: {e}")
                continue

    def broadcast_from_thread(
        self, agent_id: str, event_type: str, data: dict[str, Any]
    ) -> None:
        """Thread-safe method to broadcast events."""

        # Ensure data is JSON serializable
        def make_serializable(obj: Any) -> Any:
            if hasattr(obj, "value"):  # Handle enums
                return obj.value
            elif hasattr(obj, "isoformat"):  # Handle datetime objects
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            else:
                return obj

        serializable_data = make_serializable(data)

        event = {
            "agent_id": agent_id,
            "event_type": event_type,
            "data": serializable_data,
        }
        self._event_queue.put(event)

    async def add_connection(self, queue: asyncio.Queue) -> None:
        """Add a new SSE connection."""
        async with self._lock:
            self.connections.append(queue)

    async def remove_connection(self, queue: asyncio.Queue) -> None:
        """Remove a specific SSE connection."""
        async with self._lock:
            if queue in self.connections:
                self.connections.remove(queue)

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Broadcast an event to all active connections."""
        async with self._lock:
            if not self.connections:
                return

            dead_connections = []
            message = {
                "event": event.get("event", "state_change"),
                "data": json.dumps(event),
                "id": str(int(time.time() * 1000)),
            }

            # Send to all connections with timeout
            for queue in self.connections:
                try:
                    await asyncio.wait_for(queue.put(message), timeout=1.0)
                except (TimeoutError, Exception) as e:
                    print(f"Failed to send to SSE connection: {e}")
                    dead_connections.append(queue)

            # Clean up dead connections
            if dead_connections:
                for dead_queue in dead_connections:
                    if dead_queue in self.connections:
                        self.connections.remove(dead_queue)

    async def broadcast_status_update(self, agents_data: dict[str, Any]) -> None:
        """Broadcast agent status update specifically."""
        event = {
            "event": "agent_status_update",
            "agents": agents_data,
            "timestamp": datetime.now().isoformat(),
        }
        await self.broadcast(event)

    async def broadcast_agent_event(
        self, agent_id: str, event_type: str, data: dict[str, Any]
    ) -> None:
        """Broadcast agent-specific event."""
        event = {
            "event": event_type,
            "agent_id": agent_id,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        await self.broadcast(event)

    async def periodic_cleanup(self) -> None:
        """Periodically clean up dead connections."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            async with self._lock:
                # Remove any connections that might be dead
                len(self.connections)
                self.connections = [
                    conn for conn in self.connections if not conn.full()
                ]

                self._last_cleanup = current_time

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.connections)

    def get_connections(self) -> list[asyncio.Queue]:
        """Get all active connections."""
        return self.connections.copy()

    async def send_keepalive(self) -> None:
        """Send keepalive message to all connections."""
        event = {
            "event": "keepalive",
            "timestamp": datetime.now().isoformat(),
            "connection_count": len(self.connections),
        }
        await self.broadcast(event)

    async def process_pending_events(self) -> None:
        """Process any pending events from the thread-safe queue."""
        if not hasattr(self, "_pending_events"):
            return

        events_to_process = self._pending_events.copy()
        self._pending_events.clear()

        for event in events_to_process:
            try:
                await self.broadcast_agent_event(
                    event["agent_id"], event["event_type"], event["data"]
                )
            except Exception as e:
                print(f"Error processing pending event: {e}")

    def shutdown(self) -> None:
        """Shutdown the SSE manager and cleanup resources."""
        self._shutdown = True
        if self._event_thread.is_alive():
            self._event_thread.join(timeout=5.0)


# Global instance
sse_manager = SSEConnectionManager()
