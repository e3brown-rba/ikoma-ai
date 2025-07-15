#!/usr/bin/env python3
"""Test suite for GoalSatisfiedCriterion."""

from agent.heuristics.goal import GoalSatisfiedCriterion


class TestGoalSatisfiedCriterion:
    """Test the GoalSatisfiedCriterion class."""

    def test_should_stop_task_completed_true(self) -> None:
        """Test that criterion returns True when task_completed is True."""
        criterion = GoalSatisfiedCriterion()
        state = {"reflection_json": {"task_completed": True}}
        assert criterion.should_stop(state) is True

    def test_should_stop_task_completed_false(self) -> None:
        """Test that criterion returns False when task_completed is False."""
        criterion = GoalSatisfiedCriterion()
        state = {"reflection_json": {"task_completed": False}}
        assert criterion.should_stop(state) is False

    def test_should_stop_next_action_end(self) -> None:
        """Test that criterion returns True when next_action is 'end'."""
        criterion = GoalSatisfiedCriterion()
        state = {"reflection_json": {"next_action": "end"}}
        assert criterion.should_stop(state) is True

    def test_should_stop_next_action_continue(self) -> None:
        """Test that criterion returns False when next_action is 'continue'."""
        criterion = GoalSatisfiedCriterion()
        state = {"reflection_json": {"next_action": "continue"}}
        assert criterion.should_stop(state) is False

    def test_should_stop_both_conditions_true(self) -> None:
        """Test that criterion returns True when both conditions are met."""
        criterion = GoalSatisfiedCriterion()
        state = {"reflection_json": {"task_completed": True, "next_action": "end"}}
        assert criterion.should_stop(state) is True

    def test_should_stop_no_reflection_json(self) -> None:
        """Test that criterion returns False when reflection_json is missing."""
        criterion = GoalSatisfiedCriterion()
        state = {}
        assert criterion.should_stop(state) is False

    def test_should_stop_reflection_json_none(self) -> None:
        """Test that criterion returns False when reflection_json is None."""
        criterion = GoalSatisfiedCriterion()
        state = {"reflection_json": None}
        assert criterion.should_stop(state) is False

    def test_should_stop_reflection_json_empty(self) -> None:
        """Test that criterion returns False when reflection_json is empty."""
        criterion = GoalSatisfiedCriterion()
        state = {"reflection_json": {}}
        assert criterion.should_stop(state) is False

    def test_should_stop_missing_fields(self) -> None:
        """Test that criterion returns False when required fields are missing."""
        criterion = GoalSatisfiedCriterion()
        state = {"reflection_json": {"other_field": "value"}}
        assert criterion.should_stop(state) is False

    def test_should_stop_task_completed_string_true(self) -> None:
        """Test that criterion handles string 'true' as False (strict boolean check)."""
        criterion = GoalSatisfiedCriterion()
        state = {"reflection_json": {"task_completed": "true"}}
        assert criterion.should_stop(state) is False

    def test_should_stop_task_completed_string_false(self) -> None:
        """Test that criterion handles string 'false' as False."""
        criterion = GoalSatisfiedCriterion()
        state = {"reflection_json": {"task_completed": "false"}}
        assert criterion.should_stop(state) is False

    def test_should_stop_task_completed_1(self) -> None:
        """Test that criterion handles integer 1 as False (strict boolean check)."""
        criterion = GoalSatisfiedCriterion()
        state = {"reflection_json": {"task_completed": 1}}
        assert criterion.should_stop(state) is False

    def test_should_stop_task_completed_0(self) -> None:
        """Test that criterion handles integer 0 as False."""
        criterion = GoalSatisfiedCriterion()
        state = {"reflection_json": {"task_completed": 0}}
        assert criterion.should_stop(state) is False
