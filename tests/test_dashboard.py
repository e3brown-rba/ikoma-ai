#!/usr/bin/env python3.11
"""Test script to demonstrate the dashboard functionality."""

import threading
import time

import uvicorn

from agent.ui.state_broadcaster import broadcaster
from dashboard.server import app


def run_dashboard() -> None:
    """Run the dashboard server."""
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


def simulate_agent_events() -> None:
    """Simulate agent events for testing."""
    time.sleep(2)  # Wait for dashboard to start

    # Simulate various agent events
    events = [
        ("planning_start", {"goal": "Write a hello world program"}),
        ("plan_generated", {"steps": ["Create file", "Write code", "Test"]}),
        ("step_start", {"step": 1, "action": "Create file"}),
        ("step_complete", {"step": 1, "result": "file created"}),
        ("step_start", {"step": 2, "action": "Write code"}),
        ("step_complete", {"step": 2, "result": "code written"}),
        ("reflection", {"insight": "Task completed successfully"}),
    ]

    for event_type, data in events:
        print(f"Broadcasting: {event_type}")
        broadcaster.broadcast(event_type, data)  # type: ignore[arg-type]
        time.sleep(1)

    print("Event simulation complete!")


if __name__ == "__main__":
    # Start dashboard in a separate thread
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()

    # Start event simulation in a separate thread
    event_thread = threading.Thread(target=simulate_agent_events, daemon=True)
    event_thread.start()

    print("🚀 Dashboard test started!")
    print("📊 Dashboard available at: http://127.0.0.1:8000")
    print("⏱️  Simulating agent events...")
    print("🔄 Press Ctrl+C to stop")

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Dashboard test stopped!")
