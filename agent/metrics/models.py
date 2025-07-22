"""Pydantic models for metrics data collection."""

from datetime import datetime

from pydantic import BaseModel


class StepMetric(BaseModel):
    """Metrics for a single execution step."""

    timestamp: datetime
    thread_id: str
    step_type: str  # "plan", "execute", "reflect"
    tool_name: str | None = None
    duration_ms: float
    success: bool
    error: str | None = None
    metadata: dict = {}


class SessionMetric(BaseModel):
    """Aggregated metrics for an entire agent session."""

    timestamp: datetime
    thread_id: str
    session_id: str
    total_duration_ms: float
    iterations: int
    tools_used: list[str]
    success_rate: float
    safety_incidents: int = 0
    plan_time_ms: float = 0.0
    execute_time_ms: float = 0.0
    reflect_time_ms: float = 0.0
    total_tool_calls: int = 0
    successful_tool_calls: int = 0
    failed_tool_calls: int = 0


class MetricsSummary(BaseModel):
    """Summary statistics for CI reporting."""

    total_sessions: int
    total_iterations: int
    average_session_duration_ms: float
    average_iteration_duration_ms: float
    overall_success_rate: float
    most_used_tools: list[tuple[str, int]]
    safety_incidents: int
    performance_regression: float | None = None  # Percentage change
