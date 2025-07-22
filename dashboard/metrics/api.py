"""Metrics API endpoints for dashboard visualization."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/metrics")


class MetricsCache:
    """Simple in-memory cache for parsed metrics data"""

    def __init__(self, ttl_seconds: int = 300):
        self.cache: dict[str, tuple[Any, float]] = {}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now().timestamp() - timestamp < self.ttl:
                return data
        return None

    def set(self, key: str, data: Any) -> None:
        self.cache[key] = (data, datetime.now().timestamp())


cache = MetricsCache()


def parse_metrics_files(
    start_date: datetime, end_date: datetime
) -> list[dict[str, Any]]:
    """Parse JSONL metrics files within date range"""
    metrics_dir = Path("agent/logs")
    all_metrics = []

    # Look for metrics.jsonl file (our current format)
    metrics_file = metrics_dir / "metrics.jsonl"
    if metrics_file.exists():
        try:
            with open(metrics_file) as f:
                for line in f:
                    if line.strip():
                        metric = json.loads(line)
                        # Parse timestamp if it's a string
                        if isinstance(metric.get("timestamp"), str):
                            try:
                                metric["timestamp"] = datetime.fromisoformat(
                                    metric["timestamp"].replace("Z", "+00:00")
                                ).timestamp()
                            except ValueError:
                                continue
                        all_metrics.append(metric)
        except (OSError, json.JSONDecodeError):
            pass

    # Filter by date range
    filtered_metrics = []
    for metric in all_metrics:
        timestamp = metric.get("timestamp", 0)
        if isinstance(timestamp, int | float):
            metric_date = datetime.fromtimestamp(timestamp)
            if start_date <= metric_date <= end_date:
                filtered_metrics.append(metric)

    return sorted(filtered_metrics, key=lambda x: x.get("timestamp", 0))


def calculate_avg_response_time(metrics: list[dict[str, Any]]) -> float:
    """Calculate average response time from metrics"""
    response_times = []
    for metric in metrics:
        if "duration_ms" in metric:
            response_times.append(metric["duration_ms"])

    if not response_times:
        return 0.0
    return float(sum(response_times) / len(response_times))


def calculate_success_rate(metrics: list[dict[str, Any]]) -> float:
    """Calculate overall success rate from metrics"""
    if not metrics:
        return 0.0

    successful = sum(1 for m in metrics if m.get("success", False))
    return (successful / len(metrics)) * 100


def calculate_tool_usage(metrics: list[dict[str, Any]]) -> dict[str, int]:
    """Calculate tool usage frequency"""
    tool_usage: dict[str, int] = {}
    for metric in metrics:
        tool_name = metric.get("tool_name")
        if tool_name:
            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
    return tool_usage


def calculate_hourly_distribution(metrics: list[dict[str, Any]]) -> dict[str, int]:
    """Calculate hourly distribution of metrics"""
    hourly_dist: dict[str, int] = {}
    for metric in metrics:
        timestamp = metric.get("timestamp", 0)
        if isinstance(timestamp, int | float):
            hour = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:00")
            hourly_dist[hour] = hourly_dist.get(hour, 0) + 1
    return hourly_dist


@router.get("/overview")
async def get_metrics_overview(days: int = Query(7, ge=1, le=30)) -> dict[str, Any]:
    """Get metrics overview for specified number of days"""
    cache_key = f"overview_{days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    metrics = parse_metrics_files(start_date, end_date)

    # Calculate aggregated statistics
    result: dict[str, Any] = {
        "total_sessions": len(
            {m.get("session_id", "") for m in metrics if m.get("session_id")}
        ),
        "avg_response_time": calculate_avg_response_time(metrics),
        "success_rate": calculate_success_rate(metrics),
        "tool_usage": calculate_tool_usage(metrics),
        "hourly_distribution": calculate_hourly_distribution(metrics),
        "total_metrics": len(metrics),
    }

    cache.set(cache_key, result)
    return result


@router.get("/charts")
async def get_metrics_charts(days: int = Query(7, ge=1, le=30)) -> dict[str, Any]:
    """Get chart data for metrics visualization"""
    cache_key = f"charts_{days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    metrics = parse_metrics_files(start_date, end_date)

    # Prepare chart data
    from .charts import (
        prepare_success_rate_chart,
        prepare_timeseries_data,
        prepare_tool_usage_chart,
    )

    result: dict[str, Any] = {
        "responseTime": prepare_timeseries_data(metrics, "duration_ms", "avg"),
        "successRate": prepare_success_rate_chart(metrics),
        "toolUsage": prepare_tool_usage_chart(metrics),
        "stats": {
            "avgResponse": calculate_avg_response_time(metrics),
            "p95Response": calculate_p95_response_time(metrics),
            "totalSessions": len(
                {m.get("session_id", "") for m in metrics if m.get("session_id")}
            ),
            "avgIterations": calculate_avg_iterations(metrics),
        },
    }

    cache.set(cache_key, result)
    return result


def calculate_p95_response_time(metrics: list[dict[str, Any]]) -> float:
    """Calculate 95th percentile response time"""
    response_times = [m.get("duration_ms", 0) for m in metrics if "duration_ms" in m]
    if not response_times:
        return 0.0

    response_times.sort()
    index = int(len(response_times) * 0.95)
    return float(response_times[index])


def calculate_avg_iterations(metrics: list[dict[str, Any]]) -> float:
    """Calculate average iterations per session"""
    session_iterations = {}
    for metric in metrics:
        session_id = metric.get("session_id")
        if session_id:
            if session_id not in session_iterations:
                session_iterations[session_id] = 0
            session_iterations[session_id] += 1

    if not session_iterations:
        return 0.0

    return float(sum(session_iterations.values()) / len(session_iterations))
