#!/usr/bin/env python3
"""Test suite for reflect_node termination behavior."""

from unittest.mock import Mock, patch

import pytest

from agent.agent import AgentState, reflect_node


class TestReflectTermination:
    """Test that reflect_node properly handles termination criteria."""

    @patch("time.time")
    def test_reflect_node_stops_on_time_limit(self, mock_time: Mock) -> None:
        """Test that reflect_node stops when TimeLimitCriterion triggers."""
        # Mock time to simulate elapsed time
        mock_time.return_value = 1000.0

        state = AgentState(
            messages=[Mock(content="Test message")],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=[
                {"status": "success", "step": 1, "description": "Test", "result": "OK"}
            ],
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=5,
            start_time=1000.0 - 700,  # 11+ minutes ago (over 10 min limit)
            time_limit_secs=600,  # 10 minutes
            citations=[],
            citation_counter=1,
        )

        # Mock LLM response
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content='{"task_completed": false, "next_action": "continue", "reasoning": "test"}'
        )

        # Mock config and store
        config = {}
        store = Mock()

        # Call reflect_node
        result = reflect_node(state, config, store=store, llm=mock_llm)

        # Verify that continue_planning was set to False due to time limit
        assert result["continue_planning"] is False

    @patch("time.time")
    def test_reflect_node_continues_within_time_limit(self, mock_time: Mock) -> None:
        """Test that reflect_node continues when within time limit."""
        # Mock time to simulate elapsed time
        mock_time.return_value = 1000.0

        state = AgentState(
            messages=[Mock(content="Test message")],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=[
                {"status": "success", "step": 1, "description": "Test", "result": "OK"}
            ],
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=5,
            start_time=1000.0 - 300,  # 5 minutes ago (under 10 min limit)
            time_limit_secs=600,  # 10 minutes
            citations=[],
            citation_counter=1,
        )

        # Mock LLM response indicating task not completed
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content='{"task_completed": false, "next_action": "continue", "reasoning": "test"}'
        )

        # Mock config and store
        config = {}
        store = Mock()

        # Call reflect_node
        result = reflect_node(state, config, store=store, llm=mock_llm)

        # Verify that continue_planning remains True when within limits
        assert result["continue_planning"] is True

    @patch("time.time")
    def test_reflect_node_handles_multiple_criteria(self, mock_time: Mock) -> None:
        """Test that reflect_node handles both iteration and time criteria."""
        # Mock time to simulate elapsed time
        mock_time.return_value = 1000.0

        state = AgentState(
            messages=[Mock(content="Test message")],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=[
                {"status": "success", "step": 1, "description": "Test", "result": "OK"}
            ],
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=30,  # Over iteration limit
            start_time=1000.0 - 300,  # 5 minutes ago (under time limit)
            time_limit_secs=600,  # 10 minutes
            citations=[],
            citation_counter=1,
        )

        # Mock LLM response
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content='{"task_completed": false, "next_action": "continue", "reasoning": "test"}'
        )

        # Mock config and store
        config = {}
        store = Mock()

        # Call reflect_node
        result = reflect_node(state, config, store=store, llm=mock_llm)

        # Verify that continue_planning was set to False due to iteration limit
        assert result["continue_planning"] is False

    def test_reflect_node_no_start_time(self) -> None:
        """Test that reflect_node handles None start_time gracefully."""
        state = AgentState(
            messages=[Mock(content="Test message")],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=[
                {"status": "success", "step": 1, "description": "Test", "result": "OK"}
            ],
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=5,
            start_time=None,  # No start time
            time_limit_secs=600,
            citations=[],
            citation_counter=1,
        )

        # Mock LLM response
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(
            content='{"task_completed": false, "next_action": "continue", "reasoning": "test"}'
        )

        # Mock config and store
        config = {}
        store = Mock()

        # Call reflect_node
        result = reflect_node(state, config, store=store, llm=mock_llm)

        # Verify that continue_planning remains True when no start_time
        assert result["continue_planning"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
