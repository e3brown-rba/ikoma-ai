"""Tests for agent instrumentation system."""

import time
from unittest.mock import Mock

import pytest

from agent.agent import AgentState
from agent.instrumentation import (
    AgentInstrumentation,
    ExecutionMetrics,
    SessionMetrics,
    disable_instrumentation,
    enable_instrumentation,
    get_instrumentation,
)


def create_test_agent_state() -> AgentState:
    """Create a test AgentState for testing."""
    return {
        "messages": [],
        "memory_context": None,
        "user_profile": None,
        "session_summary": None,
        "current_plan": None,
        "execution_results": None,
        "reflection": None,
        "continue_planning": False,
        "max_iterations": 10,
        "current_iteration": 0,
        "start_time": None,
        "time_limit_secs": None,
        "citations": [],
        "citation_counter": 1,
        "reflection_json": None,
        "reflection_failures": [],
        "checkpoint_every": None,
        "last_checkpoint_iter": 0,
        "stats": {},
    }


class TestExecutionMetrics:
    """Test ExecutionMetrics data class."""

    def test_execution_metrics_creation(self):
        """Test creating ExecutionMetrics instance."""
        metrics = ExecutionMetrics(
            iteration=1,
            start_time=100.0,
            end_time=110.0,
            plan_time=2.0,
            execute_time=5.0,
            reflect_time=3.0,
            total_tools_called=3,
            tools_successful=2,
            tools_failed=1,
            plan_steps=2,
            reflection_decision="continue",
            memory_operations=1,
            citations_added=1,
            errors=["test error"],
        )

        assert metrics.iteration == 1
        assert metrics.total_time == 10.0
        assert metrics.success_rate == 2 / 3
        assert len(metrics.errors) == 1

    def test_execution_metrics_success_rate_zero_tools(self):
        """Test success rate calculation with zero tools."""
        metrics = ExecutionMetrics(
            iteration=1,
            start_time=100.0,
            end_time=110.0,
            total_tools_called=0,
            tools_successful=0,
            tools_failed=0,
        )

        assert metrics.success_rate == 1.0

    def test_execution_metrics_success_rate_all_successful(self):
        """Test success rate calculation with all tools successful."""
        metrics = ExecutionMetrics(
            iteration=1,
            start_time=100.0,
            end_time=110.0,
            total_tools_called=3,
            tools_successful=3,
            tools_failed=0,
        )

        assert metrics.success_rate == 1.0


class TestSessionMetrics:
    """Test SessionMetrics data class."""

    def test_session_metrics_creation(self):
        """Test creating SessionMetrics instance."""
        metrics = SessionMetrics(
            session_id="test_session",
            start_time=100.0,
            end_time=120.0,
            total_iterations=2,
            total_execution_time=20.0,
            total_plan_time=4.0,
            total_execute_time=10.0,
            total_reflect_time=6.0,
            total_tools_called=6,
            total_tools_successful=5,
            total_tools_failed=1,
            total_citations=2,
            total_errors=1,
        )

        assert metrics.session_id == "test_session"
        assert metrics.session_duration == 20.0
        assert metrics.average_iteration_time == 10.0
        assert metrics.overall_success_rate == 5 / 6

    def test_session_metrics_running_session(self):
        """Test session duration for running session."""
        start_time = time.time() - 10.0  # 10 seconds ago
        metrics = SessionMetrics(
            session_id="test_session",
            start_time=start_time,
        )

        assert metrics.session_duration >= 9.0  # Allow for small timing variations
        assert metrics.session_duration <= 11.0

    def test_session_metrics_zero_iterations(self):
        """Test metrics with zero iterations."""
        metrics = SessionMetrics(
            session_id="test_session",
            start_time=100.0,
            total_iterations=0,
        )

        assert metrics.average_iteration_time == 0.0
        assert metrics.overall_success_rate == 1.0


