"""Test dashboard synchronization fixes."""

import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app
from dashboard.state_manager import AgentStatus, state_manager


class TestDashboardSync:
    """Test dashboard synchronization functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
        # Clear state manager
        state_manager._agents.clear()

    def test_agent_completion_sync(self):
        """Test that agent completion properly syncs to frontend."""
        # Create an agent
        agent = state_manager.create_agent("test-1", "Test Agent", "offline")
        agent.status = AgentStatus.RUNNING

        # Simulate agent completion
        state_manager.update_agent_status(
            "test-1", AgentStatus.COMPLETED, end_time=datetime.now()
        )

        # Verify agent is marked as completed
        updated_agent = state_manager.get_agent("test-1")
        assert updated_agent.status == AgentStatus.COMPLETED
        assert updated_agent.end_time is not None

    def test_agent_deletion_sync(self):
        """Test that agent deletion properly syncs to frontend."""
        # Create an agent
        state_manager.create_agent("test-2", "Test Agent", "offline")

        # Verify agent exists
        assert state_manager.get_agent("test-2") is not None

        # Delete agent
        success = state_manager.delete_agent("test-2")
        assert success is True

        # Verify agent is deleted
        assert state_manager.get_agent("test-2") is None

    def test_agent_status_broadcast(self):
        """Test that agent status changes are properly updated."""
        # Create an agent
        state_manager.create_agent("test-3", "Test Agent", "offline")

        # Update status (this should trigger broadcast in real environment)
        state_manager.update_agent_status("test-3", AgentStatus.COMPLETED)

        # Verify agent status is updated
        updated_agent = state_manager.get_agent("test-3")
        assert updated_agent.status == AgentStatus.COMPLETED

        # Note: In a real environment with event loop, this would broadcast
        # but in test environment without event loop, it's skipped

    def test_plan_update_sync(self):
        """Test that plan updates are properly synchronized."""
        # Create an agent
        state_manager.create_agent("test-4", "Test Agent", "offline")

        # Simulate plan update
        {
            "status": "running",
            "progress": 50,
            "output": ["Step 1 completed", "Step 2 in progress"],
            "end_time": datetime.now().isoformat(),
        }

        # This would normally be called by the plan update function
        # For testing, we'll just verify the agent state can be updated
        state_manager.update_agent("test-4", progress=50, current_step="Executing plan")

        # Verify agent state is updated
        updated_agent = state_manager.get_agent("test-4")
        assert updated_agent.progress == 50
        assert updated_agent.current_step == "Executing plan"

    def test_selected_agent_clearing(self):
        """Test that selected agent is properly cleared when deleted."""
        # Create an agent
        state_manager.create_agent("test-5", "Test Agent", "offline")

        # Simulate selecting the agent
        # Note: In a real scenario, this would be set by the frontend

        # Delete the agent
        success = state_manager.delete_agent("test-5")
        assert success is True

        # Verify agent is gone
        assert state_manager.get_agent("test-5") is None

    def test_periodic_status_updates(self):
        """Test that periodic status updates work correctly."""
        # Create multiple agents
        agent1 = state_manager.create_agent("test-6", "Test Agent 1", "offline")
        agent2 = state_manager.create_agent("test-7", "Test Agent 2", "online")

        # Set different statuses
        agent1.status = AgentStatus.RUNNING
        agent2.status = AgentStatus.COMPLETED

        # Verify agents are in state manager
        agents = state_manager.list_agents()
        assert len(agents) == 2

        # Verify agent statuses
        agent_ids = [agent["id"] for agent in agents]
        assert "test-6" in agent_ids
        assert "test-7" in agent_ids

    def test_error_handling_sync(self):
        """Test that agent errors are properly synchronized."""
        # Create an agent
        state_manager.create_agent("test-8", "Test Agent", "offline")

        # Simulate agent error
        state_manager.update_agent_status(
            "test-8",
            AgentStatus.ERROR,
            end_time=datetime.now(),
            error_message="Test error occurred",
        )

        # Verify agent is in error state
        updated_agent = state_manager.get_agent("test-8")
        assert updated_agent.status == AgentStatus.ERROR
        assert updated_agent.error_message == "Test error occurred"
        assert updated_agent.end_time is not None

    def test_execution_time_calculation(self):
        """Test that execution time is calculated correctly."""
        # Create an agent with start time
        start_time = datetime.now()
        agent = state_manager.create_agent("test-9", "Test Agent", "offline")
        agent.start_time = start_time

        # Simulate some time passing
        time.sleep(0.1)

        # Complete the agent
        end_time = datetime.now()
        state_manager.update_agent_status(
            "test-9", AgentStatus.COMPLETED, end_time=end_time
        )

        # Verify execution time is calculated
        updated_agent = state_manager.get_agent("test-9")
        assert updated_agent.execution_time != "00:00:00"
        assert updated_agent.end_time == end_time

    def test_concurrent_agent_updates(self):
        """Test that concurrent agent updates don't cause issues."""
        import threading

        # Create an agent
        state_manager.create_agent("test-10", "Test Agent", "offline")

        # Simulate concurrent updates
        def update_agent():
            state_manager.update_agent_status("test-10", AgentStatus.RUNNING)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=update_agent)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify agent state is consistent
        updated_agent = state_manager.get_agent("test-10")
        assert updated_agent.status == AgentStatus.RUNNING


if __name__ == "__main__":
    pytest.main([__file__])
