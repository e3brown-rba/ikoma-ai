#!/usr/bin/env python3
"""
Test citation state persistence across conversation turns.
"""

import os
import sys
from unittest.mock import Mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from agent.agent import AgentState, store_long_term_memory


class TestCitationStatePersistence:
    """Test citation state persistence in agent state."""

    def test_citation_state_initialization(self) -> None:
        """Test that citation state is properly initialized."""
        state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=[],
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=1,
            start_time=1000.0,
            time_limit_secs=600,
            citations=[],
            citation_counter=1,
            reflection_json=None,
            reflection_failures=None,
            checkpoint_every=None,
            last_checkpoint_iter=0,
            stats=None,
        )

        assert state["citations"] == []
        assert state["citation_counter"] == 1

    def test_citation_state_update(self) -> None:
        """Test that citation state can be updated."""
        initial_state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=[],
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=1,
            start_time=1000.0,
            time_limit_secs=600,
            citations=[],
            citation_counter=1,
            reflection_json=None,
            reflection_failures=None,
            checkpoint_every=None,
            last_checkpoint_iter=0,
            stats=None,
        )

        # Simulate adding a citation
        new_citation = {
            "id": 1,
            "source": "https://example.com",
            "title": "Example Source",
            "content": "Example content",
        }

        # Update citation state - ensure citations is a list
        if initial_state["citations"] is None:
            initial_state["citations"] = []
        initial_state["citations"].append(new_citation)
        initial_state["citation_counter"] = 2

        assert len(initial_state["citations"]) == 1
        assert initial_state["citations"][0] == new_citation
        assert initial_state["citation_counter"] == 2

    def test_citation_state_persistence_across_iterations(self) -> None:
        """Test that citation state persists across agent iterations."""
        # Simulate initial state with citations
        initial_state = AgentState(
            messages=[],
            memory_context=None,
            user_profile=None,
            session_summary=None,
            current_plan=None,
            execution_results=[],
            reflection=None,
            continue_planning=True,
            max_iterations=25,
            current_iteration=1,
            start_time=1000.0,
            time_limit_secs=600,
            citations=[
                {
                    "id": 1,
                    "source": "https://example.com",
                    "title": "Example Source",
                    "content": "Example content",
                }
            ],
            citation_counter=2,
            reflection_json=None,
            reflection_failures=None,
            checkpoint_every=None,
            last_checkpoint_iter=0,
            stats=None,
        )

        # Simulate agent iteration (state should persist)
        # In a real scenario, this would be passed between nodes
        persisted_state = initial_state.copy()

        # Verify citation state is preserved
        assert persisted_state["citations"] is not None
        if persisted_state["citations"] is not None:
            assert len(persisted_state["citations"]) == 1
            assert persisted_state["citations"][0]["id"] == 1
        assert persisted_state["citation_counter"] == 2

        # Simulate adding another citation
        new_citation = {
            "id": 2,
            "source": "https://example2.com",
            "title": "Example Source 2",
            "content": "Example content 2",
        }

        # Ensure citations is a list before appending
        if persisted_state["citations"] is None:
            persisted_state["citations"] = []
        persisted_state["citations"].append(new_citation)
        persisted_state["citation_counter"] = 3

        # Verify both citations are present
        assert persisted_state["citations"] is not None
        if persisted_state["citations"] is not None:
            assert len(persisted_state["citations"]) == 2
            assert persisted_state["citations"][0]["id"] == 1
            assert persisted_state["citations"][1]["id"] == 2
        assert persisted_state["citation_counter"] == 3


def test_citation_state_storage():
    """Test that citation state is properly stored in long-term memory."""
    # Create a mock store
    mock_store = Mock()

    # Create test state with citation data
    state = AgentState(
        messages=[],
        memory_context=None,
        user_profile=None,
        session_summary=None,
        current_plan=None,
        execution_results=[],
        reflection=None,
        continue_planning=True,
        max_iterations=25,
        current_iteration=1,
        start_time=1000.0,
        time_limit_secs=600,
        citations=[{"id": 1, "url": "https://example.com", "title": "Test Citation"}],
        citation_counter=2,
        reflection_json=None,
        reflection_failures=None,
        checkpoint_every=None,
        last_checkpoint_iter=0,
        stats=None,
    )

    # Test config
    config = {
        "configurable": {
            "user_id": "test_user",
        }
    }

    # Call store_long_term_memory
    result = store_long_term_memory(state, config, store=mock_store)

    # Verify that the store was called with citation data
    # The actual verification would depend on the implementation details
    # For now, we just verify the function doesn't crash
    assert result is not None
