from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class TerminationCriterion(ABC):
    """Abstract base class for termination criteria."""

    @abstractmethod
    def should_stop(self, state: Mapping[str, Any]) -> bool:
        """Determine if the agent should stop based on the current state.
        Args:
            state: The current agent state
        Returns:
            True if the agent should stop, False otherwise
        """
        pass
