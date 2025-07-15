"""Tests for human checkpoint functionality."""

import types
from unittest.mock import patch

import pytest

from agent.heuristics.checkpoint import HumanCheckpointCriterion
from agent.ui import prompt_user_confirm


class TestHumanCheckpointCriterion:
    """Test the HumanCheckpointCriterion class."""

    def test_should_stop_always_false(self):
        """Test that should_stop always returns False."""
        criterion = HumanCheckpointCriterion()
        state = {"current_iteration": 5}

        assert criterion.should_stop(state) is False

    @pytest.mark.parametrize(
        "every,current_iteration,expected",
        [
            (5, 0, True),  # First iteration
            (5, 5, True),  # Fifth iteration
            (5, 10, True),  # Tenth iteration
            (5, 1, False),  # Second iteration
            (5, 3, False),  # Fourth iteration
            (5, 7, False),  # Eighth iteration
            (3, 0, True),  # First iteration with every=3
            (3, 3, True),  # Third iteration with every=3
            (3, 6, True),  # Sixth iteration with every=3
            (3, 1, False),  # Second iteration with every=3
            (3, 2, False),  # Third iteration with every=3
        ],
    )
    def test_should_checkpoint_truth_table(self, every, current_iteration, expected):
        """Test should_checkpoint with various parameters."""
        criterion = HumanCheckpointCriterion(every=every)
        state = {"current_iteration": current_iteration, "checkpoint_every": every}

        assert criterion.should_checkpoint(state) == expected

    def test_should_checkpoint_disabled_when_none(self):
        """Test that checkpoints are disabled when checkpoint_every is None."""
        criterion = HumanCheckpointCriterion(every=5)
        state = {"current_iteration": 5, "checkpoint_every": None}

        assert criterion.should_checkpoint(state) is False

    def test_should_checkpoint_uses_state_config(self):
        """Test that should_checkpoint uses state configuration over constructor."""
        criterion = HumanCheckpointCriterion(every=5)
        state = {"current_iteration": 3, "checkpoint_every": 3}

        # Should checkpoint at iteration 3 with every=3, not every=5
        assert criterion.should_checkpoint(state) is True

    def test_should_checkpoint_falls_back_to_constructor(self):
        """Test that should_checkpoint falls back to constructor value when state doesn't specify."""
        criterion = HumanCheckpointCriterion(every=3)
        state = {
            "current_iteration": 3,
            "checkpoint_every": 3,
        }  # Explicitly set checkpoint_every

        assert criterion.should_checkpoint(state) is True

    def test_should_checkpoint_handles_missing_iteration(self):
        """Test that should_checkpoint handles missing current_iteration."""
        criterion = HumanCheckpointCriterion(every=5)
        state = {"checkpoint_every": 5}  # No current_iteration

        assert criterion.should_checkpoint(state) is True  # 0 % 5 == 0

    def test_should_checkpoint_constructor_fallback(self):
        """Test that should_checkpoint uses constructor value when state doesn't specify checkpoint_every."""
        criterion = HumanCheckpointCriterion(every=3)
        state = {"current_iteration": 3}  # No checkpoint_every in state

        # Should use constructor value (3) and return True for iteration 3
        assert criterion.should_checkpoint(state) is True


class TestPromptUserConfirm:
    def make_state(self, iteration=5, reflection="Test reflection", goal="Test goal"):
        return {
            "current_iteration": iteration,
            "reflection": reflection,
            "messages": [types.SimpleNamespace(content=goal)],
        }

    @patch("sys.stdin.isatty", return_value=True)
    @patch("builtins.input", return_value="y")
    def test_prompt_user_confirm_yes(self, mock_input, mock_isatty):
        state = self.make_state()
        assert prompt_user_confirm(state) is True

    @patch("sys.stdin.isatty", return_value=True)
    @patch("builtins.input", return_value="n")
    def test_prompt_user_confirm_no(self, mock_input, mock_isatty):
        state = self.make_state()
        assert prompt_user_confirm(state) is False

    @patch("sys.stdin.isatty", return_value=False)
    def test_prompt_user_confirm_non_interactive(self, mock_isatty):
        state = self.make_state()
        assert prompt_user_confirm(state) is True

    @patch("sys.stdin.isatty", return_value=True)
    @patch("builtins.input", side_effect=["maybe", ""])  # invalid, then Enter (yes)
    def test_prompt_user_confirm_invalid_then_yes(self, mock_input, mock_isatty):
        state = self.make_state()
        assert prompt_user_confirm(state) is True

    @patch("sys.stdin.isatty", return_value=True)
    @patch("builtins.input", side_effect=["maybe", "n"])  # invalid, then no
    def test_prompt_user_confirm_invalid_then_no(self, mock_input, mock_isatty):
        state = self.make_state()
        assert prompt_user_confirm(state) is False
