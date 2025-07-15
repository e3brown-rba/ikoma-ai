#!/usr/bin/env python3
"""Test suite for TimeLimitCriterion."""

import time

import pytest

from agent.agent import AgentState
from agent.heuristics import TimeLimitCriterion


class TestTimeLimitCriterion:
    """Test the TimeLimitCriterion class."""

    def test_should_stop_within_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that criterion returns False when still within time limit."""
        # Mock time.time() to return a fixed timestamp
        mock_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: mock_time)

        state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=None,
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=5,
            start_time=mock_time - 300,  # 5 minutes ago (under 10 min limit)
            time_limit_secs=600,  # 10 minutes
            citations=[],
            citation_counter=1,
            reflection_json=None,
            reflection_failures=None,
        )

        criterion = TimeLimitCriterion()
        assert criterion.should_stop(state) is False

    def test_should_stop_limit_breached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that criterion returns True when time limit is exceeded."""
        # Mock time.time() to return a fixed timestamp
        mock_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: mock_time)

        state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=None,
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=5,
            start_time=mock_time - 700,  # 11+ minutes ago (over 10 min limit)
            time_limit_secs=600,  # 10 minutes
            citations=[],
            citation_counter=1,
            reflection_json=None,
            reflection_failures=None,
        )

        criterion = TimeLimitCriterion()
        assert criterion.should_stop(state) is True

    def test_should_stop_no_start_time(self) -> None:
        """Test that criterion returns False when start_time is None."""
        state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=None,
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=5,
            start_time=None,  # No start time
            time_limit_secs=600,
            citations=[],
            citation_counter=1,
            reflection_json=None,
            reflection_failures=None,
        )

        criterion = TimeLimitCriterion()
        assert criterion.should_stop(state) is False

    def test_should_stop_no_time_limit_secs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that criterion uses default time limit when time_limit_secs is None."""
        # Mock time.time() to return a fixed timestamp
        mock_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: mock_time)

        state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=None,
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=5,
            start_time=mock_time - 700,  # 11+ minutes ago (over 10 min limit)
            time_limit_secs=None,  # Should use default
            citations=[],
            citation_counter=1,
            reflection_json=None,
            reflection_failures=None,
        )

        criterion = TimeLimitCriterion()
        assert criterion.should_stop(state) is True

    def test_should_stop_custom_default_mins(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that criterion respects custom default_mins parameter."""
        # Mock time.time() to return a fixed timestamp
        mock_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: mock_time)

        state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=None,
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=5,
            start_time=mock_time - 300,  # 5 minutes ago
            time_limit_secs=None,  # Should use custom default
            citations=[],
            citation_counter=1,
            reflection_json=None,
            reflection_failures=None,
        )

        # Create criterion with 3 minute default (180 seconds)
        criterion = TimeLimitCriterion(default_mins=3)
        assert criterion.should_stop(state) is True  # 5 minutes > 3 minutes

    def test_should_stop_exact_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that criterion returns True when exactly at the time limit."""
        # Mock time.time() to return a fixed timestamp
        mock_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: mock_time)

        state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=None,
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=5,
            start_time=mock_time - 600,  # Exactly 10 minutes ago
            time_limit_secs=600,  # 10 minutes
            citations=[],
            citation_counter=1,
            reflection_json=None,
            reflection_failures=None,
        )

        criterion = TimeLimitCriterion()
        assert criterion.should_stop(state) is True

    def test_should_stop_just_under_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that criterion returns False when just under the time limit."""
        # Mock time.time() to return a fixed timestamp
        mock_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: mock_time)

        state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=None,
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=5,
            start_time=mock_time - 599,  # Just under 10 minutes ago
            time_limit_secs=600,  # 10 minutes
            citations=[],
            citation_counter=1,
            reflection_json=None,
            reflection_failures=None,
        )

        criterion = TimeLimitCriterion()
        assert criterion.should_stop(state) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
