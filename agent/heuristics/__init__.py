"""Heuristics package for termination criteria."""

from .base import TerminationCriterion
from .checkpoint import HumanCheckpointCriterion
from .goal import GoalSatisfiedCriterion
from .iteration import IterationLimitCriterion
from .time import TimeLimitCriterion

# Default criteria list for unified termination checking
DEFAULT_CRITERIA: list[TerminationCriterion] = [
    IterationLimitCriterion(),
    TimeLimitCriterion(),
    GoalSatisfiedCriterion(),
]

# Export checkpoint criterion separately so existing stop-logic remains unchanged
CHECKPOINT_CRITERION = HumanCheckpointCriterion()

__all__ = [
    "TerminationCriterion",
    "HumanCheckpointCriterion",
    "IterationLimitCriterion",
    "TimeLimitCriterion",
    "GoalSatisfiedCriterion",
    "DEFAULT_CRITERIA",
    "CHECKPOINT_CRITERION",
]
