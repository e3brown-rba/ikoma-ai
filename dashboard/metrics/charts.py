"""Chart generation utilities for metrics visualization."""

from datetime import datetime
from typing import Any


def prepare_timeseries_data(
    metrics: list[dict[str, Any]], metric_key: str, aggregation: str = "avg"
) -> dict[str, Any]:
    """Prepare metrics data for Chart.js timeseries visualization"""
    # Group by hour for better visualization
    hourly_data: dict[str, list[Any]] = {}

    for metric in metrics:
        if metric_key not in metric:
            continue

        timestamp = metric.get("timestamp", 0)
        if isinstance(timestamp, int | float):
            dt = datetime.fromtimestamp(timestamp)
            hour_key = dt.strftime("%Y-%m-%d %H:00")

            if hour_key not in hourly_data:
                hourly_data[hour_key] = []
            hourly_data[hour_key].append(metric[metric_key])

    # Aggregate data
    labels = sorted(hourly_data.keys())
    values = []

    for label in labels:
        data_points = hourly_data[label]
        if aggregation == "avg":
            values.append(sum(data_points) / len(data_points))
        elif aggregation == "sum":
            values.append(sum(data_points))
        elif aggregation == "max":
            values.append(max(data_points))
        elif aggregation == "count":
            values.append(len(data_points))

    return {
        "labels": labels,
        "datasets": [
            {
                "label": metric_key.replace("_", " ").title(),
                "data": values,
                "borderColor": "rgb(75, 192, 192)",
                "backgroundColor": "rgba(75, 192, 192, 0.2)",
                "tension": 0.1,
                "fill": False,
            }
        ],
    }


def prepare_success_rate_chart(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Prepare success rate data for Chart.js"""
    hourly_stats: dict[str, dict[str, int]] = {}

    for metric in metrics:
        if "success" not in metric:
            continue

        timestamp = metric.get("timestamp", 0)
        if isinstance(timestamp, int | float):
            dt = datetime.fromtimestamp(timestamp)
            hour_key = dt.strftime("%Y-%m-%d %H:00")

            if hour_key not in hourly_stats:
                hourly_stats[hour_key] = {"success": 0, "total": 0}

            hourly_stats[hour_key]["total"] += 1
            if metric["success"]:
                hourly_stats[hour_key]["success"] += 1

    labels = sorted(hourly_stats.keys())
    success_rates = [
        (hourly_stats[label]["success"] / hourly_stats[label]["total"] * 100)
        if hourly_stats[label]["total"] > 0
        else 0
        for label in labels
    ]

    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Success Rate (%)",
                "data": success_rates,
                "borderColor": "rgb(54, 162, 235)",
                "backgroundColor": "rgba(54, 162, 235, 0.2)",
                "tension": 0.4,
                "fill": True,
            }
        ],
    }


def prepare_tool_usage_chart(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Prepare tool usage data for Chart.js bar chart"""
    tool_usage: dict[str, int] = {}

    for metric in metrics:
        tool_name = metric.get("tool_name")
        if tool_name:
            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

    # Sort by usage count and take top 10
    sorted_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:10]

    labels = [tool[0] for tool in sorted_tools]
    values = [tool[1] for tool in sorted_tools]

    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Tool Usage Count",
                "data": values,
                "backgroundColor": [
                    "rgba(255, 99, 132, 0.8)",
                    "rgba(54, 162, 235, 0.8)",
                    "rgba(255, 206, 86, 0.8)",
                    "rgba(75, 192, 192, 0.8)",
                    "rgba(153, 102, 255, 0.8)",
                    "rgba(255, 159, 64, 0.8)",
                    "rgba(199, 199, 199, 0.8)",
                    "rgba(83, 102, 255, 0.8)",
                    "rgba(78, 252, 3, 0.8)",
                    "rgba(252, 3, 244, 0.8)",
                ],
                "borderColor": [
                    "rgba(255, 99, 132, 1)",
                    "rgba(54, 162, 235, 1)",
                    "rgba(255, 206, 86, 1)",
                    "rgba(75, 192, 192, 1)",
                    "rgba(153, 102, 255, 1)",
                    "rgba(255, 159, 64, 1)",
                    "rgba(199, 199, 199, 1)",
                    "rgba(83, 102, 255, 1)",
                    "rgba(78, 252, 3, 1)",
                    "rgba(252, 3, 244, 1)",
                ],
                "borderWidth": 1,
            }
        ],
    }


def prepare_session_duration_chart(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Prepare session duration data for Chart.js"""
    session_durations: dict[str, list[float]] = {}

    for metric in metrics:
        session_id = metric.get("session_id")
        if session_id and "duration_ms" in metric:
            if session_id not in session_durations:
                session_durations[session_id] = []
            session_durations[session_id].append(metric["duration_ms"])

    # Calculate total duration per session
    session_totals = {}
    for session_id, durations in session_durations.items():
        session_totals[session_id] = sum(durations)

    # Take top 10 longest sessions
    sorted_sessions = sorted(session_totals.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]

    labels = [f"Session {i + 1}" for i in range(len(sorted_sessions))]
    values = [session[1] for session in sorted_sessions]

    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Session Duration (ms)",
                "data": values,
                "backgroundColor": "rgba(75, 192, 192, 0.8)",
                "borderColor": "rgba(75, 192, 192, 1)",
                "borderWidth": 1,
            }
        ],
    }


def prepare_error_trend_chart(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Prepare error trend data for Chart.js"""
    hourly_errors: dict[str, dict[str, int]] = {}

    for metric in metrics:
        timestamp = metric.get("timestamp", 0)
        if isinstance(timestamp, int | float):
            dt = datetime.fromtimestamp(timestamp)
            hour_key = dt.strftime("%Y-%m-%d %H:00")

            if hour_key not in hourly_errors:
                hourly_errors[hour_key] = {"errors": 0, "total": 0}

            hourly_errors[hour_key]["total"] += 1
            if not metric.get("success", True):
                hourly_errors[hour_key]["errors"] += 1

    labels = sorted(hourly_errors.keys())
    error_rates = [
        (hourly_errors[label]["errors"] / hourly_errors[label]["total"] * 100)
        if hourly_errors[label]["total"] > 0
        else 0
        for label in labels
    ]

    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Error Rate (%)",
                "data": error_rates,
                "borderColor": "rgb(255, 99, 132)",
                "backgroundColor": "rgba(255, 99, 132, 0.2)",
                "tension": 0.4,
                "fill": True,
            }
        ],
    }