class TestAgentInstrumentation:
    """Test AgentInstrumentation class."""

    def setup_method(self):
        """Set up test method."""
        self.instrumentation = AgentInstrumentation()
        self.instrumentation.enabled = True

    def test_instrumentation_initialization(self):
        """Test instrumentation initialization."""
        assert self.instrumentation.current_session is None
        assert self.instrumentation.current_iteration is None
        assert self.instrumentation.enabled is True
        assert len(self.instrumentation.hooks) == 0

    def test_register_hook(self):
        """Test registering event hooks."""
        mock_callback = Mock()
        self.instrumentation.register_hook("test_event", mock_callback)

        assert "test_event" in self.instrumentation.hooks
        assert mock_callback in self.instrumentation.hooks["test_event"]

    def test_emit_event(self):
        """Test emitting events to registered hooks."""
        mock_callback = Mock()
        self.instrumentation.register_hook("test_event", mock_callback)

        test_data = {"key": "value"}
        self.instrumentation.emit_event("test_event", test_data)

        mock_callback.assert_called_once_with("test_event", test_data)

    def test_emit_event_disabled(self):
        """Test that events are not emitted when disabled."""
        self.instrumentation.enabled = False
        mock_callback = Mock()
        self.instrumentation.register_hook("test_event", mock_callback)

        test_data = {"key": "value"}
        self.instrumentation.emit_event("test_event", test_data)

        mock_callback.assert_not_called()

    def test_emit_event_hook_error(self):
        """Test that hook errors don't crash the system."""

        def failing_callback(event, data):
            raise Exception("Test error")

        self.instrumentation.register_hook("test_event", failing_callback)

        # Should not raise an exception
        self.instrumentation.emit_event("test_event", {"key": "value"})

    def test_start_session(self):
        """Test starting a new session."""
        self.instrumentation.start_session("test_session", "test goal")

        assert self.instrumentation.current_session is not None
        assert self.instrumentation.current_session.session_id == "test_session"
        assert self.instrumentation.current_session.start_time > 0

    def test_end_session(self):
        """Test ending a session."""
        self.instrumentation.start_session("test_session", "test goal")

        # Start and end an iteration properly
        state = create_test_agent_state()
        self.instrumentation.start_iteration(1, state)

        # Record some metrics
        self.instrumentation.record_plan_start()
        time.sleep(0.01)
        self.instrumentation.record_plan_end(2, [{"step": 1}, {"step": 2}])

        self.instrumentation.record_execute_start()
        time.sleep(0.01)
        self.instrumentation.record_execute_end([{"success": True}, {"success": False}])

        self.instrumentation.record_reflect_start()
        time.sleep(0.01)
        self.instrumentation.record_reflect_end("Test reflection", "continue")

        # End the iteration properly
        self.instrumentation.end_iteration(state)

        final_state = create_test_agent_state()
        session_metrics = self.instrumentation.end_session(final_state)

        assert session_metrics.session_id == "test_session"
        assert session_metrics.end_time is not None
        assert session_metrics.total_iterations == 1

    def test_start_iteration(self):
        """Test starting a new iteration."""
        self.instrumentation.start_session("test_session", "test goal")

        state = create_test_agent_state()
        self.instrumentation.start_iteration(1, state)

        assert self.instrumentation.current_iteration is not None
        assert self.instrumentation.current_iteration.iteration == 1
        assert self.instrumentation.current_iteration.start_time > 0

    def test_end_iteration(self):
        """Test ending an iteration."""
        self.instrumentation.start_session("test_session", "test goal")
        self.instrumentation.start_iteration(1, create_test_agent_state())

        state = create_test_agent_state()
        iteration_metrics = self.instrumentation.end_iteration(state)

        assert iteration_metrics.iteration == 1
        assert iteration_metrics.end_time > 0
        assert self.instrumentation.current_session is not None
        assert self.instrumentation.current_session.iterations == [iteration_metrics]

    def test_record_plan_start(self):
        """Test recording plan start."""
        self.instrumentation.start_session("test_session", "test goal")
        self.instrumentation.start_iteration(1, create_test_agent_state())

        self.instrumentation.record_plan_start()

        assert self.instrumentation.current_iteration is not None
        assert self.instrumentation.current_iteration.plan_start_time > 0

    def test_record_plan_end(self):
        """Test recording plan end."""
        self.instrumentation.start_session("test_session", "test goal")
        self.instrumentation.start_iteration(1, create_test_agent_state())
        self.instrumentation.record_plan_start()

        time.sleep(0.01)  # Small delay to ensure time difference
        plan = [{"step": 1, "tool_name": "test_tool"}]
        self.instrumentation.record_plan_end(1, plan)

        assert self.instrumentation.current_iteration is not None
        assert self.instrumentation.current_iteration.plan_time > 0
        assert self.instrumentation.current_iteration.plan_steps == 1

    def test_record_execute_start(self):
        """Test recording execute start."""
        self.instrumentation.start_session("test_session", "test goal")
        self.instrumentation.start_iteration(1, create_test_agent_state())

        self.instrumentation.record_execute_start()

        assert self.instrumentation.current_iteration is not None
        assert self.instrumentation.current_iteration.execute_start_time > 0

    def test_record_execute_end(self):
        """Test recording execute end."""
        self.instrumentation.start_session("test_session", "test goal")
        self.instrumentation.start_iteration(1, create_test_agent_state())
        self.instrumentation.record_execute_start()

        time.sleep(0.01)  # Small delay to ensure time difference
        results = [
            {"step": 1, "success": True, "result": "success"},
            {"step": 2, "success": False, "result": "error"},
        ]
        self.instrumentation.record_execute_end(results)

        assert self.instrumentation.current_iteration is not None
        assert self.instrumentation.current_iteration.execute_time > 0
        assert self.instrumentation.current_iteration.total_tools_called == 2
        assert self.instrumentation.current_iteration.tools_successful == 1
        assert self.instrumentation.current_iteration.tools_failed == 1

    def test_record_reflect_start(self):
        """Test recording reflect start."""
        self.instrumentation.start_session("test_session", "test goal")
        self.instrumentation.start_iteration(1, create_test_agent_state())

        self.instrumentation.record_reflect_start()

        assert self.instrumentation.current_iteration is not None
        assert self.instrumentation.current_iteration.reflect_start_time > 0

    def test_record_reflect_end(self):
        """Test recording reflect end."""
        self.instrumentation.start_session("test_session", "test goal")
        self.instrumentation.start_iteration(1, create_test_agent_state())
        self.instrumentation.record_reflect_start()

        time.sleep(0.01)  # Small delay to ensure time difference
        self.instrumentation.record_reflect_end("Test reflection", "continue")

        assert self.instrumentation.current_iteration is not None
        assert self.instrumentation.current_iteration.reflect_time > 0
        assert self.instrumentation.current_iteration.reflection_decision == "continue"

    def test_record_tool_call(self):
        """Test recording tool calls."""
        self.instrumentation.start_session("test_session", "test goal")
        self.instrumentation.start_iteration(1, create_test_agent_state())

        # Record successful tool call
        self.instrumentation.record_tool_call(
            "test_tool", {"arg": "value"}, True, "success"
        )
        assert self.instrumentation.current_iteration is not None
        assert self.instrumentation.current_iteration.total_tools_called == 1
        assert self.instrumentation.current_iteration.tools_successful == 1
        assert self.instrumentation.current_iteration.tools_failed == 0

        # Record failed tool call
        self.instrumentation.record_tool_call(
            "test_tool", {"arg": "value"}, False, "error"
        )
        assert self.instrumentation.current_iteration is not None
        assert self.instrumentation.current_iteration.total_tools_called == 2
        assert self.instrumentation.current_iteration.tools_successful == 1
        assert self.instrumentation.current_iteration.tools_failed == 1

    def test_record_error(self):
        """Test recording errors."""
        self.instrumentation.start_session("test_session", "test goal")
        self.instrumentation.start_iteration(1, create_test_agent_state())

        self.instrumentation.record_error("Test error", {"context": "test"})

        assert self.instrumentation.current_iteration is not None
        assert len(self.instrumentation.current_iteration.errors) == 1
        assert "Test error" in self.instrumentation.current_iteration.errors[0]

    def test_record_citation(self):
        """Test recording citations."""
        self.instrumentation.start_session("test_session", "test goal")
        self.instrumentation.start_iteration(1, create_test_agent_state())

        citation = {"id": 1, "title": "Test Citation", "url": "http://example.com"}
        self.instrumentation.record_citation(citation)

        assert self.instrumentation.current_iteration is not None
        assert self.instrumentation.current_iteration.citations_added == 1

    def test_record_memory_operation(self):
        """Test recording memory operations."""
        self.instrumentation.start_session("test_session", "test goal")
        self.instrumentation.start_iteration(1, create_test_agent_state())

        self.instrumentation.record_memory_operation("store", {"key": "value"})

        assert self.instrumentation.current_iteration is not None
        assert self.instrumentation.current_iteration.memory_operations == 1


