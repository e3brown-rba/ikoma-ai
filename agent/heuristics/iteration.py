from collections.abc import Mapping
from typing import Any

from .base import TerminationCriterion


class IterationLimitCriterion(TerminationCriterion):
    """Termination criterion based on iteration count."""

    def should_stop(self, state: Mapping[str, Any]) -> bool:
        """Check if the current iteration has reached the maximum allowed iterations.
        Args:
            state: The current agent state containing current_iteration and max_iterations
        Returns:
            True if current_iteration >= max_iterations, False otherwise
        """
        current_iteration: int = state.get("current_iteration", 0)
        max_iterations: int = state.get("max_iterations", 25)
        return current_iteration >= max_iterations
