from datetime import datetime

import pytest

from dashboard.sse_manager import sse_manager
from dashboard.state_manager import AgentStatus, state_manager


class TestDashboardSyncFix:
    """Test the dashboard synchronization fix for agent completion events."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        # Clear any existing agents
        for agent_id in list(state_manager._agents.keys()):
            state_manager.delete_agent(agent_id)

        # Clear SSE connections
        sse_manager.connections.clear()
        if hasattr(sse_manager, "_pending_events"):
            sse_manager._pending_events.clear()

    def test_agent_completion_broadcasts_correct_event(self):
        """Test that agent completion broadcasts the correct event type."""
        # Create a test agent
        agent = state_manager.create_agent("test-agent", "Test Agent", "offline")
        agent.status = AgentStatus.RUNNING
        agent.start_time = datetime.now()

        # Mock the broadcast method to capture the event type
        original_broadcast = sse_manager.broadcast_from_thread
        captured_events = []

        def mock_broadcast(agent_id: str, event_type: str, data: dict):
            captured_events.append((agent_id, event_type, data))

        sse_manager.broadcast_from_thread = mock_broadcast

        try:
            # Update agent status to completed
            state_manager.update_agent_status(
                "test-agent", AgentStatus.COMPLETED, end_time=datetime.now()
            )

            # Verify the correct event type was broadcasted
            assert len(captured_events) == 1
            agent_id, event_type, data = captured_events[0]
            assert agent_id == "test-agent"
            assert event_type == "agent_completed"
            assert data["status"] == "completed"

        finally:
            # Restore original method
            sse_manager.broadcast_from_thread = original_broadcast

    def test_agent_error_broadcasts_correct_event(self):
        """Test that agent error broadcasts the correct event type."""
        # Create a test agent
        agent = state_manager.create_agent("test-agent", "Test Agent", "offline")
        agent.status = AgentStatus.RUNNING

        # Mock the broadcast method to capture the event type
        original_broadcast = sse_manager.broadcast_from_thread
        captured_events = []

        def mock_broadcast(agent_id: str, event_type: str, data: dict):
            captured_events.append((agent_id, event_type, data))

        sse_manager.broadcast_from_thread = mock_broadcast

        try:
            # Update agent status to error
            state_manager.update_agent_status(
                "test-agent", AgentStatus.ERROR, error_message="Test error"
            )

            # Verify the correct event type was broadcasted
            assert len(captured_events) == 1
            agent_id, event_type, data = captured_events[0]
            assert agent_id == "test-agent"
            assert event_type == "agent_error"
            assert data["status"] == "error"
            assert data["error"] == "Test error"

        finally:
            # Restore original method
            sse_manager.broadcast_from_thread = original_broadcast

    def test_agent_running_broadcasts_correct_event(self):
        """Test that agent running broadcasts the correct event type."""
        # Create a test agent
        agent = state_manager.create_agent("test-agent", "Test Agent", "offline")
        agent.status = AgentStatus.IDLE

        # Mock the broadcast method to capture the event type
        original_broadcast = sse_manager.broadcast_from_thread
        captured_events = []

        def mock_broadcast(agent_id: str, event_type: str, data: dict):
            captured_events.append((agent_id, event_type, data))

        sse_manager.broadcast_from_thread = mock_broadcast

        try:
            # Update agent status to running
            state_manager.update_agent_status("test-agent", AgentStatus.RUNNING)

            # Verify the correct event type was broadcasted
            assert len(captured_events) == 1
            agent_id, event_type, data = captured_events[0]
            assert agent_id == "test-agent"
            assert event_type == "agent_started"
            assert data["status"] == "running"

        finally:
            # Restore original method
            sse_manager.broadcast_from_thread = original_broadcast

    def test_agent_stopped_broadcasts_correct_event(self):
        """Test that agent stopped broadcasts the correct event type."""
        # Create a test agent
        agent = state_manager.create_agent("test-agent", "Test Agent", "offline")
        agent.status = AgentStatus.RUNNING

        # Mock the broadcast method to capture the event type
        original_broadcast = sse_manager.broadcast_from_thread
        captured_events = []

        def mock_broadcast(agent_id: str, event_type: str, data: dict):
            captured_events.append((agent_id, event_type, data))

        sse_manager.broadcast_from_thread = mock_broadcast

        try:
            # Update agent status to stopped
            state_manager.update_agent_status("test-agent", AgentStatus.STOPPED)

            # Verify the correct event type was broadcasted
            assert len(captured_events) == 1
            agent_id, event_type, data = captured_events[0]
            assert agent_id == "test-agent"
            assert event_type == "agent_stopped"
            assert data["status"] == "stopped"

        finally:
            # Restore original method
            sse_manager.broadcast_from_thread = original_broadcast

    def test_agent_other_status_broadcasts_updated_event(self):
        """Test that other agent statuses broadcast the generic updated event."""
        # Create a test agent
        agent = state_manager.create_agent("test-agent", "Test Agent", "offline")
        agent.status = AgentStatus.RUNNING

        # Mock the broadcast method to capture the event type
        original_broadcast = sse_manager.broadcast_from_thread
        captured_events = []

        def mock_broadcast(agent_id: str, event_type: str, data: dict):
            captured_events.append((agent_id, event_type, data))

        sse_manager.broadcast_from_thread = mock_broadcast

        try:
            # Update agent status to idle (not a specific event type)
            state_manager.update_agent_status("test-agent", AgentStatus.IDLE)

            # Verify the generic event type was broadcasted
            assert len(captured_events) == 1
            agent_id, event_type, data = captured_events[0]
            assert agent_id == "test-agent"
            assert event_type == "agent_updated"
            assert data["status"] == "idle"

        finally:
            # Restore original method
            sse_manager.broadcast_from_thread = original_broadcast
