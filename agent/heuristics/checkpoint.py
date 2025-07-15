import os
from collections.abc import Mapping
from typing import Any

from .base import TerminationCriterion


class HumanCheckpointCriterion(TerminationCriterion):
    """Criterion for human checkpoints in continuous mode.

    This criterion determines when to pause and ask the user for confirmation
    to continue, but does not actually stop the agent (should_stop always returns False).
    Instead, it provides a should_checkpoint method for the main loop to use.
    """

    def __init__(self, every: int | None = None):
        """Initialize the checkpoint criterion.

        Args:
            every: Number of iterations between checkpoints. If None, uses
                   IKOMA_CHECKPOINT_EVERY environment variable or defaults to 5.
        """
        self.every = every or int(os.getenv("IKOMA_CHECKPOINT_EVERY", 5))

    def should_stop(self, state: Mapping[str, Any]) -> bool:
        """Determine if the agent should stop based on the current state.

        This criterion never stops the agent - it only provides checkpoint functionality.
        The actual stopping is handled by other criteria.

        Args:
            state: The current agent state

        Returns:
            Always False - this criterion doesn't stop the agent
        """
        return False

    def should_checkpoint(self, state: Mapping[str, Any]) -> bool:
        """Determine if a human checkpoint should be triggered.

        Args:
            state: The current agent state

        Returns:
            True if a checkpoint should be triggered, False otherwise
        """
        current_iteration = state.get("current_iteration", 0)
        # Only disable if checkpoint_every is explicitly None
        if "checkpoint_every" in state and state["checkpoint_every"] is None:
            return False
        every = state.get("checkpoint_every", self.every)
        return bool(current_iteration % every == 0)
