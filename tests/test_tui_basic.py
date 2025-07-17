"""Basic TUI functionality tests."""

from unittest.mock import MagicMock, patch

import pytest

from agent.ui.state_broadcaster import broadcaster
from agent.ui.tui import AsyncLogger, IkomaTUI


class TestTUI:
    """Test TUI basic functionality."""

    def test_tui_initialization(self):
        """Test that TUI can be initialized without errors."""
        tui = IkomaTUI()
        assert tui is not None
        assert hasattr(tui, "console")
        assert hasattr(tui, "layout")

    def test_async_logger(self):
        """Test async logger functionality."""
        logger = AsyncLogger("test.log")
        assert logger is not None
        logger.log("TEST", "Test message")
        logger.stop()

    def test_broadcaster_events(self):
        """Test that broadcaster can handle events."""
        # Test that broadcaster exists and can be used
        assert broadcaster is not None

        # Test event subscription (should not raise)
        mock_callback = MagicMock()
        broadcaster.subscribe("test_event", mock_callback)

        # Test event broadcasting (should not raise)
        broadcaster.broadcast("test_event", {"test": "data"})

    @patch("rich.console.Console")
    def test_tui_event_handling(self, mock_console):
        """Test TUI event handling."""
        tui = IkomaTUI()

        # Test planning start event
        test_data = {"user_request": "Test request"}
        tui.on_planning_start(test_data)
        assert tui.agent_state.get("planning") is True
        assert tui.agent_state.get("user_request") == "Test request"

        # Test plan generated event
        plan_data = {"plan": [], "step_count": 0}
        tui.on_plan_generated(plan_data)
        assert tui.agent_state.get("planning") is False
        assert tui.agent_state.get("step_count") == 0

        # Test step start event
        step_data = {
            "step_index": 1,
            "tool_name": "test_tool",
            "description": "Test step",
        }
        tui.on_step_start(step_data)
        assert tui.agent_state.get("current_step") == 1
        assert tui.agent_state.get("current_tool") == "test_tool"

        # Test step complete event
        complete_data = {"step_index": 1, "status": "success", "result": "Test result"}
        tui.on_step_complete(complete_data)
        assert len(tui.execution_results) > 0

        # Test reflection event
        reflection_data = {
            "reasoning": "Test reasoning",
            "summary": "Test summary",
            "success_rate": "100%",
        }
        tui.on_reflection(reflection_data)
        assert len(tui.changelog) > 0


if __name__ == "__main__":
    pytest.main([__file__])
