import time
from collections.abc import Mapping
from typing import Any

from agent.constants import MAX_MINS

from .base import TerminationCriterion


class TimeLimitCriterion(TerminationCriterion):
    """Stop when wall-clock time exceeds limit."""

    def __init__(self, default_mins: int = MAX_MINS):
        self.default_secs = default_mins * 60

    def should_stop(self, state: Mapping[str, Any]) -> bool:
        """Check if the current time has exceeded the time limit.

        Args:
            state: The current agent state containing start_time and time_limit_secs

        Returns:
            True if time limit exceeded, False otherwise
        """
        start: Any = state.get("start_time")
        if start is None:
            return False
        limit: int = state.get("time_limit_secs") or self.default_secs
        current_time: float = time.time()
        return bool(current_time - start >= limit)
