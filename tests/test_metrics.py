"""Tests for the metrics collection system."""

import json
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agent.metrics import metrics_collector
from agent.metrics.analyzer import MetricsAnalyzer
from agent.metrics.collector import MetricsCollector
from agent.metrics.models import MetricsSummary, SessionMetric, StepMetric


class TestMetricsModels:
    """Test the Pydantic models for metrics."""

    def test_step_metric_creation(self):
        """Test creating a StepMetric."""
        metric = StepMetric(
            timestamp=datetime(2023, 1, 1),
            thread_id="test_thread",
            step_type="plan",
            tool_name="test_tool",
            duration_ms=100.5,
            success=True,
            error=None,
            metadata={"test": "value"},
        )

        assert metric.step_type == "plan"
        assert metric.tool_name == "test_tool"
        assert metric.duration_ms == 100.5
        assert metric.success is True
        assert metric.error is None
        assert metric.metadata["test"] == "value"

    def test_session_metric_creation(self):
        """Test creating a SessionMetric."""
        metric = SessionMetric(
            timestamp=datetime(2023, 1, 1),
            thread_id="test_thread",
            session_id="test_session",
            total_duration_ms=500.0,
            iterations=3,
            tools_used=["tool1", "tool2"],
            success_rate=0.8,
            safety_incidents=0,
        )

        assert metric.session_id == "test_session"
        assert metric.total_duration_ms == 500.0
        assert metric.iterations == 3
        assert len(metric.tools_used) == 2
        assert metric.success_rate == 0.8
        assert metric.safety_incidents == 0


class TestMetricsCollector:
    """Test the metrics collector functionality."""

    def setup_method(self):
        """Reset metrics collector before each test."""
        # Reset the singleton
        MetricsCollector._instance = None
        # Clear any existing session metrics
        if hasattr(metrics_collector, "_session_metrics"):
            metrics_collector._session_metrics.clear()

    def test_singleton_pattern(self):
        """Test that MetricsCollector is a singleton."""
        collector1 = MetricsCollector()
        collector2 = MetricsCollector()
        assert collector1 is collector2

    @patch.dict("os.environ", {"IKOMA_METRICS_ENABLED": "true"})
    def test_emit_step(self):
        """Test emitting a step metric."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            metrics_file = Path(f.name)

        try:
            # Reset the singleton and reinitialize with new environment
            MetricsCollector._instance = None
            collector = MetricsCollector()

            # Mock the output path
            with patch.object(collector, "output_path", metrics_file):
                collector.emit_step(
                    step_type="test",
                    duration_ms=100.0,
                    success=True,
                    tool_name="test_tool",
                )

            # Check that the metric was written
            assert metrics_file.exists()
            with open(metrics_file, "r") as f:
                lines = f.readlines()
                assert len(lines) == 1

                metric = json.loads(lines[0])
                assert metric["step_type"] == "test"
                assert metric["duration_ms"] == 100.0
                assert metric["success"] is True
                assert metric["tool_name"] == "test_tool"
        finally:
            metrics_file.unlink(missing_ok=True)

    @patch.dict("os.environ", {"IKOMA_METRICS_ENABLED": "true"})
    def test_session_tracking(self):
        """Test session start/end tracking."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            metrics_file = Path(f.name)

        try:
            # Reset the singleton and reinitialize with new environment
            MetricsCollector._instance = None
            collector = MetricsCollector()

            # Mock the output path
            with patch.object(collector, "output_path", metrics_file):
                session_id = "test_session"

                # Start session
                collector.start_session(session_id)
                assert session_id in collector._session_metrics

                # Update session
                collector.update_session(
                    session_id, iterations=5, total_duration_ms=1000.0
                )
                session = collector._session_metrics[session_id]
                assert session.iterations == 5
                assert session.total_duration_ms == 1000.0

                # End session
                final_metrics = collector.end_session(session_id)
                assert final_metrics is not None
                assert final_metrics.session_id == session_id
                assert session_id not in collector._session_metrics

                # Check that session metric was written
                with open(metrics_file, "r") as f:
                    lines = f.readlines()
                    assert len(lines) == 1

                    metric = json.loads(lines[0])
                    assert metric["session_id"] == session_id
        finally:
            metrics_file.unlink(missing_ok=True)

    @patch.dict("os.environ", {"IKOMA_METRICS_ENABLED": "false"})
    def test_disabled_metrics(self):
        """Test that metrics are not collected when disabled."""
        metrics_collector.emit_step("test", 100.0, True)
        metrics_collector.start_session("test_session")
        metrics_collector.end_session("test_session")

        # Should not create any files or collect data
        assert not metrics_collector.output_path.exists()


class TestMetricsAnalyzer:
    """Test the metrics analyzer functionality."""

    def test_analyze_empty_metrics(self):
        """Test analyzing empty metrics file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            metrics_file = Path(f.name)

        try:
            analyzer = MetricsAnalyzer(metrics_file)
            summary = analyzer.analyze_recent_performance()

            assert summary.total_sessions == 0
            assert summary.total_iterations == 0
            assert summary.average_session_duration_ms == 0.0
            assert summary.overall_success_rate == 0.0
            assert summary.safety_incidents == 0
        finally:
            metrics_file.unlink(missing_ok=True)

    def test_analyze_with_metrics(self):
        """Test analyzing metrics with data."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            metrics_file = Path(f.name)

            # Write some test metrics
            test_metrics = [
                {
                    "timestamp": "2023-01-01T00:00:00",
                    "session_id": "test_session",
                    "total_duration_ms": 1000.0,
                    "iterations": 3,
                    "tools_used": ["tool1", "tool2"],
                    "success_rate": 0.8,
                    "safety_incidents": 0,
                },
                {
                    "timestamp": "2023-01-01T00:01:00",
                    "step_type": "plan",
                    "duration_ms": 100.0,
                    "success": True,
                    "tool_name": None,
                },
                {
                    "timestamp": "2023-01-01T00:02:00",
                    "step_type": "tool",
                    "duration_ms": 50.0,
                    "success": True,
                    "tool_name": "test_tool",
                },
            ]

            for metric in test_metrics:
                f.write(json.dumps(metric) + "\n")

        try:
            analyzer = MetricsAnalyzer(metrics_file)
            summary = analyzer.analyze_recent_performance()

            assert summary.total_sessions == 1
            assert summary.total_iterations == 3
            assert summary.average_session_duration_ms == 1000.0
            assert summary.overall_success_rate == 1.0  # All steps successful
            assert summary.safety_incidents == 0
        finally:
            metrics_file.unlink(missing_ok=True)

    def test_generate_ci_report(self):
        """Test generating CI report."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            metrics_file = Path(f.name)

        try:
            analyzer = MetricsAnalyzer(metrics_file)
            report = analyzer.generate_ci_report()

            assert "Performance Metrics Report" in report
            assert "**Sessions**: 0" in report
            assert "**Success Rate**: 0.0%" in report
        finally:
            metrics_file.unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__])
