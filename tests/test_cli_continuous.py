#!/usr/bin/env python3
"""Test suite for continuous mode CLI functionality."""

from io import StringIO
from unittest.mock import Mock, patch

import pytest

# Import the main function and related components
from agent.agent import AgentState, main, should_abort_continuous


class TestCLIContinuous:
    """Test CLI continuous mode functionality."""

    def test_should_abort_continuous_no_criteria_met(self) -> None:
        """Test that should_abort_continuous returns False when no criteria are met."""
        state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=[],
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=5,
            start_time=1000.0,
            time_limit_secs=600,
            citations=[],
            citation_counter=1,
            reflection_json=None,
            reflection_failures=None,
        )

        assert should_abort_continuous(state) is False

    def test_should_abort_continuous_iteration_limit_met(self) -> None:
        """Test that should_abort_continuous returns True when iteration limit is met."""
        state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=[],
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=25,  # At the limit
            start_time=1000.0,
            time_limit_secs=600,
            citations=[],
            citation_counter=1,
            reflection_json=None,
            reflection_failures=None,
        )

        assert should_abort_continuous(state) is True

    def test_should_abort_continuous_time_limit_met(self) -> None:
        """Test that should_abort_continuous returns True when time limit is met."""
        state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=[],
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=5,
            start_time=1000.0,
            time_limit_secs=300,  # 5 minutes
            citations=[],
            citation_counter=1,
            reflection_json=None,
            reflection_failures=None,
        )

        # Mock time.time to return a time that exceeds the limit
        with patch("time.time", return_value=1400.0):  # 400 seconds later
            assert should_abort_continuous(state) is True

    def test_should_abort_continuous_goal_satisfied(self) -> None:
        """Test that should_abort_continuous returns True when goal is satisfied."""
        state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=[],
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=5,
            start_time=1000.0,
            time_limit_secs=600,
            citations=[],
            citation_counter=1,
            reflection_json={"task_completed": True, "next_action": "end"},
            reflection_failures=None,
        )

        assert should_abort_continuous(state) is True


class TestCLIArguments:
    """Test CLI argument parsing."""

    @patch("sys.argv", ["ikoma", "--continuous", "--goal", "test goal"])
    def test_continuous_mode_with_goal(self) -> None:
        """Test that continuous mode works with a valid goal."""
        with patch("agent.agent.create_agent") as mock_create_agent:
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent
            mock_agent.invoke.return_value = {"messages": []}

            # Capture stdout to check banner output
            with patch("sys.stdout", new=StringIO()) as mock_stdout:
                try:
                    main()
                except SystemExit:
                    pass  # Expected to exit after continuous mode

                output = mock_stdout.getvalue()
                assert "Continuous mode activated" in output
                assert "test goal" in output

    @patch("sys.argv", ["ikoma", "--continuous"])
    def test_continuous_mode_without_goal(self) -> None:
        """Test that continuous mode fails without a goal."""
        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            try:
                main()
            except SystemExit as e:
                assert e.code == 2  # argparse error code
                error_output = mock_stderr.getvalue()
                assert "--goal is required" in error_output

    @patch(
        "sys.argv", ["ikoma", "--continuous", "--goal", "test", "--max-iterations", "5"]
    )
    def test_continuous_mode_custom_iterations(self) -> None:
        """Test that custom max iterations are respected."""
        with patch("agent.agent.create_agent") as mock_create_agent:
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent
            mock_agent.invoke.return_value = {"messages": []}

            with patch("sys.stdout", new=StringIO()) as mock_stdout:
                try:
                    main()
                except SystemExit:
                    pass

                output = mock_stdout.getvalue()
                assert "Max iterations: 5" in output

    @patch(
        "sys.argv", ["ikoma", "--continuous", "--goal", "test", "--time-limit", "15"]
    )
    def test_continuous_mode_custom_time_limit(self) -> None:
        """Test that custom time limit is respected."""
        with patch("agent.agent.create_agent") as mock_create_agent:
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent
            mock_agent.invoke.return_value = {"messages": []}

            with patch("sys.stdout", new=StringIO()) as mock_stdout:
                try:
                    main()
                except SystemExit:
                    pass

                output = mock_stdout.getvalue()
                assert "Time limit: 15 min" in output

    @patch("sys.argv", ["ikoma"])
    def test_interactive_mode_default(self) -> None:
        """Test that interactive mode is the default."""
        with patch("agent.agent.create_agent") as mock_create_agent:
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent

            # Mock input to exit immediately
            with patch("builtins.input", return_value="quit"):
                with patch("sys.stdout", new=StringIO()) as mock_stdout:
                    main()

                    output = mock_stdout.getvalue()
                    assert "Hello! I'm your AI assistant" in output


class TestContinuousModeIntegration:
    """Integration tests for continuous mode."""

    @patch(
        "sys.argv",
        ["ikoma", "--continuous", "--goal", "test goal", "--max-iterations", "2"],
    )
    def test_continuous_mode_iteration_limit_integration(self) -> None:
        """Test that continuous mode respects iteration limits in actual execution."""
        with patch("agent.agent.create_agent") as mock_create_agent:
            mock_agent = Mock()
            mock_create_agent.return_value = mock_agent

            # Mock agent to simulate a task that would continue indefinitely
            def mock_invoke(initial_state: dict) -> dict:
                # Simulate the agent always wanting to continue
                return {
                    "messages": [Mock(content="Test response")],
                    "continue_planning": True,
                    "current_iteration": initial_state.get("current_iteration", 0) + 1,
                    "max_iterations": initial_state.get("max_iterations", 25),
                    "start_time": initial_state.get("start_time"),
                    "time_limit_secs": initial_state.get("time_limit_secs", 600),
                }

            mock_agent.invoke.side_effect = mock_invoke

            with patch("sys.stdout", new=StringIO()):
                try:
                    main()
                except SystemExit:
                    pass

                # Verify that the agent was invoked with correct initial state
                mock_create_agent.assert_called_once()
                mock_agent.invoke.assert_called_once()

                # Check that the initial state had the correct parameters
                call_args = mock_agent.invoke.call_args[0][0]
                assert call_args["max_iterations"] == 2
                assert call_args["start_time"] is not None
                assert call_args["time_limit_secs"] == 600  # 10 minutes default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
