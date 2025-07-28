import asyncio
from datetime import datetime

import pytest

from dashboard.sse_manager import sse_manager
from dashboard.state_manager import AgentState, AgentStatus, state_manager


class TestStateManager:
    """Test the unified state manager."""

    def setup_method(self):
        """Clear state before each test."""
        state_manager._agents.clear()

    def test_create_agent(self):
        """Test creating a new agent."""
        agent = state_manager.create_agent("test-1", "Test Agent", "online")

        assert agent.agent_id == "test-1"
        assert agent.name == "Test Agent"
        assert agent.demo_type == "online"
        assert agent.status == AgentStatus.IDLE
        assert agent.start_time is not None

    def test_update_agent(self):
        """Test updating agent state."""
        state_manager.create_agent("test-2", "Test Agent", "offline")

        state_manager.update_agent("test-2", status=AgentStatus.RUNNING, progress=50)

        updated_agent = state_manager.get_agent("test-2")
        assert updated_agent.status == AgentStatus.RUNNING
        assert updated_agent.progress == 50

    def test_delete_agent(self):
        """Test deleting an agent."""
        state_manager.create_agent("test-3", "Test Agent")

        assert state_manager.delete_agent("test-3") is True
        assert state_manager.get_agent("test-3") is None
        assert state_manager.delete_agent("nonexistent") is False

    def test_list_agents(self):
        """Test listing all agents."""
        state_manager.create_agent("test-4", "Agent 1", "online")
        state_manager.create_agent("test-5", "Agent 2", "offline")

        agents = state_manager.list_agents()
        assert len(agents) == 2
        assert any(agent["id"] == "test-4" for agent in agents)
        assert any(agent["id"] == "test-5" for agent in agents)

    def test_agent_count_by_status(self):
        """Test counting agents by status."""
        agent1 = state_manager.create_agent("test-6", "Agent 1")
        agent2 = state_manager.create_agent("test-7", "Agent 2")

        agent1.status = AgentStatus.RUNNING
        agent2.status = AgentStatus.COMPLETED

        assert state_manager.get_agent_count_by_status(AgentStatus.IDLE) == 0
        assert state_manager.get_agent_count_by_status(AgentStatus.RUNNING) == 1
        assert state_manager.get_agent_count_by_status(AgentStatus.COMPLETED) == 1


class TestSSEManager:
    """Test the SSE connection manager."""

    def setup_method(self):
        """Clear connections before each test."""
        sse_manager.connections.clear()

    def test_add_remove_connection(self):
        """Test adding and removing connections."""

        async def _test():
            queue = asyncio.Queue()

            await sse_manager.add_connection(queue)
            assert len(sse_manager.connections) == 1

            await sse_manager.remove_connection(queue)
            assert len(sse_manager.connections) == 0

        asyncio.run(_test())

    def test_broadcast(self):
        """Test broadcasting messages."""

        async def _test():
            queue1 = asyncio.Queue()
            queue2 = asyncio.Queue()

            await sse_manager.add_connection(queue1)
            await sse_manager.add_connection(queue2)

            event = {"event": "test", "data": "test_data"}
            await sse_manager.broadcast(event)

            # Check that messages were sent
            msg1 = await queue1.get()
            msg2 = await queue2.get()

            assert msg1["event"] == "test"
            assert msg2["event"] == "test"

        asyncio.run(_test())

    def test_get_connection_count(self):
        """Test getting connection count."""
        assert sse_manager.get_connection_count() == 0


class TestAgentState:
    """Test the AgentState dataclass."""

    def test_to_dict(self):
        """Test converting agent state to dictionary."""
        agent = AgentState(
            agent_id="test-8",
            name="Test Agent",
            status=AgentStatus.RUNNING,
            demo_type="online",
            progress=75,
        )

        data = agent.to_dict()

        assert data["id"] == "test-8"
        assert data["name"] == "Test Agent"
        assert data["status"] == "running"
        assert data["demo_type"] == "online"
        assert data["progress"] == 75
        assert data["is_demo"] is True

    def test_update_progress(self):
        """Test updating progress."""
        agent = AgentState(
            agent_id="test-9", name="Test Agent", status=AgentStatus.RUNNING
        )

        agent.update_progress(60, 3, 5)

        assert agent.progress == 60
        assert agent.steps_completed == 3
        assert agent.total_steps == 5

    def test_update_execution_time(self):
        """Test updating execution time."""
        agent = AgentState(
            agent_id="test-10",
            name="Test Agent",
            status=AgentStatus.RUNNING,
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 10, 1, 30),
        )

        agent.update_execution_time()

        assert agent.execution_time == "0:01:30"

    def test_add_output_line(self):
        """Test adding output lines."""
        agent = AgentState(
            agent_id="test-11", name="Test Agent", status=AgentStatus.RUNNING
        )

        agent.add_output_line("Test output line")

        assert len(agent.output_lines) == 1
        assert agent.output_lines[0] == "Test output line"

    def test_set_error(self):
        """Test setting error state."""
        agent = AgentState(
            agent_id="test-12", name="Test Agent", status=AgentStatus.RUNNING
        )

        agent.set_error("Test error message")

        assert agent.status == AgentStatus.ERROR
        assert agent.error_message == "Test error message"


if __name__ == "__main__":
    pytest.main([__file__])
