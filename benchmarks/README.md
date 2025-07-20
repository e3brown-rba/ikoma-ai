# Ikoma Performance Benchmarking System

This directory contains the performance benchmarking system for the Ikoma agent. The system measures startup time and per-turn latency to detect performance regressions.

## Overview

The benchmarking system consists of:

- **`bench.py`**: Main benchmark runner with regression detection
- **`metrics.py`**: Performance metrics collection and reporting
- **`scenarios.py`**: Standardized test scenarios for consistent measurements
- **`baselines.json`**: Historical baseline data (auto-generated)

## Usage

### Running Benchmarks

```bash
# Run all benchmarks and check for regressions
python -m benchmarks.bench

# Run benchmarks and save as new baseline
python -m benchmarks.bench --save-baseline

# Check existing results against baseline
python -m benchmarks.bench --check-only
```

### Establishing New Baselines

When performance improvements are made or the baseline becomes outdated:

```bash
# Use the convenience script
./scripts/establish_baseline.sh

# Or run manually
python -m benchmarks.bench --save-baseline
```

## Metrics Measured

### Startup Time
- **Metric**: `agent_startup`
- **Description**: Time to initialize the agent (create_agent function)
- **Iterations**: 5 (averaged)
- **Unit**: seconds

### Turn Latency
- **Metric**: `turn_latency_{scenario_name}`
- **Description**: Time for single plan-execute-reflect cycle
- **Iterations**: 3 (averaged)
- **Unit**: seconds

### Scenarios
1. **simple_math**: Calculate 23*7+11
2. **file_operation**: Create a file with content
3. **multi_step**: List files and create summary
4. **text_processing**: Create and read a file
5. **simple_planning**: Basic question answering

## Regression Detection

The system detects performance regressions using these thresholds:

- **Regression**: >20% slower than baseline
- **Improvement**: >10% faster than baseline (noted but doesn't fail CI)
- **Acceptable**: Within ±20% of baseline

## CI Integration

The benchmarking system is integrated into the CI pipeline:

1. **Main CI** (`.github/workflows/ci.yml`): Runs performance checks after build
2. **Benchmark Workflow** (`.github/workflows/benchmark.yml`): Dedicated benchmark job with PR comments

### CI Behavior

- **No Baseline**: Creates new baseline automatically
- **Regression Detected**: Fails CI with detailed report
- **PR Comments**: Posts benchmark results to PRs
- **Artifacts**: Uploads results for historical tracking

## Configuration

### Environment Variables

The benchmarks use the same environment as the main agent:
- `LMSTUDIO_BASE_URL`: LLM endpoint (default: http://127.0.0.1:11434/v1)
- `LMSTUDIO_MODEL`: Model name (default: meta-llama-3-8b-instruct)

### Baseline Management

Baselines are stored in `benchmarks/baselines.json`:
```json
{
  "timestamp": 1234567890,
  "baselines": {
    "agent_startup": {
      "name": "agent_startup",
      "value": 2.5,
      "unit": "seconds",
      "timestamp": "2023-01-01T00:00:00"
    }
  }
}
```

## Development

### Adding New Scenarios

Add scenarios to `benchmarks/scenarios.py`:

```python
{
    "name": "new_scenario",
    "goal": "Description of what to test",
    "expected_tools": ["tool1", "tool2"],
    "config": {"configurable": {"user_id": "benchmark"}}
}
```

### Running Tests

```bash
# Run benchmark tests
pytest tests/test_benchmarks.py

# Run with coverage
pytest tests/test_benchmarks.py --cov=benchmarks
```

## Troubleshooting

### Common Issues

1. **No baseline found**: Run `./scripts/establish_baseline.sh`
2. **Benchmark failures**: Check LLM availability and environment setup
3. **High variance**: Increase iterations in benchmark code
4. **False regressions**: Update baseline after legitimate changes

### Debug Mode

For debugging, you can run benchmarks with verbose output:

```bash
python -m benchmarks.bench --output debug_results.json
```

Then examine the detailed results in `debug_results.json`.

## Performance Tips

1. **Isolation**: Benchmarks run with `disable_checkpoint=True` for consistency
2. **Cleanup**: Agents are properly cleaned up between iterations
3. **Averaging**: Multiple iterations reduce variance
4. **Single Turn**: Turn latency tests use `max_iterations=1` for focused measurement

## Future Enhancements

- Memory usage tracking
- CPU utilization metrics
- Network latency measurements
- Custom scenario definitions
- Trend analysis and charts 