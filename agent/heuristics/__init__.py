"""Heuristics package for termination criteria."""

from .base import TerminationCriterion
from .iteration import IterationLimitCriterion
from .time import TimeLimitCriterion

__all__ = ["TerminationCriterion", "IterationLimitCriterion", "TimeLimitCriterion"]
