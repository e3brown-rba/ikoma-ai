"""Tests for metrics dashboard functionality."""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from dashboard.app import app
from dashboard.metrics.api import calculate_avg_response_time, parse_metrics_files


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_metrics_file():
    """Create a temporary metrics file with sample data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        # Sample metrics data
        metrics = [
            {
                "timestamp": datetime.now().timestamp(),
                "session_id": "test_session_1",
                "step_type": "plan",
                "duration_ms": 150.5,
                "success": True,
                "tool_name": None,
            },
            {
                "timestamp": datetime.now().timestamp(),
                "session_id": "test_session_1",
                "step_type": "execute",
                "duration_ms": 250.0,
                "success": True,
                "tool_name": "search_web",
            },
            {
                "timestamp": datetime.now().timestamp(),
                "session_id": "test_session_2",
                "step_type": "plan",
                "duration_ms": 200.0,
                "success": False,
                "tool_name": None,
            },
        ]

        for metric in metrics:
            f.write(json.dumps(metric) + "\n")

        temp_file = f.name

    # Yield the file name and clean up after the test
    yield temp_file

    # Cleanup
    try:
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    except Exception:
        pass  # Ignore cleanup errors


def test_metrics_dashboard_page(client):
    """Test that metrics dashboard page loads."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "Ikoma AI - Metrics Dashboard" in response.text


def test_metrics_api_overview(client, sample_metrics_file):
    """Test metrics API overview endpoint."""
    with patch("dashboard.metrics.api.parse_metrics_files") as mock_parse:
        # Mock the metrics data
        mock_metrics = [
            {
                "timestamp": datetime.now().timestamp(),
                "session_id": "test_session_1",
                "duration_ms": 150.5,
                "success": True,
                "tool_name": "search_web",
            }
        ]
        mock_parse.return_value = mock_metrics

        response = client.get("/api/metrics/overview?days=7")
        assert response.status_code == 200

        data = response.json()
        assert "total_sessions" in data
        assert "avg_response_time" in data
        assert "success_rate" in data


def test_metrics_api_charts(client, sample_metrics_file):
    """Test metrics API charts endpoint."""
    with patch("dashboard.metrics.api.parse_metrics_files") as mock_parse:
        # Mock the metrics data
        mock_metrics = [
            {
                "timestamp": datetime.now().timestamp(),
                "session_id": "test_session_1",
                "duration_ms": 150.5,
                "success": True,
                "tool_name": "search_web",
            }
        ]
        mock_parse.return_value = mock_metrics

        response = client.get("/api/metrics/charts?days=7")
        assert response.status_code == 200

        data = response.json()
        assert "responseTime" in data
        assert "successRate" in data
        assert "toolUsage" in data
        assert "stats" in data


def test_parse_metrics_files():
    """Test parsing metrics files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        metrics_dir = Path(temp_dir)
        metrics_file = metrics_dir / "metrics.jsonl"

        # Create sample metrics file
        with open(metrics_file, "w") as f:
            metrics = [
                {
                    "timestamp": datetime.now().timestamp(),
                    "session_id": "test_session_1",
                    "duration_ms": 150.5,
                    "success": True,
                }
            ]
            for metric in metrics:
                f.write(json.dumps(metric) + "\n")

        # Test parsing with mocked path
        with patch("dashboard.metrics.api.Path") as mock_path:
            mock_path.return_value = metrics_dir

            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)

            result = parse_metrics_files(start_date, end_date)
            assert len(result) == 1
            assert result[0]["session_id"] == "test_session_1"


def test_calculate_avg_response_time():
    """Test average response time calculation."""
    metrics = [{"duration_ms": 100.0}, {"duration_ms": 200.0}, {"duration_ms": 300.0}]

    avg_time = calculate_avg_response_time(metrics)
    assert avg_time == 200.0

    # Test with empty metrics
    empty_metrics = []
    avg_time = calculate_avg_response_time(empty_metrics)
    assert avg_time == 0.0


def test_metrics_panel_endpoint(client):
    """Test metrics panel HTMX endpoint."""
    response = client.get("/metrics-panel")
    assert response.status_code == 200
    assert "Ikoma AI - Metrics Dashboard" in response.text


def test_metrics_cache_functionality():
    """Test metrics cache functionality."""
    from dashboard.metrics.api import MetricsCache

    cache = MetricsCache(ttl_seconds=1)

    # Test setting and getting
    cache.set("test_key", "test_value")
    assert cache.get("test_key") == "test_value"

    # Test cache expiration
    import time

    time.sleep(1.1)  # Wait for TTL to expire
    assert cache.get("test_key") is None


if __name__ == "__main__":
    pytest.main([__file__])