class TestGlobalInstrumentation:
    """Test global instrumentation functions."""

    def test_get_instrumentation(self):
        """Test getting the global instrumentation instance."""
        instrumentation = get_instrumentation()
        assert isinstance(instrumentation, AgentInstrumentation)

    def test_enable_disable_instrumentation(self):
        """Test enabling and disabling instrumentation."""
        instrumentation = get_instrumentation()

        # Test enable
        enable_instrumentation()
        assert instrumentation.enabled is True

        # Test disable
        disable_instrumentation()
        assert instrumentation.enabled is False

        # Re-enable for other tests
        enable_instrumentation()

    def test_instrumentation_integration(self):
        """Test that instrumentation integrates with agent state."""
        instrumentation = get_instrumentation()
        instrumentation.enabled = True

        # Simulate a complete agent session
        instrumentation.start_session("test_session", "test goal")

        state = create_test_agent_state()
        instrumentation.start_iteration(1, state)

        # Record some metrics
        instrumentation.record_plan_start()
        time.sleep(0.01)
        instrumentation.record_plan_end(2, [{"step": 1}, {"step": 2}])

        instrumentation.record_execute_start()
        time.sleep(0.01)
        instrumentation.record_execute_end([{"success": True}, {"success": False}])

        instrumentation.record_reflect_start()
        time.sleep(0.01)
        instrumentation.record_reflect_end("Test reflection", "continue")

        # End the iteration properly
        instrumentation.end_iteration(state)

        final_state = create_test_agent_state()
        session_metrics = instrumentation.end_session(final_state)

        # Verify metrics were collected
        assert session_metrics.total_iterations == 1
        assert session_metrics.total_tools_called == 2
        assert session_metrics.total_tools_successful == 1
        assert session_metrics.total_tools_failed == 1
        assert session_metrics.total_execution_time > 0
        assert session_metrics.total_plan_time > 0
        assert session_metrics.total_execute_time > 0
        assert session_metrics.total_reflect_time > 0


if __name__ == "__main__":
    pytest.main([__file__])
