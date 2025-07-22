"""Metrics collector singleton for agent performance monitoring."""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .models import SessionMetric, StepMetric


class MetricsCollector:
    """Thread-safe metrics collector with JSON lines output."""

    _instance: Optional["MetricsCollector"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MetricsCollector":
        """Singleton pattern for global metrics collector."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        if hasattr(self, "_initialized"):
            return

        self.enabled = self._get_enabled()
        self.output_path = self._get_output_path()
        self.max_size_mb = self._get_max_size()
        self._file_lock = threading.Lock()
        self._session_metrics: dict[str, SessionMetric] = {}
        self._session_lock = threading.Lock()

        # Ensure output directory exists
        if self.enabled:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialized = True

    def _get_enabled(self) -> bool:
        """Get metrics collection enabled status from environment."""
        return os.getenv("IKOMA_METRICS_ENABLED", "false").lower() == "true"

    def _get_output_path(self) -> Path:
        """Get metrics output path from environment."""
        path = os.getenv("IKOMA_METRICS_PATH", "agent/logs/metrics.jsonl")
        return Path(path)

    def _get_max_size(self) -> int:
        """Get maximum file size in MB from environment."""
        return int(os.getenv("IKOMA_METRICS_MAX_SIZE_MB", "100"))

    def emit_step(
        self,
        step_type: str,
        duration_ms: float,
        success: bool,
        tool_name: str | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Emit a step metric."""
        if not self.enabled:
            return

        metric = StepMetric(
            timestamp=datetime.utcnow(),
            thread_id=threading.current_thread().name,
            step_type=step_type,
            tool_name=tool_name,
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata=metadata or {},
        )

        self._write_metric(metric.model_dump())

    def start_session(self, session_id: str) -> None:
        """Start tracking a new session."""
        if not self.enabled:
            return

        with self._session_lock:
            self._session_metrics[session_id] = SessionMetric(
                timestamp=datetime.utcnow(),
                thread_id=threading.current_thread().name,
                session_id=session_id,
                total_duration_ms=0.0,
                iterations=0,
                tools_used=[],
                success_rate=0.0,
                safety_incidents=0,
            )

    def update_session(self, session_id: str, **kwargs: Any) -> None:
        """Update session metrics."""
        if not self.enabled:
            return

        with self._session_lock:
            if session_id in self._session_metrics:
                session = self._session_metrics[session_id]
                for key, value in kwargs.items():
                    if hasattr(session, key):
                        setattr(session, key, value)

    def end_session(self, session_id: str) -> SessionMetric | None:
        """End session tracking and return final metrics."""
        if not self.enabled:
            return None

        with self._session_lock:
            if session_id in self._session_metrics:
                session = self._session_metrics.pop(session_id)
                self._write_metric(session.model_dump())
                return session
        return None

    def record_safety_incident(self, session_id: str, incident_type: str) -> None:
        """Record a safety incident."""
        if not self.enabled:
            return

        with self._session_lock:
            if session_id in self._session_metrics:
                self._session_metrics[session_id].safety_incidents += 1

        # Also emit as step metric for detailed tracking
        self.emit_step(
            step_type="safety_incident",
            duration_ms=0.0,
            success=False,
            error=incident_type,
            metadata={"incident_type": incident_type},
        )

    def _write_metric(self, metric: dict[str, Any]) -> None:
        """Write metric to JSONL file with rotation."""
        with self._file_lock:
            # Check file size and rotate if needed
            if self.output_path.exists():
                size_mb = self.output_path.stat().st_size / (1024 * 1024)
                if size_mb > self.max_size_mb:
                    self._rotate_file()

            # Convert datetime objects to ISO format for JSON serialization
            def serialize_metric(obj: Any) -> Any:
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj

            # Write metric as JSON line
            with open(self.output_path, "a") as f:
                f.write(json.dumps(metric, default=serialize_metric) + "\n")

    def _rotate_file(self) -> None:
        """Rotate metrics file when size limit is reached."""
        if not self.output_path.exists():
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = self.output_path.with_suffix(f".{timestamp}.jsonl")
        self.output_path.rename(backup_path)

    def get_recent_metrics(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Get recent metrics for analysis."""
        if not self.output_path.exists():
            return []

        metrics = []
        with open(self.output_path) as f:
            for line in f:
                try:
                    metrics.append(json.loads(line.strip()))
                    if len(metrics) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
        return metrics


# Global instance
metrics_collector = MetricsCollector()
