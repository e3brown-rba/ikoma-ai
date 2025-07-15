"""Heuristics package for termination criteria."""

from .base import TerminationCriterion
from .goal import GoalSatisfiedCriterion
from .iteration import IterationLimitCriterion
from .time import TimeLimitCriterion

# Default criteria list for unified termination checking
DEFAULT_CRITERIA: list[TerminationCriterion] = [
    IterationLimitCriterion(),
    TimeLimitCriterion(),
    GoalSatisfiedCriterion(),
]

__all__ = [
    "TerminationCriterion",
    "IterationLimitCriterion",
    "TimeLimitCriterion",
    "GoalSatisfiedCriterion",
    "DEFAULT_CRITERIA",
]
