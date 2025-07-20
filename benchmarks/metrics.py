"""Performance metrics collection and reporting."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class PerformanceResult:
    """Single performance measurement result."""

    name: str
    value: float
    unit: str = "seconds"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": datetime.utcnow().isoformat(),
        }


class BenchmarkMetrics:
    """Collect and format performance metrics."""

    def format_github_output(self, results: list[PerformanceResult]) -> str:
        """Format results for GitHub Actions output."""
        lines = ["## Performance Benchmark Results\n"]

        for result in results:
            emoji = "🚀" if "startup" in result.name else "⏱️"
            lines.append(f"{emoji} **{result.name}**: {result.value:.3f}s")

        return "\n".join(lines)

    def save_artifacts(self, results: list[PerformanceResult], path: Path) -> None:
        """Save results as JSON artifact."""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "results": [r.to_dict() for r in results],
            "summary": {
                "total_metrics": len(results),
                "average_latency": sum(r.value for r in results if "latency" in r.name)
                / max(1, sum(1 for r in results if "latency" in r.name)),
            },
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)
