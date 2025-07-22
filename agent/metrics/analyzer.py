"""Metrics analyzer for spike detection and performance analysis."""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import MetricsSummary, SessionMetric, StepMetric


class MetricsAnalyzer:
    """Analyze metrics for performance regressions and safety incidents."""

    def __init__(self, metrics_file: Path):
        self.metrics_file = metrics_file
        self.regression_threshold = 0.20  # 20% performance degradation
        self.analysis_window_days = 7

    def analyze_recent_performance(self) -> MetricsSummary:
        """Analyze recent metrics and generate summary."""
        metrics = self._load_metrics()

        if not metrics:
            return MetricsSummary(
                total_sessions=0,
                total_iterations=0,
                average_session_duration_ms=0.0,
                average_iteration_duration_ms=0.0,
                overall_success_rate=0.0,
                most_used_tools=[],
                safety_incidents=0,
            )

        # Parse session metrics
        sessions = [m for m in metrics if m.get("session_id")]
        steps = [m for m in metrics if m.get("step_type")]

        # Calculate summary statistics
        total_sessions = len(sessions)
        total_iterations = sum(s.get("iterations", 0) for s in sessions)

        # Calculate average durations
        session_durations = [s.get("total_duration_ms", 0) for s in sessions]
        avg_session_duration = sum(session_durations) / max(1, len(session_durations))

        iteration_durations = []
        for step in steps:
            if step.get("step_type") in ["plan", "execute", "reflect"]:
                iteration_durations.append(step.get("duration_ms", 0))
        avg_iteration_duration = sum(iteration_durations) / max(
            1, len(iteration_durations)
        )

        # Calculate success rates
        successful_steps = sum(1 for s in steps if s.get("success", False))
        total_steps = len(steps)
        overall_success_rate = successful_steps / max(1, total_steps)

        # Count tool usage
        tool_usage: dict[str, int] = defaultdict(int)
        for step in steps:
            if step.get("tool_name"):
                tool_usage[step["tool_name"]] += 1

        most_used_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]

        # Count safety incidents
        safety_incidents = sum(
            1 for s in steps if s.get("step_type") == "safety_incident"
        )

        # Check for performance regression
        regression = self._detect_performance_regression(metrics)

        return MetricsSummary(
            total_sessions=total_sessions,
            total_iterations=total_iterations,
            average_session_duration_ms=avg_session_duration,
            average_iteration_duration_ms=avg_iteration_duration,
            overall_success_rate=overall_success_rate,
            most_used_tools=most_used_tools,
            safety_incidents=safety_incidents,
            performance_regression=regression,
        )

    def _detect_performance_regression(
        self, metrics: list[dict[str, Any]]
    ) -> float | None:
        """Detect performance regression using rolling average comparison."""
        if not metrics:
            return None

        # Group metrics by date (day)
        daily_metrics = defaultdict(list)
        for metric in metrics:
            if "timestamp" in metric:
                try:
                    timestamp = datetime.fromisoformat(
                        metric["timestamp"].replace("Z", "+00:00")
                    )
                    date_key = timestamp.date()
                    daily_metrics[date_key].append(metric)
                except (ValueError, TypeError):
                    continue

        if len(daily_metrics) < 2:
            return None

        # Calculate recent vs historical averages
        sorted_dates = sorted(daily_metrics.keys())
        cutoff_date = sorted_dates[-1] - timedelta(days=self.analysis_window_days)

        recent_metrics = []
        historical_metrics = []

        for date, day_metrics in daily_metrics.items():
            if date > cutoff_date:
                recent_metrics.extend(day_metrics)
            else:
                historical_metrics.extend(day_metrics)

        if not recent_metrics or not historical_metrics:
            return None

        # Calculate average step duration
        def get_avg_duration(metrics_list: list[dict[str, Any]]) -> float:
            durations = [
                float(m.get("duration_ms", 0)) for m in metrics_list if m.get("duration_ms")
            ]
            return sum(durations) / max(1, len(durations))

        recent_avg = get_avg_duration(recent_metrics)
        historical_avg = get_avg_duration(historical_metrics)

        if historical_avg == 0:
            return None

        # Calculate percentage change
        change = (recent_avg - historical_avg) / historical_avg

        # Return regression percentage if it exceeds threshold
        if change > self.regression_threshold:
            return change * 100

        return None

    def _load_metrics(self) -> list[dict[str, Any]]:
        """Load metrics from JSONL file."""
        if not self.metrics_file.exists():
            return []

        metrics = []
        try:
            with open(self.metrics_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        metrics.append(json.loads(line))
        except (json.JSONDecodeError, IOError):
            pass

        return metrics

    def check_safety_incidents(self) -> list[dict[str, Any]]:
        """Check for safety incidents in recent metrics."""
        metrics = self._load_metrics()
        incidents = []

        for metric in metrics:
            if metric.get("step_type") == "safety_incident":
                incidents.append(
                    {
                        "timestamp": metric.get("timestamp"),
                        "error": metric.get("error"),
                        "metadata": metric.get("metadata", {}),
                    }
                )

        return incidents

    def generate_ci_report(self) -> str:
        """Generate a CI-friendly report."""
        summary = self.analyze_recent_performance()
        incidents = self.check_safety_incidents()

        report_lines = [
            "## Performance Metrics Report",
            "",
            f"**Sessions**: {summary.total_sessions}",
            f"**Iterations**: {summary.total_iterations}",
            f"**Avg Session Duration**: {summary.average_session_duration_ms:.1f}ms",
            f"**Avg Iteration Duration**: {summary.average_iteration_duration_ms:.1f}ms",
            f"**Success Rate**: {summary.overall_success_rate:.1%}",
            f"**Safety Incidents**: {summary.safety_incidents}",
            "",
        ]

        if summary.most_used_tools:
            report_lines.append("**Most Used Tools**:")
            for tool, count in summary.most_used_tools[:5]:
                report_lines.append(f"  - {tool}: {count} calls")
            report_lines.append("")

        if summary.performance_regression:
            report_lines.append(
                f"⚠️ **PERFORMANCE REGRESSION DETECTED**: {summary.performance_regression:.1f}% slower"
            )
            report_lines.append("")

        if incidents:
            report_lines.append("**Safety Incidents**:")
            for incident in incidents[:5]:  # Show last 5 incidents
                report_lines.append(f"  - {incident['timestamp']}: {incident['error']}")
            report_lines.append("")

        return "\n".join(report_lines)
