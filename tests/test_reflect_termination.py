#!/usr/bin/env python3
"""Test suite for reflect_node termination behavior."""

from unittest.mock import Mock, patch

import pytest

from agent.agent import AgentState, reflect_node


class TestReflectTermination:
    """Test reflect_node termination behavior with unified criteria."""

    def test_reflect_node_continues_when_no_criteria_met(self) -> None:
        """Test that reflect_node continues when no termination criteria are met."""
        # Mock LLM response that doesn't indicate completion
        mock_llm = Mock()
        mock_llm.invoke.return_value.content = (
            '{"task_completed": false, "next_action": "continue", "reasoning": "test"}'
        )

        # Create a mock message
        mock_message = Mock()
        mock_message.content = "Test user request"

        state = AgentState(
            messages=[
                mock_message
            ],  # Add a message so reflect_node can access messages[-1]
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
            checkpoint_every=None,
            last_checkpoint_iter=0,
        )

        config = {"configurable": {"user_id": "test"}}
        mock_store = Mock()

        # Mock time.time to ensure we're within the time limit
        with patch(
            "time.time", return_value=1200.0
        ):  # 200 seconds later (under 600 limit)
            result = reflect_node(state, config, store=mock_store, llm=mock_llm)

        # Should continue planning
        assert result["continue_planning"] is True
        assert result["reflection_json"] == {
            "task_completed": False,
            "next_action": "continue",
            "reasoning": "test",
        }

    def test_reflect_node_stops_when_goal_satisfied(self) -> None:
        """Test that reflect_node stops when goal satisfaction criterion is met."""
        # Mock LLM response that indicates completion
        mock_llm = Mock()
        mock_llm.invoke.return_value.content = (
            '{"task_completed": true, "next_action": "end", "reasoning": "test"}'
        )

        # Create a mock message
        mock_message = Mock()
        mock_message.content = "Test user request"

        state = AgentState(
            messages=[
                mock_message
            ],  # Add a message so reflect_node can access messages[-1]
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
            checkpoint_every=None,
            last_checkpoint_iter=0,
        )

        config = {"configurable": {"user_id": "test"}}
        mock_store = Mock()

        result = reflect_node(state, config, store=mock_store, llm=mock_llm)

        # Should stop planning
        assert result["continue_planning"] is False
        assert result["reflection_json"] == {
            "task_completed": True,
            "next_action": "end",
            "reasoning": "test",
        }

    def test_reflect_node_stops_when_iteration_limit_reached(self) -> None:
        """Test that reflect_node stops when iteration limit criterion is met."""
        # Mock LLM response that doesn't indicate completion
        mock_llm = Mock()
        mock_llm.invoke.return_value.content = (
            '{"task_completed": false, "next_action": "continue", "reasoning": "test"}'
        )

        # Create a mock message
        mock_message = Mock()
        mock_message.content = "Test user request"

        state = AgentState(
            messages=[
                mock_message
            ],  # Add a message so reflect_node can access messages[-1]
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
            checkpoint_every=None,
            last_checkpoint_iter=0,
        )

        config = {"configurable": {"user_id": "test"}}
        mock_store = Mock()

        result = reflect_node(state, config, store=mock_store, llm=mock_llm)

        # Should stop planning due to iteration limit
        assert result["continue_planning"] is False
        assert result["reflection_json"] == {
            "task_completed": False,
            "next_action": "continue",
            "reasoning": "test",
        }

    def test_reflect_node_stops_when_time_limit_reached(self) -> None:
        """Test that reflect_node stops when time limit criterion is met."""
        # Mock LLM response that doesn't indicate completion
        mock_llm = Mock()
        mock_llm.invoke.return_value.content = (
            '{"task_completed": false, "next_action": "continue", "reasoning": "test"}'
        )

        # Create a mock message
        mock_message = Mock()
        mock_message.content = "Test user request"

        state = AgentState(
            messages=[
                mock_message
            ],  # Add a message so reflect_node can access messages[-1]
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
            checkpoint_every=None,
            last_checkpoint_iter=0,
        )

        config = {"configurable": {"user_id": "test"}}
        mock_store = Mock()

        # Mock time.time to return a time that exceeds the limit
        with patch("time.time", return_value=1400.0):  # 400 seconds later
            result = reflect_node(state, config, store=mock_store, llm=mock_llm)

        # Should stop planning due to time limit
        assert result["continue_planning"] is False
        assert result["reflection_json"] == {
            "task_completed": False,
            "next_action": "continue",
            "reasoning": "test",
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
