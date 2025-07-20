"""Tests for the benchmarking system."""
import json
from unittest.mock import Mock, patch

from benchmarks.bench import IkomaBenchmark
from benchmarks.metrics import BenchmarkMetrics, PerformanceResult
from benchmarks.scenarios import BENCHMARK_SCENARIOS


class TestPerformanceResult:
    """Test PerformanceResult dataclass."""

    def test_to_dict(self):
        """Test PerformanceResult.to_dict() method."""
        result = PerformanceResult(
            name="test_metric",
            value=1.234,
            unit="seconds"
        )

        data = result.to_dict()
        assert data["name"] == "test_metric"
        assert data["value"] == 1.234
        assert data["unit"] == "seconds"
        assert "timestamp" in data


class TestBenchmarkMetrics:
    """Test BenchmarkMetrics class."""

    def test_format_github_output(self):
        """Test GitHub output formatting."""
        metrics = BenchmarkMetrics()
        results = [
            PerformanceResult("agent_startup", 2.5),
            PerformanceResult("turn_latency_simple", 1.2)
        ]

        output = metrics.format_github_output(results)
        assert "🚀 **agent_startup**" in output
        assert "⏱️ **turn_latency_simple**" in output
        assert "2.500s" in output
        assert "1.200s" in output

    def test_save_artifacts(self, tmp_path):
        """Test saving artifacts to JSON."""
        metrics = BenchmarkMetrics()
        results = [
            PerformanceResult("test_metric", 1.5)
        ]

        output_path = tmp_path / "results.json"
        metrics.save_artifacts(results, output_path)

        assert output_path.exists()
        with open(output_path) as f:
            data = json.load(f)

        assert "timestamp" in data
        assert "results" in data
        assert "summary" in data
        assert len(data["results"]) == 1


class TestIkomaBenchmark:
    """Test IkomaBenchmark class."""

    def test_init(self, tmp_path):
        """Test benchmark initialization."""
        baseline_path = tmp_path / "baselines.json"
        benchmark = IkomaBenchmark(baseline_path)

        assert benchmark.baseline_path == baseline_path
        assert isinstance(benchmark.metrics, BenchmarkMetrics)

    @patch('benchmarks.bench.create_agent')
    def test_measure_startup(self, mock_create_agent, tmp_path):
        """Test startup time measurement."""
        mock_agent = Mock()
        mock_create_agent.return_value = mock_agent

        benchmark = IkomaBenchmark(tmp_path / "baselines.json")
        result = benchmark.measure_startup(iterations=2)

        assert isinstance(result, float)
        assert result > 0
        assert mock_create_agent.call_count == 2

    def test_check_regression_no_baseline(self, tmp_path):
        """Test regression check when no baseline exists."""
        baseline_path = tmp_path / "baselines.json"
        benchmark = IkomaBenchmark(baseline_path)

        results = [PerformanceResult("test_metric", 1.0)]

        # Should not have regression and should create baseline
        has_regression = benchmark.check_regression(results)
        assert not has_regression
        assert baseline_path.exists()

    def test_check_regression_with_baseline(self, tmp_path):
        """Test regression check with existing baseline."""
        baseline_path = tmp_path / "baselines.json"

        # Create baseline
        baseline_data = {
            "timestamp": 1234567890,
            "baselines": {
                "test_metric": {
                    "name": "test_metric",
                    "value": 1.0,
                    "unit": "seconds",
                    "timestamp": "2023-01-01T00:00:00"
                }
            }
        }

        with open(baseline_path, "w") as f:
            json.dump(baseline_data, f)

        benchmark = IkomaBenchmark(baseline_path)

        # Test no regression (within 20%)
        results = [PerformanceResult("test_metric", 1.1)]
        has_regression = benchmark.check_regression(results)
        assert not has_regression

        # Test regression (>20% slower)
        results = [PerformanceResult("test_metric", 1.3)]
        has_regression = benchmark.check_regression(results)
        assert has_regression

    def test_save_baseline(self, tmp_path):
        """Test saving baseline data."""
        baseline_path = tmp_path / "baselines.json"
        benchmark = IkomaBenchmark(baseline_path)

        results = [
            PerformanceResult("metric1", 1.0),
            PerformanceResult("metric2", 2.0)
        ]

        benchmark.save_baseline(results)

        assert baseline_path.exists()
        with open(baseline_path) as f:
            data = json.load(f)

        assert "timestamp" in data
        assert "baselines" in data
        assert "metric1" in data["baselines"]
        assert "metric2" in data["baselines"]


class TestBenchmarkScenarios:
    """Test benchmark scenarios."""

    def test_scenarios_structure(self):
        """Test that all scenarios have required fields."""
        for scenario in BENCHMARK_SCENARIOS:
            assert "name" in scenario
            assert "goal" in scenario
            assert "expected_tools" in scenario
            assert "config" in scenario
            assert isinstance(scenario["name"], str)
            assert isinstance(scenario["goal"], str)
            assert isinstance(scenario["expected_tools"], list)
            assert isinstance(scenario["config"], dict)

    def test_scenario_names_unique(self):
        """Test that scenario names are unique."""
        names = [scenario["name"] for scenario in BENCHMARK_SCENARIOS]
        assert len(names) == len(set(names)), "Scenario names must be unique"

    def test_scenario_configs(self):
        """Test that all scenarios have proper config structure."""
        for scenario in BENCHMARK_SCENARIOS:
            config = scenario["config"]
            assert "configurable" in config
            assert "user_id" in config["configurable"]
            assert config["configurable"]["user_id"] == "benchmark"
