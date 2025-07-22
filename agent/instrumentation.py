"""Instrumentation hooks for agent loop monitoring and metrics collection."""

import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent.agent import AgentState


@dataclass
class ExecutionMetrics:
    """Metrics for a single execution cycle."""

    iteration: int
    start_time: float
    end_time: float
    plan_time: float = 0.0
    execute_time: float = 0.0
    reflect_time: float = 0.0
    total_tools_called: int = 0
    tools_successful: int = 0
    tools_failed: int = 0
    plan_steps: int = 0
    reflection_decision: str = ""
    memory_operations: int = 0
    citations_added: int = 0
    errors: list[str] = field(default_factory=list)
    # Add missing timing fields
    plan_start_time: float = 0.0
    execute_start_time: float = 0.0
    reflect_start_time: float = 0.0

    @property
    def total_time(self) -> float:
        """Total execution time for this iteration."""
        return self.end_time - self.start_time

    @property
    def success_rate(self) -> float:
        """Tool execution success rate."""
        if self.total_tools_called == 0:
            return 1.0
        return self.tools_successful / self.total_tools_called


@dataclass
class SessionMetrics:
    """Aggregated metrics for an entire agent session."""

    session_id: str
    start_time: float
    end_time: float | None = None
    total_iterations: int = 0
    total_execution_time: float = 0.0
    total_plan_time: float = 0.0
    total_execute_time: float = 0.0
    total_reflect_time: float = 0.0
    total_tools_called: int = 0
    total_tools_successful: int = 0
    total_tools_failed: int = 0
    total_citations: int = 0
    total_errors: int = 0
    iterations: list[ExecutionMetrics] = field(default_factory=list)

    @property
    def session_duration(self) -> float:
        """Total session duration."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def average_iteration_time(self) -> float:
        """Average time per iteration."""
        if self.total_iterations == 0:
            return 0.0
        return self.total_execution_time / self.total_iterations

    @property
    def overall_success_rate(self) -> float:
        """Overall tool execution success rate."""
        if self.total_tools_called == 0:
            return 1.0
        return self.total_tools_successful / self.total_tools_called


class AgentInstrumentation:
    """Instrumentation system for agent loop monitoring."""

    def __init__(self) -> None:
        self.current_session: SessionMetrics | None = None
        self.current_iteration: ExecutionMetrics | None = None
        self.hooks: dict[str, list[Callable]] = defaultdict(list)
        self.enabled = True

    def register_hook(self, event: str, callback: Callable) -> None:
        """Register a callback for a specific event."""
        self.hooks[event].append(callback)

    def emit_event(self, event: str, data: dict[str, Any]) -> None:
        """Emit an event to all registered hooks."""
        if not self.enabled:
            return

        for callback in self.hooks[event]:
            try:
                callback(event, data)
            except Exception as e:
                print(f"Warning: Hook error in {event}: {e}")

    def start_session(self, session_id: str, goal: str) -> None:
        """Start a new agent session."""
        self.current_session = SessionMetrics(
            session_id=session_id, start_time=time.time()
        )

        self.emit_event(
            "session_start",
            {
                "session_id": session_id,
                "goal": goal,
                "start_time": self.current_session.start_time,
            },
        )

    def end_session(self, final_state: "AgentState") -> SessionMetrics:
        """End the current session and return metrics."""
        if self.current_session is None:
            return SessionMetrics(session_id="unknown", start_time=time.time())

        self.current_session.end_time = time.time()

        # Aggregate metrics from iterations
        for iteration in self.current_session.iterations:
            self.current_session.total_execution_time += iteration.total_time
            self.current_session.total_plan_time += iteration.plan_time
            self.current_session.total_execute_time += iteration.execute_time
            self.current_session.total_reflect_time += iteration.reflect_time
            self.current_session.total_tools_called += iteration.total_tools_called
            self.current_session.total_tools_successful += iteration.tools_successful
            self.current_session.total_tools_failed += iteration.tools_failed
            self.current_session.total_citations += iteration.citations_added
            self.current_session.total_errors += len(iteration.errors)

        self.current_session.total_iterations = len(self.current_session.iterations)

        self.emit_event(
            "session_end",
            {
                "session_id": self.current_session.session_id,
                "metrics": self.current_session,
                "final_state": final_state,
            },
        )

        return self.current_session

    def start_iteration(self, iteration: int, state: "AgentState") -> None:
        """Start a new iteration."""
        self.current_iteration = ExecutionMetrics(
            iteration=iteration,
            start_time=time.time(),
            end_time=time.time(),  # Will be updated when iteration ends
        )

        self.emit_event("iteration_start", {"iteration": iteration, "state": state})

    def end_iteration(self, state: "AgentState") -> ExecutionMetrics:
        """End the current iteration and return metrics."""
        if self.current_iteration is None:
            return ExecutionMetrics(
                iteration=0, start_time=time.time(), end_time=time.time()
            )

        self.current_iteration.end_time = time.time()

        # Update session metrics
        if self.current_session is not None:
            self.current_session.iterations.append(self.current_iteration)

        self.emit_event(
            "iteration_end",
            {
                "iteration": self.current_iteration.iteration,
                "metrics": self.current_iteration,
                "state": state,
            },
        )

        # Store the iteration metrics before clearing current_iteration
        iteration_metrics = self.current_iteration
        self.current_iteration = None

        return iteration_metrics

    def record_plan_start(self) -> None:
        """Record the start of planning phase."""
        if self.current_iteration is None:
            return

        self.current_iteration.plan_start_time = time.time()
        self.emit_event("plan_start", {"iteration": self.current_iteration.iteration})

    def record_plan_end(self, plan_steps: int, plan: list[dict[str, Any]]) -> None:
        """Record the end of planning phase."""
        if self.current_iteration is None:
            return

        self.current_iteration.plan_time = (
            time.time() - self.current_iteration.plan_start_time
        )
        self.current_iteration.plan_steps = plan_steps

        self.emit_event(
            "plan_end",
            {
                "iteration": self.current_iteration.iteration,
                "plan_steps": plan_steps,
                "plan": plan,
                "plan_time": self.current_iteration.plan_time,
            },
        )

    def record_execute_start(self) -> None:
        """Record the start of execution phase."""
        if self.current_iteration is None:
            return

        self.current_iteration.execute_start_time = time.time()
        self.emit_event(
            "execute_start", {"iteration": self.current_iteration.iteration}
        )

    def record_execute_end(self, results: list[dict[str, Any]]) -> None:
        """Record the end of execution phase."""
        if self.current_iteration is None:
            return

        self.current_iteration.execute_time = (
            time.time() - self.current_iteration.execute_start_time
        )

        # Count tool results
        for result in results:
            self.current_iteration.total_tools_called += 1
            if result.get("success", False):
                self.current_iteration.tools_successful += 1
            else:
                self.current_iteration.tools_failed += 1

        self.emit_event(
            "execute_end",
            {
                "iteration": self.current_iteration.iteration,
                "results": results,
                "execute_time": self.current_iteration.execute_time,
                "tools_called": self.current_iteration.total_tools_called,
            },
        )

    def record_reflect_start(self) -> None:
        """Record the start of reflection phase."""
        if self.current_iteration is None:
            return

        self.current_iteration.reflect_start_time = time.time()
        self.emit_event(
            "reflect_start", {"iteration": self.current_iteration.iteration}
        )

    def record_reflect_end(self, reflection: str, decision: str) -> None:
        """Record the end of reflection phase."""
        if self.current_iteration is None:
            return

        self.current_iteration.reflect_time = (
            time.time() - self.current_iteration.reflect_start_time
        )
        self.current_iteration.reflection_decision = decision

        self.emit_event(
            "reflect_end",
            {
                "iteration": self.current_iteration.iteration,
                "reflection": reflection,
                "decision": decision,
                "reflect_time": self.current_iteration.reflect_time,
            },
        )

    def record_tool_call(
        self, tool_name: str, args: dict[str, Any], success: bool, result: Any
    ) -> None:
        """Record a tool call."""
        if self.current_iteration is None:
            return

        self.current_iteration.total_tools_called += 1
        if success:
            self.current_iteration.tools_successful += 1
        else:
            self.current_iteration.tools_failed += 1

        self.emit_event(
            "tool_call",
            {
                "iteration": self.current_iteration.iteration,
                "tool_name": tool_name,
                "args": args,
                "success": success,
                "result": result,
            },
        )

    def record_error(self, error: str, context: dict[str, Any]) -> None:
        """Record an error."""
        if self.current_iteration is None:
            return

        self.current_iteration.errors.append(error)

        self.emit_event(
            "error",
            {
                "iteration": self.current_iteration.iteration,
                "error": error,
                "context": context,
            },
        )

    def record_citation(self, citation: dict[str, Any]) -> None:
        """Record a citation addition."""
        if self.current_iteration is None:
            return

        self.current_iteration.citations_added += 1

        self.emit_event(
            "citation",
            {"iteration": self.current_iteration.iteration, "citation": citation},
        )

    def record_memory_operation(self, operation: str, details: dict[str, Any]) -> None:
        """Record a memory operation."""
        if self.current_iteration is None:
            return

        self.current_iteration.memory_operations += 1

        self.emit_event(
            "memory_operation",
            {
                "iteration": self.current_iteration.iteration,
                "operation": operation,
                "details": details,
            },
        )


# Global instrumentation instance
instrumentation = AgentInstrumentation()


def get_instrumentation() -> AgentInstrumentation:
    """Get the global instrumentation instance."""
    return instrumentation


def enable_instrumentation() -> None:
    """Enable instrumentation."""
    instrumentation.enabled = True


def disable_instrumentation() -> None:
    """Disable instrumentation."""
    instrumentation.enabled = False


# Convenience functions for common instrumentation patterns
def instrument_session(session_id: str, goal: str) -> Callable:
    """Decorator to instrument a complete agent session."""

    def decorator(func: Callable) -> Callable:
        def wrapper(initial_state: "AgentState") -> Any:
            instrumentation.start_session(session_id, goal)
            try:
                result = func(initial_state)
                return instrumentation.end_session(result)
            except Exception as e:
                instrumentation.record_error(str(e), {"session_id": session_id})
                raise

        return wrapper

    return decorator


def instrument_iteration(iteration: int) -> Callable:
    """Decorator to instrument a single iteration."""

    def decorator(func: Callable) -> Callable:
        def wrapper(state: "AgentState") -> Any:
            instrumentation.start_iteration(iteration, state)
            try:
                result = func(state)
                return instrumentation.end_iteration(result)
            except Exception as e:
                instrumentation.record_error(str(e), {"iteration": iteration})
                raise

        return wrapper

    return decorator
