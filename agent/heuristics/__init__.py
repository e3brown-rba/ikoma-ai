"""Heuristics package for termination criteria."""

from .base import TerminationCriterion
from .iteration import IterationLimitCriterion

__all__ = ["TerminationCriterion", "IterationLimitCriterion"]
