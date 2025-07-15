#!/usr/bin/env python3
"""Integration tests for goal satisfaction termination heuristic."""

from unittest.mock import Mock, patch

from agent.agent import AgentState, reflect_node


class TestGoalSatisfactionIntegration:
    """Integration tests for goal satisfaction termination heuristic."""

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
            execution_results=[
                {
                    "status": "success",
                    "step": 1,
                    "description": "Test",
                    "result": "OK",
                }
            ],
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

    def test_reflect_node_continues_when_goal_not_satisfied(self) -> None:
        """Test that reflect_node continues when goal satisfaction criterion is not met."""
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
            execution_results=[
                {
                    "status": "success",
                    "step": 1,
                    "description": "Test",
                    "result": "OK",
                }
            ],
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

    def test_reflect_node_handles_next_action_end(self) -> None:
        """Test that reflect_node stops when next_action is 'end' even if task_completed is false."""
        # Mock LLM response with next_action: "end" but task_completed: false
        mock_llm = Mock()
        mock_llm.invoke.return_value.content = (
            '{"task_completed": false, "next_action": "end", "reasoning": "test"}'
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
            execution_results=[
                {
                    "status": "success",
                    "step": 1,
                    "description": "Test",
                    "result": "OK",
                }
            ],
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

        config = {"configurable": {"user_id": "test"}}
        mock_store = Mock()

        result = reflect_node(state, config, store=mock_store, llm=mock_llm)

        # Should stop planning due to next_action: "end"
        assert result["continue_planning"] is False
        assert result["reflection_json"] == {
            "task_completed": False,
            "next_action": "end",
            "reasoning": "test",
        }

    def test_reflect_node_handles_malformed_json_gracefully(self) -> None:
        """Test that reflect_node handles malformed JSON responses gracefully."""
        # Mock LLM response with malformed JSON
        mock_llm = Mock()
        mock_llm.invoke.return_value.content = (
            '{"task_completed": true, "next_action": "end", "reasoning": "test"'
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
            execution_results=[
                {
                    "status": "success",
                    "step": 1,
                    "description": "Test",
                    "result": "OK",
                }
            ],
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

        config = {"configurable": {"user_id": "test"}}
        mock_store = Mock()

        # Mock time.time to ensure we're within the time limit
        with patch(
            "time.time", return_value=1200.0
        ):  # 200 seconds later (under 600 limit)
            result = reflect_node(state, config, store=mock_store, llm=mock_llm)

        # Should stop planning due to JSON parsing error
        assert result["continue_planning"] is False
        # Should have recorded the failure
        assert result["reflection_failures"] is not None
        assert len(result["reflection_failures"]) == 1
        failure = result["reflection_failures"][0]
        assert "error" in failure
        assert "raw_response" in failure
        assert "prompt" in failure
        assert "timestamp" in failure
        assert failure["raw_response"].startswith('{"task_completed"')
