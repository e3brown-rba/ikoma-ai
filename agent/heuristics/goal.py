from collections.abc import Mapping
from typing import Any

from .base import TerminationCriterion


class GoalSatisfiedCriterion(TerminationCriterion):
    """Stop when the LLM reflection says the goal is done."""

    def should_stop(self, state: Mapping[str, Any]) -> bool:
        """Check if the reflection indicates the task is completed.

        Args:
            state: The current agent state containing reflection_json

        Returns:
            True if task_completed is True or next_action is "end", False otherwise
        """
        data = state.get("reflection_json", {}) or {}
        return bool(
            data.get("task_completed") is True or data.get("next_action") == "end"
        )
