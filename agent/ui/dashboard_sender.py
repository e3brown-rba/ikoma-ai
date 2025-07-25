"""Dashboard event sender for agent-dashboard communication."""

import os
import threading
from datetime import datetime
from typing import Any

import requests

# Import AgentEvent from dashboard models if available, otherwise define it locally
try:
    from dashboard.models import AgentEvent as DashboardAgentEvent

    # Use the imported AgentEvent
    AgentEvent = DashboardAgentEvent
except ImportError:
    # Fallback if dashboard models aren't available
    from dataclasses import dataclass
    from datetime import datetime
    from typing import Any

    @dataclass
    class AgentEvent:  # type: ignore[no-redef]
        type: str
        data: dict[str, Any]
        timestamp: datetime = datetime.now()


class DashboardEventSender:
    """Sends agent events to the dashboard via HTTP POST."""

    def __init__(self, dashboard_url: str = "http://localhost:8000") -> None:
        self.dashboard_url = dashboard_url
        self.session = requests.Session()
        self.enabled = False
        self._lock = threading.Lock()

    def enable(self) -> None:
        """Enable dashboard event sending."""
        with self._lock:
            self.enabled = True

    def disable(self) -> None:
        """Disable dashboard event sending."""
        with self._lock:
            self.enabled = False

    def send_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Send an event to the dashboard."""
        if not self.enabled:
            return

        try:
            event = AgentEvent(type=event_type, data=data, timestamp=datetime.now())

            # Send to dashboard via HTTP POST
            # Note: This is a simplified approach - in production you'd want WebSocket
            response = self.session.post(
                f"{self.dashboard_url}/agent-event",
                json=event.model_dump(),
                timeout=1.0,
            )

            if response.status_code != 200:
                print(f"Dashboard event failed: {response.status_code}")

        except Exception as e:
            # Don't let dashboard errors break the agent
            print(f"Dashboard event error: {e}")


# Global dashboard sender instance
dashboard_sender = DashboardEventSender()


def get_dashboard_sender() -> DashboardEventSender:
    """Get the global dashboard sender instance."""
    return dashboard_sender


def enable_dashboard_events() -> None:
    """Enable dashboard event sending if dashboard mode is active."""
    if os.getenv("IKOMA_DASHBOARD_MODE") == "true":
        dashboard_sender.enable()
        print("[Dashboard] Event sending enabled")
