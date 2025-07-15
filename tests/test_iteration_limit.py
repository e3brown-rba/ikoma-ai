"""Tests for iteration limit termination heuristic."""

import os
from unittest.mock import Mock, patch

import pytest

from agent.constants import MAX_ITER
from agent.heuristics.iteration import IterationLimitCriterion


class TestIterationLimitCriterion:
    """Test the IterationLimitCriterion class."""

    def test_should_stop_below_limit(self):
        """Test that criterion returns False when below iteration limit."""
        criterion = IterationLimitCriterion()
        state = {"current_iteration": 1, "max_iterations": 5}
        assert not criterion.should_stop(state)

    def test_should_stop_at_limit(self):
        """Test that criterion returns True when at iteration limit."""
        criterion = IterationLimitCriterion()
        state = {"current_iteration": 5, "max_iterations": 5}
        assert criterion.should_stop(state)

    def test_should_stop_above_limit(self):
        """Test that criterion returns True when above iteration limit."""
        criterion = IterationLimitCriterion()
        state = {"current_iteration": 6, "max_iterations": 5}
        assert criterion.should_stop(state)

    def test_should_stop_default_values(self):
        """Test that criterion uses default values when state is missing fields."""
        criterion = IterationLimitCriterion()
        state = {}
        # Should use default max_iterations=25, current_iteration=0
        assert not criterion.should_stop(state)

    def test_should_stop_partial_state(self):
        """Test that criterion handles partial state gracefully."""
        criterion = IterationLimitCriterion()
        state = {"current_iteration": 10}
        # Should use default max_iterations=25
        assert not criterion.should_stop(state)


class TestConstants:
    """Test the MAX_ITER constant."""

    def test_default_value(self):
        """Test that MAX_ITER has the expected default value."""
        assert MAX_ITER == 25

    @patch.dict(os.environ, {"IKOMA_MAX_ITER": "7"})
    def test_environment_override(self):
        """Test that MAX_ITER can be overridden via environment variable."""
        # Re-import to get the new environment value
        import importlib

        import agent.constants

        importlib.reload(agent.constants)

        assert agent.constants.MAX_ITER == 7

    @patch.dict(os.environ, {"IKOMA_MAX_ITER": "invalid"})
    def test_invalid_environment_value(self):
        """Test that invalid environment values are handled gracefully."""
        # This should raise a ValueError when trying to convert "invalid" to int
        with pytest.raises(ValueError):
            import importlib

            import agent.constants

            importlib.reload(agent.constants)


class TestCLIIntegration:
    """Test CLI integration with iteration limits."""

    @patch("agent.agent.create_agent")
    @patch("agent.agent._render_final_response")
    @patch("builtins.input", return_value="quit")
    def test_cli_max_iter_override(self, mock_input, mock_render, mock_create_agent):
        """Test that --max-iter CLI argument overrides environment and defaults."""
        from agent.agent import main

        # Mock the agent
        mock_agent = Mock()
        mock_create_agent.return_value = mock_agent

        # Mock the invoke method to capture the initial state
        captured_state = {}

        def mock_invoke(state, config=None):
            captured_state.update(state)
            return {"messages": []}

        mock_agent.invoke = mock_invoke

        # Test with --max-iter argument
        with patch(
            "sys.argv",
            ["agent.py", "--continuous", "--goal", "test goal", "--max-iter", "5"],
        ):
            with patch("sys.exit"):
                main()

        # Verify that max_iterations was set to the CLI value
        assert captured_state.get("max_iterations") == 5

    @patch("agent.agent.create_agent")
    @patch("agent.agent._render_final_response")
    @patch("builtins.input", return_value="quit")
    def test_cli_max_iterations_fallback(
        self, mock_input, mock_render, mock_create_agent
    ):
        """Test that --max-iterations is used when --max-iter is not provided."""
        from agent.agent import main

        # Mock the agent
        mock_agent = Mock()
        mock_create_agent.return_value = mock_agent

        # Mock the invoke method to capture the initial state
        captured_state = {}

        def mock_invoke(state, config=None):
            captured_state.update(state)
            return {"messages": []}

        mock_agent.invoke = mock_invoke

        # Test with --max-iterations argument but no --max-iter
        with patch(
            "sys.argv",
            [
                "agent.py",
                "--continuous",
                "--goal",
                "test goal",
                "--max-iterations",
                "10",
            ],
        ):
            with patch("sys.exit"):
                main()

        # Verify that max_iterations was set to the max-iterations value
        assert captured_state.get("max_iterations") == 10

    @patch("agent.agent.create_agent")
    @patch("agent.agent._render_final_response")
    @patch("builtins.input", return_value="quit")
    def test_cli_priority_order(self, mock_input, mock_render, mock_create_agent):
        """Test that --max-iter takes priority over --max-iterations."""
        from agent.agent import main

        # Mock the agent
        mock_agent = Mock()
        mock_create_agent.return_value = mock_agent

        # Mock the invoke method to capture the initial state
        captured_state = {}

        def mock_invoke(state, config=None):
            captured_state.update(state)
            return {"messages": []}

        mock_agent.invoke = mock_invoke

        # Test with both arguments - --max-iter should take priority
        with patch(
            "sys.argv",
            [
                "agent.py",
                "--continuous",
                "--goal",
                "test goal",
                "--max-iterations",
                "10",
                "--max-iter",
                "5",
            ],
        ):
            with patch("sys.exit"):
                main()

        # Verify that max_iterations was set to the --max-iter value
        assert captured_state.get("max_iterations") == 5
